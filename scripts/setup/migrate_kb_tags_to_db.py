"""This script performs a one-time migration of thematic tags from the legacy
CSV file (`user_content/website_tags_kb.csv`) into the main SQLite database 
(`data/digest.db`)."""

# ==============================================================================
# One-Time Migration Script: Tags to SQLite
# ==============================================================================
#
# **Purpose:**
# This script performs a one-time migration of thematic tags from the legacy
# CSV file (`user_content/website_tags_kb.csv`) into the main SQLite
# database (`data/digest.db`).
#
# **Process:**
# 1. Reads the list of tags from the CSV.
# 2. Loads the `all-MiniLM-L6-v2` sentence transformer model.
# 3. Generates a 384-dimension embedding for each tag name.
# 4. Connects to the SQLite database.
# 5. Creates a new `tags` table if it doesn't already exist.
# 6. Inserts each tag, its category, and its serialized embedding into the table.
#
# **To Run:**
# `python scripts/setup/migrate_tags_to_db.py`
#
# ==============================================================================

import os
import sys
import sqlite3
import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer

def migrate_tags():
    """
    Main function to handle the migration process.
    """
    print("--- Starting Tag Migration Script ---")

    # --- 1. Define Paths and Configuration ---
    # Correctly set up paths to find project files from the script's location
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    ROOT_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR)) # Go up two levels
    
    # Add root to sys.path for potential future imports if needed
    if ROOT_DIR not in sys.path:
        sys.path.append(ROOT_DIR)

    DB_PATH = os.path.join(ROOT_DIR, 'data', 'digest.db')
    TAGS_CSV_PATH = os.path.join(ROOT_DIR, 'user_content', 'website_tags_kb.csv')
    MODEL_NAME = 'all-MiniLM-L6-v2'

    print(f"Database path: {DB_PATH}")
    print(f"Tags CSV path: {TAGS_CSV_PATH}")

    # --- 2. Load Source Data ---
    print("\n--- Loading source tags from CSV ---")
    if not os.path.exists(TAGS_CSV_PATH):
        print(f"❌ ERROR: Cannot find the source file at {TAGS_CSV_PATH}")
        return

    tags_df = pd.read_csv(TAGS_CSV_PATH)
    tags_df.dropna(subset=['Term Name'], inplace=True)

    # === FIX: Defensively handle the 'Term Category' column ===
    # Check if the column exists. If not, create it with a default value.
    if 'Term Category' not in tags_df.columns:
        print("Column 'Term Category' not found. Defaulting to 'Uncategorized'.")
        tags_df['Term Category'] = 'Uncategorized'
    else:
        # If the column does exist, fill any missing values.
        tags_df['Term Category'] = tags_df['Term Category'].fillna('Uncategorized')
    
    tags_to_process = tags_df[['Term Name', 'Term Category']].to_dict('records')
    print(f"Found {len(tags_to_process)} tags to process.")

    # --- 3. Load Model and Generate Embeddings ---
    print(f"\n--- Loading embedding model: {MODEL_NAME} ---")
    try:
        model = SentenceTransformer(MODEL_NAME)
    except Exception as e:
        print(f"❌ ERROR: Failed to load the SentenceTransformer model. Ensure it's installed.")
        print(e)
        return
    
    print("Generating embeddings for all tags...")
    tag_names = [tag['Term Name'] for tag in tags_to_process]
    tag_embeddings = model.encode(tag_names, show_progress_bar=True)
    print("Embeddings generated successfully.")

    # --- 4. Connect to DB and Create Table ---
    print("\n--- Connecting to SQLite database and setting up table ---")
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Use `CREATE TABLE IF NOT EXISTS` to make the script safely re-runnable.
        # no longer needed. now in setup_db 
        create_table_query = """
        CREATE TABLE IF NOT EXISTS tags (
            tag_name TEXT PRIMARY KEY,
            tag_category TEXT,
            embedding BLOB NOT NULL
        );
        """
        cursor.execute(create_table_query)
        print("`tags` table created or already exists.")

    except sqlite3.Error as e:
        print(f"❌ DATABASE ERROR: {e}")
        return

    # --- 5. Insert Data into Table ---
    print("\n--- Inserting tags and embeddings into the database ---")
    insert_count = 0
    for i, tag_data in enumerate(tags_to_process):
        tag_name = tag_data['Term Name']
        tag_category = tag_data['Term Category']
        # Serialize the numpy array to bytes (BLOB) for storage
        embedding_blob = tag_embeddings[i].astype(np.float32).tobytes()

        # Use `INSERT OR IGNORE` to prevent errors if a tag already exists.
        # This makes the script idempotent.
        insert_query = "INSERT OR IGNORE INTO tags (tag_name, tag_category, embedding) VALUES (?, ?, ?)"
        
        try:
            cursor.execute(insert_query, (tag_name, tag_category, embedding_blob))
            # The `rowcount` tells us if a row was actually inserted (1) or ignored (0).
            if cursor.rowcount > 0:
                insert_count += 1
        except sqlite3.Error as e:
            print(f"❌ DATABASE ERROR while inserting '{tag_name}': {e}")
            continue

    # Commit changes and close the connection
    conn.commit()
    conn.close()

    print(f"\n--- Migration Complete ---")
    print(f"✅ Successfully inserted {insert_count} new tags into the database.")
    if (len(tags_to_process) - insert_count) > 0:
        print(f"   (Skipped {len(tags_to_process) - insert_count} tags that already existed in the DB)")


if __name__ == "__main__":
    migrate_tags()
