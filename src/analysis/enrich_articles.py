# src/delivery/enrich_articles.py (Refactored for DB updates)
"""
Performs enrichment calculations and writes the results (highlight flags)
directly back into the PostgreSQL database.
"""

import os
import sys
import argparse
import pandas as pd
from datetime import datetime
import psycopg2
from psycopg2.extras import execute_batch

# --- Path Setup ---
try:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:
    SCRIPT_DIR = os.path.abspath('')
ROOT_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from src.management.db_utils import get_db_connection

# --- Global Constants ---
TIER1_CATEGORIES = [
    'Think Tank', 'AI Research', 'Research Institute', 'Non-Profit',
    'Academic', 'Advocacy', 'Publication', 'Business Council'
]
TIER2_CATEGORY = 'Government'
TIER3_CATEGORY = 'News Media'

def load_data_to_process(conn):
    """
    Loads all article link data for articles that have not yet been enriched.
    CHANGED: This now selects the article_anchor_links primary key (link_id)
             for efficient updates.
    """
    print("Loading dataset from the database for enrichment...")
    sql = """
        SELECT
            aal.id as link_id,
            a.id as article_id, a.title, a.link, a.summary, a.published_date,
            src.name as source_name, src.category as source_category,
            sa.id as anchor_id, sa.name as anchor_name,
            aal.similarity_score
        FROM articles a
        JOIN article_anchor_links aal ON a.id = aal.article_id
        JOIN sources src ON a.source_id = src.id
        JOIN semantic_anchors sa ON aal.anchor_id = sa.id
        WHERE a.analyzed_at IS NOT NULL
          AND a.enrichment_processed_at IS NULL
          AND sa.is_active = true
    """
    to_process_df = pd.read_sql_query(sql, conn)
    
    if to_process_df.empty:
        print("No new articles to process for enrichment.")
        return pd.DataFrame(), pd.DataFrame()

    to_process_df['abs_score'] = to_process_df['similarity_score'].abs()
    print(f"Found {to_process_df['article_id'].nunique()} new articles to process.")
    
    # We also need the full history to calculate the org highlight threshold
    historical_sql = "SELECT article_id, similarity_score FROM article_anchor_links"
    historical_df = pd.read_sql_query(historical_sql, conn)
    historical_df['abs_score'] = historical_df['similarity_score'].abs()
    
    return to_process_df, historical_df

def calculate_threshold_map(conn):
    """
    Learns the historical performance thresholds from the database.
    This logic is unchanged but now reads directly from the DB.
    """
    print("Calculating historical performance to create threshold map...")
    sql = """
        SELECT sa.name as anchor_name, src.category as source_category, aal.similarity_score
        FROM article_anchor_links aal
        JOIN articles a ON a.id = aal.article_id
        JOIN sources src ON a.source_id = src.id
        JOIN semantic_anchors sa ON aal.anchor_id = sa.id
        WHERE sa.is_active = true
    """
    full_df = pd.read_sql_query(sql, conn)
    full_df['abs_score'] = full_df['similarity_score'].abs()
    
    historical_stats = full_df.groupby(['anchor_name', 'source_category'])['abs_score'].agg(['mean', 'std']).reset_index()
    historical_stats['mean_plus_std'] = historical_stats['mean'] + historical_stats['std'].fillna(0)
    threshold_map = historical_stats.pivot_table(index='anchor_name', columns='source_category', values=['mean', 'mean_plus_std'])
    print("Threshold map successfully calculated.")
    return threshold_map

