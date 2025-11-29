# -*- coding: utf-8 -*-
# src/ingestion/index_knowledge_base.py (Refactored for Orchestrator)
"""
Indexes content from the knowledge base into ChromaDB and the main database.

This script reads the definitive 'knowledge_base.csv' manifest and populates
the databases. It uses a robust, two-stage process:
1. It processes unique documents (by URL/path) to ensure content is fetched
   and embedded only once.
2. It processes the full manifest to populate the relational database,
   correctly handling many-to-many relationships between documents and programs.
"""
import csv
import os
import time
import random
import re
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
import fitz
from sentence_transformers import SentenceTransformer
import chromadb
import psycopg2 # CHANGED: For error handling

# CHANGED: This import is now only used when the script is run standalone for testing.
from src.management.db_utils import get_db_connection

# --- CONFIGURATION ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Assuming the script is in 'src/ingestion', we go up two levels for the root
ROOT_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR)) 
USER_CONTENT_DIR = os.path.join(ROOT_DIR, 'user_content')
DATA_DIR = os.path.join(ROOT_DIR, 'data')
LOG_DIR = os.path.join(ROOT_DIR, 'logs')
KNOWLEDGE_BASE_CSV = os.path.join(USER_CONTENT_DIR, 'knowledge_base.csv')
SQLITE_DB_PATH = os.path.join(DATA_DIR, 'digest.db')
CHROMA_DB_PATH = os.path.join(DATA_DIR, 'chroma_db')
LOG_FILE = os.path.join(LOG_DIR, 'indexing_log_kb.txt')
FAILED_URL_LOG = os.path.join(USER_CONTENT_DIR, 'failed_indexing_kb.csv')
COLLECTION_NAME = 'irpp_research'
MODEL_NAME = 'all-MiniLM-L6-v2'
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36',
]

# --- HELPER & SETUP FUNCTIONS ---

def slugify(text):
    """Converts a string into a URL-friendly slug."""
    text = str(text).lower().strip()
    text = re.sub(r'[\s-]+', '-', text)
    text = re.sub(r'[^\w-]', '', text)
    return text

def setup_logging():
    os.makedirs(LOG_DIR, exist_ok=True)
    open(LOG_FILE, 'w').close()
    with open(FAILED_URL_LOG, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['timestamp', 'url', 'error_message'])

def log_message(message, level='INFO'):
    log_entry = f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {level} - {message}"
    print(log_entry)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_entry + '\n')

def log_failure(url, error_message):
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    with open(FAILED_URL_LOG, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([timestamp, url, str(error_message)])

def create_requests_session():
    session = requests.Session()
    session.headers.update({'User-Agent': random.choice(USER_AGENTS)})
    retry = Retry(total=3, read=3, connect=3, backoff_factor=0.5, status_forcelist=(500, 502, 503, 504))
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

def get_text_from_source(session, url, source_type):
    """
    Fetches text content based on the source type.
    **FIX #2**: This function now correctly handles 'program_charter' and 'draft' types.
    """
    text = None
    try:
        if source_type in ['web', 'oped', 'program_home']:
            log_message(f"Fetching web content for {url}...")
            jina_url = f"https://r.jina.ai/{url}"
            response = session.get(jina_url, timeout=45)
            response.raise_for_status()
            text = response.text.strip()
            
        elif source_type == 'pdf':
            log_message(f"Fetching PDF content for {url}...")
            if url.startswith('http'):
                response = session.get(url, timeout=45)
                response.raise_for_status()
                doc = fitz.open(stream=response.content, filetype="pdf")
            else:
                abs_file_path = os.path.join(ROOT_DIR, url)
                doc = fitz.open(abs_file_path)
            
            full_text = "".join(page.get_text() for page in doc)
            doc.close()
            text = ' '.join(full_text.split())

        elif source_type in ['draft', 'program_charter']:
            log_message(f"Fetching local text file for {url}...")
            abs_file_path = os.path.join(ROOT_DIR, url)
            with open(abs_file_path, 'r', encoding='utf-8') as f:
                text = f.read()

    except Exception as e:
        log_message(f"Failed to get content for {url}: {e}", 'ERROR')
        log_failure(url, e)
        return None
        
    log_message(f"Successfully retrieved content for {url}.")
    return text

def chunk_text(text, chunk_size=350, overlap=50):
    words = text.split()
    if not words: return []
    return [' '.join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size - overlap)]

