# src/delivery/engine.py
import os
import sys
import requests
import pandas as pd
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import psycopg2.extensions

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from src.management.db_utils import get_db_connection
from src.delivery import config, renderer

@dataclass
class Article:
    id: int
    title: str
    url: str
    source_name: str
    source_category: str
    score: float
    is_highlight: bool
    anchors: List[str] = field(default_factory=list)

def should_run() -> bool:
    """Ensures the digest only sends in the morning.

    Returns:
        True if it should run, False otherwise.
    """
    current_hour = datetime.now().hour
    if current_hour >= 20:
        print(f"Skipping Digest: Current hour is {current_hour} (Afternoon). Digest only runs in AM.")
        return False
    return True

def fetch_candidates(conn: psycopg2.extensions.connection) -> pd.DataFrame:
    """Fetches candidate articles from the database.

    Args:
        conn: Database connection.

    Returns:
        DataFrame containing candidate articles.
    """
    print("Fetching candidate articles...")
    # Fetch all potential matches first (Highlights OR Score > Min)
    sql = f"""
        SELECT 
            a.id, a.title, a.link, src.name as source_name, src.category,
            aal.similarity_score, a.is_org_highlight, sa.name as anchor_name
        FROM articles a
        JOIN article_anchor_links aal ON a.id = aal.article_id
        JOIN sources src ON a.source_id = src.id
        JOIN semantic_anchors sa ON aal.anchor_id = sa.id
        WHERE 
            a.created_at > NOW() - INTERVAL '{config.LOOKBACK_HOURS} HOURS'
            AND a.newsletter_sent_at IS NULL
            AND (a.is_org_highlight = TRUE OR aal.similarity_score >= {config.MIN_SCORE})
    """
    df = pd.read_sql_query(sql, conn)
    return df

def process_articles(df: pd.DataFrame) -> List[Article]:
    """Aggregates rows (1 article : N anchors) into unique Article objects.

    Args:
        df: DataFrame of article rows.

    Returns:
        List of Article objects.
    """
    if df.empty: return []
    
    articles_map = {}
    for _, row in df.iterrows():
        aid = row['id']
        if aid not in articles_map:
            articles_map[aid] = Article(
                id=aid, title=row['title'], url=row['link'],
                source_name=row['source_name'], source_category=row['category'],
                score=row['similarity_score'], is_highlight=row['is_org_highlight']
            )
        
        anchor = row['anchor_name']
        if anchor not in articles_map[aid].anchors:
            articles_map[aid].anchors.append(anchor)
            
        if row['similarity_score'] > articles_map[aid].score:
            articles_map[aid].score = row['similarity_score']

    return list(articles_map.values())

def filter_by_scope(articles: List[Article]) -> List[Article]:
    """Filters articles based on Configured Allowed Anchors/Types.

    Args:
        articles: List of Article objects.

    Returns:
        Filtered list of Article objects.
    """
    # If no filters are set, return everything
    if not config.ALLOWED_ANCHORS and not config.ALLOWED_ANCHOR_TYPES:
        return articles

    keep_list = []
    for art in articles:
        # RULE 1: VIP Pass
        # If it's a Priority Highlight, keep it regardless of filters
        if art.is_highlight:
            keep_list.append(art)
            continue

        # Normal Filtering Logic for everything else
        keep = False
        
        # Check 1: Specific Anchor Names
        if config.ALLOWED_ANCHORS:
            if any(a in config.ALLOWED_ANCHORS for a in art.anchors):
                keep = True

        # Check 2: Anchor Types (Prefixes)
        if not keep and config.ALLOWED_ANCHOR_TYPES:
            for anchor in art.anchors:
                for allowed_type in config.ALLOWED_ANCHOR_TYPES:
                    # Check if anchor starts with "PROG:" or just "PROG"
                    if anchor.upper().startswith(f"{allowed_type.upper()}:"):
                        keep = True
                        break
                if keep: break
        
        if keep:
            keep_list.append(art)
            
    print(f"Scope Filter: Kept {len(keep_list)} out of {len(articles)} articles.")
    return keep_list

def select_content(all_articles: List[Article]) -> Dict[str, List[Article]]:
    """Sorts articles into sections and picks the winners.

    Args:
        all_articles: List of Article objects.

    Returns:
        Dictionary mapping section titles to lists of Article objects.
    """
    selected_ids = set()
    sections_content = {}
    
    def pick_top_n(candidates: List[Article], limit: int) -> List[Article]:
        candidates.sort(key=lambda x: (x.is_highlight, x.score), reverse=True)
        picks = []
        for art in candidates:
            if art.id not in selected_ids:
                picks.append(art)
                selected_ids.add(art.id)
            if len(picks) >= limit:
                break
        return picks

    highlights = [a for a in all_articles if a.is_highlight]
    sections_content["🚨 Priority Highlights"] = pick_top_n(highlights, config.ITEMS_PER_SECTION)
    
    for section_title, settings in config.SECTIONS.items():
        if "Priority" in section_title: continue
        target_categories = settings["categories"]
        candidates = [a for a in all_articles if a.source_category in target_categories]
        sections_content[section_title] = pick_top_n(candidates, config.ITEMS_PER_SECTION)
        
    return sections_content

def mark_as_sent(conn: psycopg2.extensions.connection, articles_data: Dict[str, List[Article]]) -> None:
    """Updates the database timestamp for sent articles.

    Args:
        conn: Database connection.
        articles_data: Dictionary of sections containing articles.
    """
    ids_to_update = []
    for section in articles_data.values():
        for art in section:
            ids_to_update.append(art.id)
    
    if not ids_to_update: return

    with conn.cursor() as cur:
        cur.execute(
            "UPDATE articles SET newsletter_sent_at = NOW() WHERE id = ANY(%s)",
            (ids_to_update,)
        )
    print(f"Marked {len(ids_to_update)} articles as sent.")

def main(conn: psycopg2.extensions.connection) -> None:
    """Main execution logic for the digest delivery engine.

    Args:
        conn: Database connection.
    """
    print("--- Starting Digest Delivery Engine ---")
    
    if not should_run(): return

    raw_df = fetch_candidates(conn)
    if raw_df.empty:
        print("No new relevant articles found for digest.")
        return
    
    all_articles = process_articles(raw_df)
    
    # --- FILTERING STEP ---
    filtered_articles = filter_by_scope(all_articles)
    
    if not filtered_articles:
        print("Articles found, but none matched the configured Scope (PROG/Allowed list).")
        return

    final_sections = select_content(filtered_articles)
    total_items = sum(len(v) for v in final_sections.values())
    
    if total_items == 0:
        print("Articles passed filter, but were not selected for sections.")
        return

    print(f"Generating digest with {total_items} items...")
    card_payload = renderer.render_digest_card(final_sections, len(all_articles))
    
    webhook_url = os.getenv("TEAMS_WEBHOOK_URL")
    if not webhook_url:
        print("Error: TEAMS_WEBHOOK_URL not set.")
        return

    try:
        response = requests.post(webhook_url, json=card_payload)
        response.raise_for_status()
        print("✅ Digest sent to Teams successfully.")
        mark_as_sent(conn, final_sections)
    except Exception as e:
        print(f"❌ Failed to send digest: {e}")
        print(response.text)

if __name__ == "__main__":
    conn = get_db_connection()
    main(conn)
    conn.commit()
    conn.close()
