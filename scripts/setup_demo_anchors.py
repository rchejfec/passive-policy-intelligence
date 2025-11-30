#!/usr/bin/env python3
"""
Demo Anchor Setup Script

Prepares the database for G7 GovAI demo by:
1. Loading HyDE documents from JSON
2. Generating embeddings for HyDE documents
3. Creating DEMO: semantic anchors in PostgreSQL
4. Indexing HyDE embeddings to ChromaDB
5. Optionally deactivating PROG: anchors

Usage:
    python scripts/setup_demo_anchors.py --deactivate-prog
    python scripts/setup_demo_anchors.py --dry-run
"""

import os
import sys
import json
import argparse
import numpy as np
from datetime import datetime

# Add project root to path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from src.management.db_utils import get_db_connection
import chromadb
from sentence_transformers import SentenceTransformer

# Configuration
DATA_DIR = os.path.join(ROOT_DIR, 'data')
CHROMA_DB_PATH = os.path.join(DATA_DIR, 'chroma_db')
COLLECTION_NAME = 'irpp_research'
HYDE_DOCS_PATH = os.path.join(ROOT_DIR, 'user_content', 'demo_hyde_documents.json')
EMBEDDING_MODEL_NAME = 'sentence-transformers/all-MiniLM-L6-v2'


def load_hyde_documents():
    """Load HyDE documents from JSON file."""
    print(f"\n📄 Loading HyDE documents from: {HYDE_DOCS_PATH}")
    with open(HYDE_DOCS_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    anchors = data['demo_anchors']
    print(f"   ✓ Loaded {len(anchors)} demo anchor definitions")
    return anchors


def generate_embeddings(texts, model):
    """Generate embeddings for a list of texts."""
    print(f"\n🧮 Generating embeddings for {len(texts)} documents...")
    embeddings = model.encode(texts, show_progress_bar=True)
    print(f"   ✓ Generated embeddings with shape: {embeddings.shape}")
    return embeddings


def create_semantic_anchors(conn, anchors, dry_run=False):
    """Create DEMO: semantic anchors in PostgreSQL."""
    print(f"\n📊 Creating semantic anchors in PostgreSQL...")

    if dry_run:
        print("   [DRY RUN] Would create the following anchors:")
        for anchor in anchors:
            print(f"     - {anchor['name']}")
        return []

    created_ids = []
    with conn.cursor() as cursor:
        for anchor in anchors:
            cursor.execute("""
                INSERT INTO semantic_anchors
                    (name, anchor_author, is_active)
                VALUES (%s, %s, %s)
                RETURNING id
            """, (
                anchor['name'],
                anchor['author'],
                True
            ))
            anchor_id = cursor.fetchone()[0]
            created_ids.append(anchor_id)
            print(f"   ✓ Created anchor ID {anchor_id}: {anchor['name']}")

        conn.commit()

    return created_ids


def index_to_chromadb(anchors, embeddings, dry_run=False):
    """Index HyDE embeddings to ChromaDB collection."""
    print(f"\n💾 Indexing to ChromaDB collection '{COLLECTION_NAME}'...")

    if dry_run:
        print("   [DRY RUN] Would index the following to ChromaDB:")
        for i, anchor in enumerate(anchors):
            print(f"     - {anchor['name']}: {len(anchor['hyde_document'])} chars")
        return

    # Initialize ChromaDB
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    collection = client.get_or_create_collection(name=COLLECTION_NAME)

    # Prepare data for ChromaDB
    ids = []
    documents = []
    metadatas = []
    embeddings_list = []

    for i, anchor in enumerate(anchors):
        # Use a special ID format for HyDE documents
        doc_id = f"HYDE_{anchor['name'].replace('DEMO: ', '').replace(' ', '_').replace('&', 'and')}"
        ids.append(doc_id)
        documents.append(anchor['hyde_document'])
        metadatas.append({
            'source_type': 'hyde_anchor',
            'anchor_name': anchor['name'],
            'indexed_at': datetime.now().isoformat()
        })
        embeddings_list.append(embeddings[i].tolist())

    # Add to collection
    collection.add(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
        embeddings=embeddings_list
    )

    print(f"   ✓ Indexed {len(ids)} HyDE documents to ChromaDB")
    for doc_id in ids:
        print(f"     - {doc_id}")


def deactivate_prog_anchors(conn, dry_run=False):
    """Deactivate PROG: anchors for demo (reversible)."""
    print(f"\n⏸️  Deactivating PROG: anchors for demo...")

    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT id, name
            FROM semantic_anchors
            WHERE name LIKE 'PROG:%' AND is_active = true
        """)
        prog_anchors = cursor.fetchall()

    if not prog_anchors:
        print("   ℹ️  No active PROG: anchors found")
        return

    print(f"   Found {len(prog_anchors)} active PROG: anchors:")
    for anchor_id, name in prog_anchors:
        print(f"     - [{anchor_id}] {name}")

    if dry_run:
        print("   [DRY RUN] Would deactivate these anchors")
        return

    with conn.cursor() as cursor:
        cursor.execute("""
            UPDATE semantic_anchors
            SET is_active = false
            WHERE name LIKE 'PROG:%' AND is_active = true
        """)
        conn.commit()

    print(f"   ✓ Deactivated {len(prog_anchors)} PROG: anchors")
    print("   ℹ️  To reactivate later, run:")
    print("      UPDATE semantic_anchors SET is_active = true WHERE name LIKE 'PROG:%';")


def cleanup_existing_demo_anchors(conn, dry_run=False):
    """Remove any existing DEMO: anchors before creating new ones."""
    print(f"\n🧹 Checking for existing DEMO: anchors...")

    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT id, name
            FROM semantic_anchors
            WHERE name LIKE 'DEMO:%'
        """)
        existing = cursor.fetchall()

    if not existing:
        print("   ℹ️  No existing DEMO: anchors found")
        return

    print(f"   Found {len(existing)} existing DEMO: anchors:")
    for anchor_id, name in existing:
        print(f"     - [{anchor_id}] {name}")

    if dry_run:
        print("   [DRY RUN] Would delete these anchors")
        return

    # Delete anchor_components first (foreign key constraint)
    with conn.cursor() as cursor:
        cursor.execute("""
            DELETE FROM anchor_components
            WHERE anchor_id IN (
                SELECT id FROM semantic_anchors WHERE name LIKE 'DEMO:%'
            )
        """)

        cursor.execute("""
            DELETE FROM article_anchor_links
            WHERE anchor_id IN (
                SELECT id FROM semantic_anchors WHERE name LIKE 'DEMO:%'
            )
        """)

        cursor.execute("DELETE FROM semantic_anchors WHERE name LIKE 'DEMO:%'")
        conn.commit()

    print(f"   ✓ Deleted {len(existing)} existing DEMO: anchors and their relationships")


