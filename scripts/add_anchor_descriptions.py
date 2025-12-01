"""
Add HyDE document descriptions to demo semantic anchors.

This script updates the anchor descriptions in the database with the first 300
characters of their HyDE documents for display on the Sources page.
"""

import os
import sys
import json

# Path setup
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from src.management.db_utils import get_db_connection

# Load HyDE documents
HYDE_FILE = os.path.join(ROOT_DIR, 'user_content', 'demo_hyde_documents.json')

def truncate_text(text: str, max_length: int = 300) -> str:
    """Truncate text to max_length, breaking at sentence boundary if possible."""
    if len(text) <= max_length:
        return text

    # Try to break at sentence boundary
    truncated = text[:max_length]
    last_period = truncated.rfind('. ')

    if last_period > max_length * 0.7:  # If we can break at a sentence within 70% of max length
        return truncated[:last_period + 1]
    else:
        return truncated.rstrip() + '...'

def main():
    print("=" * 60)
    print("Adding HyDE Document Descriptions to Semantic Anchors")
    print("=" * 60)

    # Load HyDE documents
    with open(HYDE_FILE, 'r', encoding='utf-8') as f:
        hyde_data = json.load(f)

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        for anchor in hyde_data['demo_anchors']:
            name = anchor['name']
            hyde_doc = anchor['hyde_document']

            # Truncate to first ~300 characters for description
            description = truncate_text(hyde_doc, 300)

            # Update description in database
            cursor.execute("""
                UPDATE semantic_anchors
                SET description = %s
                WHERE name = %s
                RETURNING id, name
            """, (description, name))

            result = cursor.fetchone()
            if result:
                print(f"[OK] Updated: {result[1]}")
                print(f"     Description: {description[:80]}...")
            else:
                print(f"[SKIP] Anchor not found: {name}")

        conn.commit()
        print("\n" + "=" * 60)
        print("[OK] Descriptions updated successfully")
        print("=" * 60)
        print("\nNext step: Run export script to update parquet files")
        print("  python scripts/export_to_parquet.py --demo-only")

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"\n[ERROR] Update failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        if conn:
            cursor.close()
            conn.close()

if __name__ == "__main__":
    main()
