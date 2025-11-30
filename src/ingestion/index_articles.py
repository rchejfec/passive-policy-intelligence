# src/ingestion/index_articles.py (Refactored for Orchestrator)
"""
Processes and indexes new articles from the database into ChromaDB.
"""

import os
import time
import re
from sentence_transformers import SentenceTransformer
import chromadb
import psycopg2 # CHANGED: For error handling
import psycopg2.extensions
from typing import List, Dict, Any, Optional

# CHANGED: This import is now only used when the script is run standalone for testing.
from src.management.db_utils import get_db_connection

# --- CONFIGURATION (No changes needed here) ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR)) 
DATA_DIR = os.path.join(ROOT_DIR, 'data')
LOG_DIR = os.path.join(ROOT_DIR, 'logs')

CHROMA_DB_PATH = os.path.join(DATA_DIR, 'chroma_db')
LOG_FILE = os.path.join(LOG_DIR, 'indexing_log_articles.txt')

COLLECTION_NAME = 'irpp_research'
MODEL_NAME = 'all-MiniLM-L6-v2'
BATCH_SIZE = 100

# --- HELPER & SETUP FUNCTIONS (No changes needed here) ---

def setup_logging() -> None:
    """Creates the log directory and clears the log file."""
    os.makedirs(LOG_DIR, exist_ok=True)
    open(LOG_FILE, 'w').close()

def log_message(message: str, level: str = 'INFO') -> None:
    """Logs a message to console and file.

    Args:
        message: Message to log.
        level: Log level (default: INFO).
    """
    log_entry = f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {level} - {message}"
    print(log_entry)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_entry + '\n')

def slugify(text: Any) -> str:
    """Creates a URL-friendly slug from text.

    Args:
        text: Input text.

    Returns:
        Slugified string.
    """
    text = str(text).lower().strip()
    text = re.sub(r'[\s-]+', '-', text)
    text = re.sub(r'[^\w-]', '', text)
    return text

def chunk_text(text: str, chunk_size: int = 350, overlap: int = 50) -> List[str]:
    """Splits text into overlapping chunks.

    Args:
        text: Input text.
        chunk_size: Size of each chunk in words.
        overlap: Overlap between chunks in words.

    Returns:
        List of text chunks.
    """
    words = text.split()
    if not words: return []
    return [' '.join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size - overlap)]

# CHANGED: Function now uses the passed-in connection object and PostgreSQL syntax.
def get_unindexed_articles(conn: psycopg2.extensions.connection) -> List[Dict[str, Any]]:
    """
    Fetches a batch of articles from the database that have not been indexed yet.

    Args:
        conn: Active database connection.

    Returns:
        List of dictionaries representing articles.
    """
    with conn.cursor() as cursor:
        # CHANGED: SQL parameter style from ? to %s
        cursor.execute("""
            SELECT id, link, title, summary 
            FROM articles 
            WHERE indexed_at IS NULL
            LIMIT %s
        """, (BATCH_SIZE,))
        articles = cursor.fetchall()
        # Convert list of tuples to list of dictionaries for easier access
        return [dict(zip([column[0] for column in cursor.description], row)) for row in articles]

# --- MAIN SCRIPT ---
# CHANGED: Main logic is wrapped in a function that accepts a connection.
def main(conn: psycopg2.extensions.connection) -> int:
    """Main execution logic for the article indexer.

    Args:
        conn: Active database connection.

    Returns:
        Total number of articles indexed.
    """
    setup_logging()
    log_message("--- Starting Article Indexing Process ---")
    
    try:
        log_message("Connecting to ChromaDB and loading model...")
        chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        collection = chroma_client.get_collection(name=COLLECTION_NAME)
        model = SentenceTransformer(MODEL_NAME)
        log_message("Initialization successful.")
    except Exception as e:
        log_message(f"FATAL: Failed to initialize ChromaDB or model. Error: {e}", "ERROR")
        return 0

    total_indexed_count = 0
    while True:
        log_message(f"Fetching a batch of up to {BATCH_SIZE} un-indexed articles...")
        articles_to_process = get_unindexed_articles(conn)
        
        if not articles_to_process:
            log_message("No new articles to index. Process is complete for this step.")
            break
            
        log_message(f"Found {len(articles_to_process)} articles to process in this batch.")
        
        for article in articles_to_process:
            article_id = article['id']
            article_link = article['link']
            
            text_to_embed = article.get('title', '')
            if article.get('summary'):
                text_to_embed += f"\n\n{article['summary']}"
            
            chunks = chunk_text(text_to_embed)

            if chunks:
                embeddings = model.encode(chunks, show_progress_bar=False).tolist()
                doc_id_prefix = slugify(article_link)
                ids = [f"{doc_id_prefix}#{i}" for i in range(len(chunks))]
                metadatas = [{"source_location": article_link, "article_db_id": article_id}] * len(chunks)
                
                try:
                    collection.add(embeddings=embeddings, documents=chunks, metadatas=metadatas, ids=ids)
                except Exception as e:
                    log_message(f"FAILED to add to ChromaDB for article {article_id}: {e}", "ERROR")

            try:
                with conn.cursor() as cursor:
                    cursor.execute("UPDATE articles SET indexed_at = CURRENT_TIMESTAMP WHERE id = %s", (article_id,))
                total_indexed_count += 1
            except psycopg2.Error as e:
                log_message(f"Failed to update database for article {article_id}: {e}", "ERROR")
                raise
            
            time.sleep(0.1) 

    log_message(f"\n--- Article Indexing Finished ---")
    log_message(f"Total articles marked as indexed in this run: {total_indexed_count}")

    return total_indexed_count


# This block allows the script to be run standalone for testing.
if __name__ == "__main__":
    connection = None
    print("--- Running index_articles.py standalone for testing ---")
    try:
        connection = get_db_connection()
        main(connection)
    except Exception as e:
        print(f"An error occurred during standalone execution: {e}")
    finally:
        if connection:
            connection.close()
            print("Standalone execution finished. Connection closed.")