def main():
    parser = argparse.ArgumentParser(description='Setup demo anchors for G7 GovAI presentation')
    parser.add_argument('--deactivate-prog', action='store_true',
                       help='Deactivate PROG: anchors (reversible)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Preview actions without making changes')
    args = parser.parse_args()

    print("=" * 70)
    print("DEMO ANCHOR SETUP SCRIPT")
    print("=" * 70)
    print(f"Mode: {'DRY RUN (preview only)' if args.dry_run else 'EXECUTE'}")
    print(f"Deactivate PROG anchors: {'Yes' if args.deactivate_prog else 'No'}")
    print()

    # Connect to database
    conn = get_db_connection()
    print("✓ Connected to PostgreSQL database")

    try:
        # Load HyDE documents
        anchors = load_hyde_documents()

        # Initialize embedding model
        print(f"\n🤖 Loading embedding model: {EMBEDDING_MODEL_NAME}")
        model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        print("   ✓ Model loaded")

        # Generate embeddings
        hyde_texts = [anchor['hyde_document'] for anchor in anchors]
        embeddings = generate_embeddings(hyde_texts, model)

        # Cleanup existing demo anchors
        cleanup_existing_demo_anchors(conn, dry_run=args.dry_run)

        # Create semantic anchors
        anchor_ids = create_semantic_anchors(conn, anchors, dry_run=args.dry_run)

        # Index to ChromaDB
        index_to_chromadb(anchors, embeddings, dry_run=args.dry_run)

        # Optionally deactivate PROG anchors
        if args.deactivate_prog:
            deactivate_prog_anchors(conn, dry_run=args.dry_run)

        print("\n" + "=" * 70)
        if args.dry_run:
            print("DRY RUN COMPLETE - No changes were made")
            print("Run without --dry-run to execute")
        else:
            print("✅ DEMO SETUP COMPLETE")
            print(f"\nCreated {len(anchors)} demo anchors:")
            for anchor in anchors:
                print(f"  - {anchor['name']}")
            print(f"\nNext step: Re-run analysis on recent articles")
            print("  python scripts/reanalyze_for_demo.py --months 3")
        print("=" * 70)

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()
            print("\nDatabase connection closed")


if __name__ == "__main__":
    main()
