# --- setup/setup_database.py (Refactored for PostgreSQL) ---

"""
Initializes and updates the master Azure PostgreSQL database schema.

This script is designed to be idempotent. It can be run at any time to create 
the database schema if it doesn't exist.
"""

import psycopg2
import csv
import os
import sys
from dotenv import load_dotenv

# --- Path Setup ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(PROJECT_ROOT)

# CHANGED: ChromaDB is initialized separately now, but pathing may be useful.
# from src.management.system_manager import initialize_chroma_db

# --- Configuration ---
# CHANGED: Load environment variables from .env file
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))
DATABASE_URL = os.getenv("DATABASE_URL")

SETUP_FOLDER = os.path.join(PROJECT_ROOT, 'scripts', 'setup')
CSV_FILE = os.path.join(SETUP_FOLDER, 'ConsolidatedRSSFeeds.csv')


# --- SQL Schema Definitions (PostgreSQL Dialect) ---

### --- Foundational Tables --- ###

CREATE_SOURCES_TABLE = """
CREATE TABLE IF NOT EXISTS sources (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    site_url TEXT,
    feed_url TEXT,
    social_feed_url TEXT,
    ga_feed_url TEXT,
    category TEXT,
    tags TEXT,
    bias_lean TEXT,
    notes TEXT,
    is_active BOOLEAN DEFAULT true,
    last_fetched TIMESTAMP
);
"""

CREATE_ARTICLES_TABLE = """
CREATE TABLE IF NOT EXISTS articles (
    id SERIAL PRIMARY KEY,
    source_id INTEGER,
    title TEXT,
    link TEXT NOT NULL UNIQUE,
    summary TEXT,
    published_date TIMESTAMP,
    retrieved_from_url TEXT,
    status TEXT DEFAULT 'new',
    is_flagged BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    indexed_at TIMESTAMP,
    analyzed_at TIMESTAMP,
    enrichment_processed_at TIMESTAMP,
    is_org_highlight BOOLEAN DEFAULT false,
    newsletter_sent_at TIMESTAMP,
    FOREIGN KEY (source_id) REFERENCES sources (id)
);
"""

CREATE_KB_TABLE = """
CREATE TABLE IF NOT EXISTS knowledge_base (
    id SERIAL PRIMARY KEY,
    source_location TEXT,
    source_type TEXT,
    program_tag TEXT,
    program_name TEXT,
    status TEXT,
    initiative_type TEXT,
    product_name TEXT,
    UNIQUE(source_location, program_tag)
);
"""

CREATE_TAGS_TABLE = """
CREATE TABLE IF NOT EXISTS tags (
    tag_name TEXT PRIMARY KEY,
    tag_category TEXT,
    embedding BYTEA NOT NULL
);
"""

### --- Core Engine Blueprint Tables --- ###