# --- REFACTORED MAIN SCRIPT ---

def main(conn):
    """Main execution logic for the knowledge base indexer."""
    setup_logging()
    log_message("--- Starting Knowledge Base Indexing Process ---")
    
    session = create_requests_session()
    model = SentenceTransformer(MODEL_NAME)
    
    try:
        chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        collection = chroma_client.get_collection(name=COLLECTION_NAME)
        log_message(f"Successfully connected to ChromaDB collection '{COLLECTION_NAME}'.")
    except Exception as e:
        log_message(f"FATAL: Could not get ChromaDB collection '{COLLECTION_NAME}'. Error: {e}", "ERROR")
        return
    
    try:
        with open(KNOWLEDGE_BASE_CSV, mode='r', encoding='utf-8') as infile:
            manifest = list(csv.DictReader(infile))
    except FileNotFoundError:
        log_message(f"FATAL: Knowledge base file not found at {KNOWLEDGE_BASE_CSV}", 'ERROR')
        return

    # **FIX #1: The Duplication Fix**
    # --- STAGE 1: Process and embed UNIQUE documents into ChromaDB ---
    log_message("--- Stage 1: Processing unique documents for ChromaDB ---")
    unique_docs = {row['source_location']: row for row in manifest}.values()
    log_message(f"Found {len(unique_docs)} unique documents to process.")

    for doc_info in unique_docs:
        url = doc_info['source_location']
        
        existing_docs = collection.get(where={"source_location": url})
        if existing_docs['ids']:
            log_message(f"-> Document {url} already in ChromaDB. Skipping content processing.")
            continue

        log_message(f"-> New document: {url}. Fetching and embedding...")
        text = get_text_from_source(session, url, doc_info['source_type'])
        if not text:
            time.sleep(1)
            continue

        chunks = chunk_text(text)
        if not chunks:
            log_message(f"Text from {url} resulted in zero chunks. Skipping.", 'WARNING')
            continue
            
        embeddings = model.encode(chunks).tolist()
        
        # Deterministic IDs are based only on the URL/path, not the program
        doc_id_prefix = slugify(url)
        ids = [f"{doc_id_prefix}#{i}" for i in range(len(chunks))]
        
        # Minimal metadata for ChromaDB, only what's intrinsic to the content
        metadatas = [{"source_location": url, "product_name": doc_info['product_name']}] * len(chunks)

        collection.add(embeddings=embeddings, documents=chunks, metadatas=metadatas, ids=ids)
        log_message(f"-> SUCCESS: Added {len(chunks)} chunks for {url}.")
        time.sleep(1)

  # --- STAGE 2: Populate database with the full relational data from the manifest ---
    log_message("\n--- Stage 2: Populating database with program relationships ---")
    try:
        # Use the passed-in connection object
        with conn.cursor() as cursor:
            for row in manifest:
                # CHANGED: Using INSERT ... ON CONFLICT (id) DO NOTHING for PostgreSQL
                # This is the equivalent of SQLite's INSERT OR IGNORE for a primary key.
                cursor.execute("""
                    INSERT INTO knowledge_base (id, source_location, source_type, program_tag, program_name, status, initiative_type, product_name)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO NOTHING
                """, (
                    row['id'], row['source_location'], row['source_type'], row['program_tag'], row['program_name'],
                    row['status'], row['initiative_type'], row['product_name']
                ))
        log_message("-> SUCCESS: Database knowledge_base table populated.")
    except psycopg2.Error as e:
        log_message(f"ERROR during database population: {e}", "ERROR")
        # Let the orchestrator handle rollback
        raise

    log_message("\n--- Knowledge Base Indexing Complete ---")

# This block allows the script to be run standalone for testing
if __name__ == "__main__":
    connection = None
    print("--- Running index_knowledge_base.py standalone for testing ---")
    try:
        connection = get_db_connection()
        main(connection)
        # Standalone run should commit its own transaction
        connection.commit()
    except Exception as e:
        print(f"An error occurred during standalone execution: {e}")
        if connection:
            connection.rollback()
    finally:
        if connection:
            connection.close()
            print("Standalone execution finished. Connection closed.")