# src/analysis/analyze_articles.py (Final Refactor)
"""
Analyzes new articles against semantic anchors to generate intelligence.
Applies a minimum similarity score threshold for specific source categories.
"""

import os
import sys
import time
import argparse
import numpy as np
import pandas as pd
import chromadb
import psycopg2
from scipy.spatial.distance import cdist # ADD THIS LINE

# --- Path Setup ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from src.management.db_utils import get_db_connection

# --- CONFIGURATION ---
DATA_DIR = os.path.join(ROOT_DIR, 'data')
LOG_DIR = os.path.join(ROOT_DIR, 'logs')
CHROMA_DB_PATH = os.path.join(DATA_DIR, 'chroma_db')
COLLECTION_NAME = 'irpp_research'
BATCH_SIZE = 50
K_FOR_SIMILARITY = 5

# NEW: Define the threshold and the categories it applies to
MINIMUM_SIMILARITY_SCORE = 0.25
CATEGORIES_TO_FILTER = ['News Media', 'Misc. Research']

# ==============================================================================
# --- HELPER FUNCTIONS ---
# ==============================================================================

def setup_logging():
    os.makedirs(LOG_DIR, exist_ok=True)
    log_file = os.path.join(LOG_DIR, 'analysis_log.txt')
    open(log_file, 'w').close()
    return log_file

def log_message(message, log_file, level='INFO'):
    log_entry = f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {level} - {message}"
    print(log_entry)
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(log_entry + '\n')

def load_anchors_with_embeddings(conn, chroma_collection, log_file):
    """
    Loads all ACTIVE anchors and calculates their representative embeddings.
    This is the corrected version that handles all component types.
    """
    log_message("Loading all ACTIVE anchors and their component embeddings...", log_file)
    with conn.cursor() as cursor:
        # Fetch data from the database in fewer queries
        cursor.execute("SELECT program_tag, source_location FROM knowledge_base WHERE source_type = 'program_charter'")
        charter_map = {row[0]: row[1] for row in cursor.fetchall()}

        cursor.execute("SELECT tag_name, embedding FROM tags")
        tag_embeddings_map = {name: np.frombuffer(blob, dtype=np.float32) for name, blob in cursor.fetchall()}

        cursor.execute("SELECT id, name FROM semantic_anchors WHERE is_active = true")
        anchor_names = dict(cursor.fetchall())
        
        cursor.execute("SELECT anchor_id, component_type, component_id FROM anchor_components WHERE anchor_id = ANY(%s)", (list(anchor_names.keys()),))
        components_by_anchor = {}
        for anchor_id, comp_type, comp_id in cursor.fetchall():
            components_by_anchor.setdefault(anchor_id, []).append({'type': comp_type, 'id': comp_id})

    final_anchor_embeddings = {}
    for anchor_id, components in components_by_anchor.items():
        embeddings_for_this_anchor = []
        for component in components:
            comp_type, comp_id = component['type'], component['id']
            if comp_type == 'tag' and comp_id in tag_embeddings_map:
                embeddings_for_this_anchor.append(tag_embeddings_map[comp_id])
            elif comp_type == 'kb_item':
                results = chroma_collection.get(where={"source_location": comp_id}, include=["embeddings"])
                if results['ids']:
                    embeddings_for_this_anchor.extend([np.array(e) for e in results['embeddings']])
            elif comp_type == 'program':
                charter_loc = charter_map.get(comp_id)
                if charter_loc:
                    results = chroma_collection.get(where={"source_location": charter_loc}, include=["embeddings"])
                    if results['ids']:
                        embeddings_for_this_anchor.extend([np.array(e) for e in results['embeddings']])
        
        if embeddings_for_this_anchor:
            final_anchor_embeddings[anchor_id] = {
                'name': anchor_names.get(anchor_id, 'Unknown Anchor'),
                'embeddings': embeddings_for_this_anchor
            }

    log_message(f"Successfully processed and loaded embeddings for {len(final_anchor_embeddings)} active anchors.", log_file)
    
    return final_anchor_embeddings

def calculate_similarity(article_embeddings, anchor_embeddings):
    if not article_embeddings or not anchor_embeddings: return 0.0
    return np.mean(np.sort(1 - cdist(np.array(article_embeddings), np.array(anchor_embeddings), 'cosine'), axis=None)[-K_FOR_SIMILARITY:])