CREATE_SEMANTIC_ANCHORS_TABLE = """
CREATE TABLE IF NOT EXISTS semantic_anchors (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    anchor_author TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_ANCHOR_COMPONENTS_TABLE = """
CREATE TABLE IF NOT EXISTS anchor_components (
    id SERIAL PRIMARY KEY,
    anchor_id INTEGER NOT NULL,
    component_type TEXT NOT NULL,
    component_id TEXT NOT NULL,
    FOREIGN KEY (anchor_id) REFERENCES semantic_anchors (id) ON DELETE CASCADE
);
"""

# MODIFIED: Added new highlight columns for enrichment workflow
CREATE_ARTICLE_ANCHOR_LINKS_TABLE = """
CREATE TABLE IF NOT EXISTS article_anchor_links (
    id SERIAL PRIMARY KEY,
    article_id INTEGER NOT NULL,
    anchor_id INTEGER NOT NULL,
    similarity_score REAL NOT NULL,
    linked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_anchor_highlight BOOLEAN,
    is_org_highlight BOOLEAN,
    FOREIGN KEY (article_id) REFERENCES articles (id) ON DELETE CASCADE,
    FOREIGN KEY (anchor_id) REFERENCES semantic_anchors (id)
);
"""

### --- Delivery Layer Blueprint Tables --- ###

CREATE_SUBSCRIBERS_TABLE = """
CREATE TABLE IF NOT EXISTS subscribers (
    id SERIAL PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_SUBSCRIPTIONS_TABLE = """
CREATE TABLE IF NOT EXISTS subscriptions (
    id SERIAL PRIMARY KEY,
    subscriber_id INTEGER NOT NULL,
    anchor_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (subscriber_id) REFERENCES subscribers (id) ON DELETE CASCADE,
    FOREIGN KEY (anchor_id) REFERENCES semantic_anchors (id) ON DELETE CASCADE,
    UNIQUE(subscriber_id, anchor_id)
);
"""

# REMOVED: SQLite-specific helper functions (add_column_if_not_exists, _recreate_article_anchor_links_without_cascade)
# are no longer needed for a direct PostgreSQL setup.

# --- Main Functions ---
 
def update_schema(conn):
    """
    Creates all tables if they don't exist in the PostgreSQL database.
    """
    print("--- Applying database schema... ---")
    cursor = conn.cursor()

    # Create all tables using IF NOT EXISTS
    print("Creating tables if they do not exist...")
    # Foundational Tables
    cursor.execute(CREATE_SOURCES_TABLE)
    cursor.execute(CREATE_ARTICLES_TABLE)
    cursor.execute(CREATE_KB_TABLE)
    cursor.execute(CREATE_TAGS_TABLE)

    # Core Engine Tables
    cursor.execute(CREATE_SEMANTIC_ANCHORS_TABLE)
    cursor.execute(CREATE_ANCHOR_COMPONENTS_TABLE)
    cursor.execute(CREATE_ARTICLE_ANCHOR_LINKS_TABLE)

    # Delivery Layer Tables
    cursor.execute(CREATE_SUBSCRIBERS_TABLE)
    cursor.execute(CREATE_SUBSCRIPTIONS_TABLE)
    
    conn.commit()
    cursor.close()
    print("--- Schema update complete. ---")


def populate_sources_from_csv(conn):
    """Reads the consolidated CSV and populates the 'sources' table if it's empty."""
    print("\n--- Checking 'sources' table population... ---")
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT COUNT(*) FROM sources")
        if cursor.fetchone()[0] > 0:
            print("'sources' table is already populated. Skipping insertion.")
            return

        print(f"Table is empty. Reading sources from {CSV_FILE}...")
        with open(CSV_FILE, mode='r', encoding='utf-8') as infile:
            reader = csv.DictReader(infile)
            sources_to_add = [tuple(row.get(key, '').strip() for key in ['Source Name', 'Site URL', 'Feed URL', 'Socials Feed URL', 'GA Feed URL', 'Category', 'Tags', 'Bias / Lean', 'Notes'])]
        
        if not sources_to_add:
            print("No sources found in CSV file.")
            return

        print(f"Found {len(sources_to_add)} sources to add. Inserting into database...")
        
        # CHANGED: Parameter style from '?' to '%s' for psycopg2
        insert_query = """
            INSERT INTO sources (name, site_url, feed_url, social_feed_url, ga_feed_url, category, tags, bias_lean, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.executemany(insert_query, sources_to_add)

        conn.commit()
        print("Successfully populated the 'sources' table.")

    except FileNotFoundError:
        print(f"Error: The file {CSV_FILE} was not found.")
    except Exception as e:
        conn.rollback()
        print(f"An unexpected error occurred during population: {e}")
    finally:
        cursor.close()

# --- Main Execution ---

if __name__ == "__main__":
    print("--- Running Database Schema Setup/Update for PostgreSQL ---")
    
    if not DATABASE_URL:
        print("FATAL ERROR: DATABASE_URL is not set in the .env file.")
        sys.exit(1)

    connection = None
    try:
        # CHANGED: Connect to PostgreSQL using the DATABASE_URL
        connection = psycopg2.connect(DATABASE_URL)
        
        update_schema(connection)
        # populate_sources_from_csv(connection)

    except psycopg2.Error as e:
        print(f"DATABASE ERROR: {e}")
    finally:
        if connection:
            connection.close()
        print("\n--- Database schema setup/update process complete. ---")
        
    # REMOVED: ChromaDB initialization should be handled by a separate process.
    # initialize_chroma_db()