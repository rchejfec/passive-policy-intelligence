# scripts/batch_create_anchors.py
"""
Bulk-imports semantic anchors from a JSON file.
"""

import json
import os
import sys
import logging
import re
import time
import requests
import chromadb
import fitz # PyMuPDF
from sentence_transformers import SentenceTransformer
import psycopg2

# Add src to path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.append(ROOT_DIR)

from src.ingestion.index_knowledge_base import get_text_from_source, create_requests_session, slugify
from src.analysis.dspy_utils import HyDEGenerator
from src.management.db_utils import get_db_connection

# Configuration
USER_CONTENT_DIR = os.path.join(ROOT_DIR, 'user_content')
INPUT_FILE = os.path.join(USER_CONTENT_DIR, 'new_anchors.json')
DATA_DIR = os.path.join(ROOT_DIR, 'data')
CHROMA_DB_PATH = os.path.join(DATA_DIR, 'chroma_db')
COLLECTION_NAME = 'irpp_research'
MODEL_NAME = 'all-MiniLM-L6-v2'

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def process_inputs(inputs, session):
    """
    Extracts and combines text from a list of inputs.
    """
    combined_text = []

    for item in inputs:
        inputType = item.get('type')
        value = item.get('value')

        logger.info(f"Processing input type: {inputType}, value: {value}")

        text = ""
        if inputType == 'url':
            # Use get_text_from_source logic.
            # Note: get_text_from_source expects 'web' or similar source_type for URLs
            text = get_text_from_source(session, value, 'web')

        elif inputType == 'file':
            # Use fitz directly for local files
            try:
                abs_path = os.path.join(ROOT_DIR, value)
                doc = fitz.open(abs_path)
                text = "".join(page.get_text() for page in doc)
                doc.close()
                text = ' '.join(text.split()) # Normalize whitespace
            except Exception as e:
                logger.error(f"Failed to read file {value}: {e}")

        elif inputType == 'text':
            text = value

        else:
            logger.warning(f"Unknown input type: {inputType}")

        if text:
            combined_text.append(text)

    return "\n\n".join(combined_text)

def main():
    logger.info("Starting batch anchor creation...")

    if not os.path.exists(INPUT_FILE):
        logger.error(f"Input file not found: {INPUT_FILE}")
        return

    try:
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            anchors = json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON: {e}")
        return

    # Initialize components
    session = create_requests_session()
    hyde_gen = HyDEGenerator()
    model = SentenceTransformer(MODEL_NAME)

    try:
        chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        collection = chroma_client.get_collection(name=COLLECTION_NAME)
    except Exception as e:
        logger.error(f"Failed to connect to ChromaDB: {e}")
        return

    conn = get_db_connection()

    for anchor in anchors:
        name = anchor.get('name')
        description = anchor.get('description')
        inputs = anchor.get('inputs', [])

        logger.info(f"Processing anchor: {name}")

        # 1. Extract Text
        raw_text = process_inputs(inputs, session)
        if not raw_text:
            logger.warning(f"No text extracted for anchor {name}. Skipping.")
            continue

        # 2. Synthesize (HyDE)
        # Split raw text into context list for HyDE generation
        context_list = [raw_text]  # Can be extended to multiple sources
        definition_string = hyde_gen.generate_hyde(context_list, name)
        if not definition_string:
            logger.warning(f"Empty definition string for anchor {name}. Skipping.")
            continue

        # 3. ChromaDB Storage
        anchor_slug = slugify(name)
        chroma_id = f"anchor_hyde_{anchor_slug}"

        # Generate embedding
        embedding = model.encode(definition_string).tolist()

        metadata = {
            'source_type': 'anchor_hyde',
            'name': name,
            'description': description
        }

        try:
            collection.upsert(
                ids=[chroma_id],
                embeddings=[embedding],
                documents=[definition_string],
                metadatas=[metadata]
            )
            logger.info(f"Upserted vector document {chroma_id} to ChromaDB.")
        except Exception as e:
            logger.error(f"Failed to upsert to ChromaDB: {e}")
            continue

        # 4. SQL Linking
        try:
            with conn.cursor() as cursor:
                # Insert into semantic_anchors
                cursor.execute("""
                    INSERT INTO semantic_anchors (name, description, is_active)
                    VALUES (%s, %s, true)
                    RETURNING id
                """, (name, description))
                anchor_id = cursor.fetchone()[0]

                # Insert into anchor_components
                cursor.execute("""
                    INSERT INTO anchor_components (anchor_id, component_type, component_id)
                    VALUES (%s, 'chroma_doc', %s)
                """, (anchor_id, chroma_id))

            conn.commit()
            logger.info(f"Created SQL records for anchor {name} (ID: {anchor_id}).")

        except psycopg2.Error as e:
            conn.rollback()
            logger.error(f"Database error for anchor {name}: {e}")

    conn.close()
    logger.info("Batch anchor creation complete.")

if __name__ == "__main__":
    main()
