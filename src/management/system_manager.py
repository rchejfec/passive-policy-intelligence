# src/management/system_manager.py
"""
Contains system-level functions for database management and maintenance.
"""

import os
import chromadb
from typing import Optional, Any
from src.management.db_utils import get_db_connection

# --- Configuration (mirrors configuration in indexing scripts) ---
# This path navigates from this file (in src/management) up to the project root
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DATA_DIR = os.path.join(ROOT_DIR, 'data')
CHROMA_DB_PATH = os.path.join(DATA_DIR, 'chroma_db')
COLLECTION_NAME = 'irpp_research'

def initialize_chroma_db() -> None:
    """
    Connects to ChromaDB and ensures the required collection exists.

    This function is idempotent and non-destructive.
    """
    print("\n--- Verifying ChromaDB setup... ---")
    try:
        os.makedirs(CHROMA_DB_PATH, exist_ok=True)

        client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

        # get_or_create_collection is idempotent
        collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"} # Specifies the distance function
        )

        print(f"-> ChromaDB collection '{collection.name}' is ready.")
        print(f"   Current number of items in collection: {collection.count()}")
        print("--- ChromaDB setup verified. ---")

    except Exception as e:
        print(f"DATABASE ERROR: An error occurred with ChromaDB setup: {e}")

# Add this new function at the end of the file
def reset_analysis_data() -> None:
    """
    Deletes all records from the article_anchor_links table and resets the
    'analyzed_at' timestamp in the articles table.
    """
    print("\n--- Resetting analysis data... ---")
    conn = get_db_connection()
    try:
        with conn:
            # Delete all links between articles and anchors
            cursor = conn.cursor()
            cursor.execute("DELETE FROM article_anchor_links")
            deleted_links = cursor.rowcount
            print(f"-> Deleted {deleted_links} records from 'article_anchor_links'.")

            # Reset the analyzed_at timestamp for all articles
            cursor.execute("UPDATE articles SET analyzed_at = NULL WHERE analyzed_at IS NOT NULL")
            reset_articles = cursor.rowcount
            print(f"-> Reset 'analyzed_at' timestamp for {reset_articles} articles.")

        print("--- Analysis data successfully reset. ---")
    except Exception as e:
        print(f"DATABASE ERROR: An error occurred while resetting analysis data: {e}")
    finally:
        if conn:
            conn.close()

def reset_subscriber_data() -> None:
    """
    Deletes all records from the subscribers and subscriptions tables.
    This is done explicitly to clean up any potential orphan subscription
    records left over from before foreign_keys were enforced.
    """
    print("\n--- Resetting subscriber data... ---")
    conn = get_db_connection()
    try:
        with conn:
            cursor = conn.cursor()

            # Step 1: Delete from the child table first.
            cursor.execute("DELETE FROM subscriptions")
            deleted_subscriptions = cursor.rowcount
            print(f"-> Deleted {deleted_subscriptions} records from 'subscriptions'.")

            # Step 2: Delete from the parent table.
            cursor.execute("DELETE FROM subscribers")
            deleted_subscribers = cursor.rowcount
            print(f"-> Deleted {deleted_subscribers} records from 'subscribers'.")

        print("--- Subscriber data successfully reset. ---")
    except Exception as e:
        print(f"DATABASE ERROR: An error occurred while resetting subscriber data: {e}")
    finally:
        if conn:
            conn.close()


def reset_anchor_data() -> None:
    """
    DEACTIVATES all active anchors by setting their 'is_active' flag to 0.
    This is a non-destructive reset.
    """
    print("\n--- Deactivating all active anchors... ---")
    conn = get_db_connection()
    try:
        with conn:
            cursor = conn.cursor()
            # MODIFIED: Perform a soft delete instead of a hard DELETE.
            cursor.execute("UPDATE semantic_anchors SET is_active = 0 WHERE is_active = 1")
            deactivated_anchors = cursor.rowcount
            print(f"-> Deactivated {deactivated_anchors} anchors.")

        print("--- Anchor deactivation complete. ---")
    except Exception as e:
        print(f"DATABASE ERROR: An error occurred while deactivating anchors: {e}")
    finally:
        if conn:
            conn.close()

# --- NEW ---
def reset_enrichment_data(limit: Optional[int] = None, offset: int = 0) -> None:
    """
    Resets the enrichment_processed_at timestamp and is_org_highlight flag
    for a specified number of articles, allowing them to be re-processed.
    Sorts by article ID ASC to ensure predictability.

    Args:
        limit: The maximum number of articles to reset.
        offset: The starting offset for resetting articles.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # MODIFIED: Select based on ID ASC for predictable resets
        base_select_query = "SELECT id FROM articles WHERE enrichment_processed_at IS NOT NULL ORDER BY id ASC"
        
        params = []
        if limit is not None:
            base_select_query += " LIMIT ?"
            params.append(limit)
        
        # Offset must be used with limit in SQLite
        if limit is not None and offset > 0:
            base_select_query += " OFFSET ?"
            params.append(offset)

        # Main query to update articles based on the sub-selection
        update_query = f"""
            UPDATE articles
            SET 
                enrichment_processed_at = NULL,
                is_org_highlight = 0
            WHERE id IN ({base_select_query});
        """

        print("\n--- Resetting enrichment data... ---")
        if limit is not None:
            print(f"-> Parameters: LIMIT={limit}, OFFSET={offset}")
        
        cursor.execute(update_query, params)
        conn.commit()
        
        row_count = cursor.rowcount
        if row_count > 0:
            print(f"✅ Success: {row_count} articles have been reset and are ready for re-enrichment.")
        else:
            print("✅ Success: No articles matching the criteria were found to reset.")

    except Exception as e:
        print(f"❌ An error occurred: {e}")
        conn.rollback()
    finally:
        if conn:
            conn.close()