def apply_enrichment_logic(articles_to_process_df, full_historical_df, threshold_map):
    """
    Enriches articles with `is_anchor_highlight` and `is_org_highlight` flags.
    The core logic here is preserved from your original script.
    """
    print("Applying enrichment logic to articles...")
    if articles_to_process_df.empty:
        return articles_to_process_df
        
    def apply_anchor_rules(row):
        category = row['source_category']
        anchor = row['anchor_name']
        score = row['abs_score']
        if category in TIER1_CATEGORIES:
            return score > 0.20
        elif category == TIER2_CATEGORY:
            try: return score > threshold_map.loc[anchor, ('mean', TIER2_CATEGORY)]
            except KeyError: return False
        elif category == TIER3_CATEGORY:
            try: return score > threshold_map.loc[anchor, ('mean_plus_std', TIER3_CATEGORY)]
            except KeyError: return False
        return False
    articles_to_process_df['is_anchor_highlight'] = articles_to_process_df.apply(apply_anchor_rules, axis=1)
    
    org_relevance_scores = full_historical_df.groupby('article_id')['abs_score'].max()
    org_highlight_threshold = org_relevance_scores.quantile(0.90)
    print(f"Organizational highlight threshold set at {org_highlight_threshold:.4f} (90th percentile).")

    current_org_scores = articles_to_process_df.groupby('article_id')['abs_score'].max().rename('org_relevance_score')
    enriched_df = articles_to_process_df.merge(current_org_scores, on='article_id')
    enriched_df['is_org_highlight'] = enriched_df['org_relevance_score'] > org_highlight_threshold
    
    num_anchor_highlights = enriched_df['is_anchor_highlight'].sum()
    num_org_highlights = enriched_df.drop_duplicates(subset='article_id')['is_org_highlight'].sum()
    print(f"Enrichment complete. Flagged {num_anchor_highlights:,} anchor highlights and {num_org_highlights:,} org highlights.")
    return enriched_df

def update_database_with_enrichments(conn, enriched_df):
    """
    NEW: Writes the calculated enrichment flags back to the database.
    """
    if enriched_df.empty:
        print("No enrichments to save to the database.")
        return

    print("Preparing to write enrichment data back to the database...")
    with conn.cursor() as cursor:
        # --- Update `article_anchor_links` table ---
        anchor_links_data = enriched_df[['is_anchor_highlight', 'link_id']].values.tolist()
        update_anchor_links_sql = "UPDATE article_anchor_links SET is_anchor_highlight = %s WHERE id = %s"
        execute_batch(cursor, update_anchor_links_sql, anchor_links_data)
        print(f"- Updated {cursor.rowcount} rows in 'article_anchor_links'.")

        # --- Update `articles` table ---
        # First, update the is_org_highlight flag
        org_highlights_df = enriched_df[['is_org_highlight', 'article_id']].drop_duplicates()
        org_highlights_data = org_highlights_df.values.tolist()
        update_org_highlights_sql = "UPDATE articles SET is_org_highlight = %s WHERE id = %s"
        execute_batch(cursor, update_org_highlights_sql, org_highlights_data)
        print(f"- Updated {cursor.rowcount} 'is_org_highlight' flags in 'articles'.")

        # Second, update the enrichment_processed_at timestamp for all processed articles
        processed_article_ids = enriched_df['article_id'].unique().tolist()
        # executemany expects a list of tuples/lists, so we format it correctly
        processed_ids_data = [[pid] for pid in processed_article_ids]
        update_timestamp_sql = "UPDATE articles SET enrichment_processed_at = CURRENT_TIMESTAMP WHERE id = %s"
        execute_batch(cursor, update_timestamp_sql, processed_ids_data)
        print(f"- Stamped {cursor.rowcount} articles as 'enriched'.")

def main(conn):
    """Main execution function for the enrichment process."""
    print("\n--- Starting Enrichment Engine ---")
    try:
        to_process_df, historical_df = load_data_to_process(conn)

        if to_process_df.empty:
            return 0 # Exit gracefully if there's nothing to do

        threshold_map = calculate_threshold_map(conn)
        enriched_df = apply_enrichment_logic(to_process_df, historical_df, threshold_map)
        update_database_with_enrichments(conn, enriched_df)

        # Return the number of org highlights found (or we could return anchor highlights too,
        # but the prompt specified a single integer for 'highlights_found')
        num_org_highlights = enriched_df.drop_duplicates(subset='article_id')['is_org_highlight'].sum()
        return int(num_org_highlights)

    except (Exception, psycopg2.Error) as e:
        print(f"An error occurred during enrichment: {e}")
        # Let the orchestrator handle rollback
        raise

if __name__ == "__main__":
    connection = None
    try:
        connection = get_db_connection()
        main(connection)
        connection.commit()
    except Exception as e:
        print(f"An error occurred during standalone execution.")
        if connection:
            connection.rollback()
    finally:
        if connection:
            connection.close()