def get_unanalyzed_articles(conn, batch_size=BATCH_SIZE):
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT a.id, a.title, src.category as source_category
            FROM articles a
            JOIN sources src ON a.source_id = src.id
            WHERE a.indexed_at IS NOT NULL AND a.analyzed_at IS NULL
            LIMIT %s
        """, (batch_size,))
        return [dict(zip([column[0] for column in cursor.description], row)) for row in cursor.fetchall()]

def get_article_embeddings(chroma_collection, article_db_ids):
    article_embeddings = {db_id: [] for db_id in article_db_ids}
    results = chroma_collection.get(where={"article_db_id": {"$in": article_db_ids}}, include=["metadatas", "embeddings"])
    if results['ids']:
        for i in range(len(results['ids'])):
            db_id = results['metadatas'][i].get('article_db_id')
            if db_id in article_embeddings:
                article_embeddings[db_id].append(np.array(results['embeddings'][i]))
    return article_embeddings

# ==============================================================================
# --- MAIN ORCHESTRATION ---
# ==============================================================================

def main(conn, limit=None):
    """Main function to orchestrate the analysis process."""
    log_file = setup_logging()
    
    try:
        chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        collection = chroma_client.get_collection(name=COLLECTION_NAME)
    except Exception as e:
        log_message(f"FATAL: Failed to connect to ChromaDB: {e}", log_file, "ERROR")
        return 0

    # Pass the log_file to the function
    anchors = load_anchors_with_embeddings(conn, collection, log_file)
    if not anchors:
        log_message("No active anchors with embeddings found. Exiting.", log_file, "WARNING")
        return 0
 
    batch_size = limit if limit else BATCH_SIZE
    total_articles_analyzed = 0
    
    # Add this flag before the loop
    first_article_debug_done = False

    log_message("--- Starting Article Analysis Process ---", log_file)
    while True:
        articles_to_process = get_unanalyzed_articles(conn, batch_size)

        if not articles_to_process:
            log_message("No new unanalyzed articles found. Process complete.", log_file)
            break

        log_message(f"Found {len(articles_to_process)} articles to analyze in this batch.", log_file)
        article_ids = [article['id'] for article in articles_to_process]
        batch_article_embeddings = get_article_embeddings(collection, article_ids)
            
        links_to_insert = []
        skipped_links = 0
        for article in articles_to_process:
            article_id = article['id']
            article_embeddings = batch_article_embeddings.get(article_id, [])
            
                        # --- START DEBUGGING BLOCK ---
            if not first_article_debug_done:
                print("\n\n--- DEBUGGING FIRST ARTICLE ---")
                print(f"  Article ID: {article_id}")
                print(f"  Source Category: {article.get('source_category')}")
                print(f"  Number of embeddings found for this article: {len(article_embeddings)}")
            # --- END DEBUGGING BLOCK ---

            if not article_embeddings:
                if not first_article_debug_done:
                    print("  DEBUG: No embeddings found, skipping.")
                continue

            for anchor_id, anchor_data in anchors.items():
                score = calculate_similarity(article_embeddings, anchor_data['embeddings'])

                # --- MORE DEBUGGING ---
                if not first_article_debug_done:
                    print(f"  - Calculated score against anchor '{anchor_data['name']}': {score:.4f}")
                    # Set the flag so we don't print this again
                    first_article_debug_done = True
                # --- END MORE DEBUGGING ---
                
                # --- NEW LOGIC: Conditional Threshold Filter ---
                if article['source_category'] in CATEGORIES_TO_FILTER:
                    if score < MINIMUM_SIMILARITY_SCORE:
                        skipped_links += 1
                        continue # Skip saving this link
                
                links_to_insert.append((article_id, anchor_id, score))
            
        if links_to_insert:
            log_message(f"Inserting {len(links_to_insert)} new anchor links into the database...", log_file)
            with conn.cursor() as cursor:
                cursor.executemany("INSERT INTO article_anchor_links (article_id, anchor_id, similarity_score) VALUES (%s, %s, %s)", links_to_insert)
        
        if skipped_links > 0:
            log_message(f"Skipped {skipped_links} links that did not meet the {MINIMUM_SIMILARITY_SCORE} threshold for filtered categories.", log_file)

        log_message(f"Updating {len(article_ids)} articles as analyzed...", log_file)
        update_ids = [[article_id] for article_id in article_ids]
        with conn.cursor() as cursor:
            cursor.executemany("UPDATE articles SET analyzed_at = CURRENT_TIMESTAMP WHERE id = %s", update_ids)
        
        total_articles_analyzed += len(articles_to_process)
        if limit: break # If in limit mode, only run one batch
        
    log_message(f"--- Article Analysis Finished ---", log_file)
    log_message(f"Total articles analyzed in this run: {total_articles_analyzed}", log_file)

    return total_articles_analyzed

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze articles and link them to semantic anchors.")
    parser.add_argument("--limit", type=int, help="Run in test mode, processing only a limited number of articles.")
    args = parser.parse_args()

    connection = None
    try:
        connection = get_db_connection()
        main(connection, limit=args.limit)
        connection.commit()
    except Exception as e:
        print(f"An error occurred during standalone execution: {e}")
        if connection: connection.rollback()
    finally:
        if connection:
            connection.close()