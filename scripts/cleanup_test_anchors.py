"""
Cleanup Script: Remove test anchor data from PostgreSQL and ChromaDB.

This script safely removes all data associated with semantic anchors that
do NOT start with "PROG:", which are test/development anchors.

Safety features:
- Dry-run mode by default
- Lists what will be deleted before executing
- Preserves all PROG: anchors and their data
- Maintains referential integrity
"""

import os
import sys
import argparse

# Add project root to path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from src.management.db_utils import get_db_connection

# Configuration (ChromaDB support commented out for now)
# DATA_DIR = os.path.join(ROOT_DIR, 'data')
# CHROMA_DB_PATH = os.path.join(DATA_DIR, 'chroma_db')
# COLLECTION_NAME = 'irpp_research'


def get_test_anchor_ids(conn):
    """Get IDs of all anchors that do NOT start with 'PROG:'."""
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT id, name, anchor_author
            FROM semantic_anchors
            WHERE name NOT LIKE 'PROG:%'
            ORDER BY name
        """)
        return cursor.fetchall()


def preview_deletion(conn, test_anchor_ids):
    """Show what will be deleted."""
    print("\n" + "="*70)
    print("DELETION PREVIEW")
    print("="*70)

    if not test_anchor_ids:
        print("\n✓ No test anchors found. Nothing to delete.")
        return False

    print(f"\nFound {len(test_anchor_ids)} test anchors to delete:")
    print("-" * 70)
    for anchor_id, name, author in test_anchor_ids:
        print(f"  [{anchor_id:3d}] {name}")
        print(f"        Author: {author or 'N/A'}")

    # Count affected records
    anchor_id_list = [aid for aid, _, _ in test_anchor_ids]

    with conn.cursor() as cursor:
        # Article-anchor links
        cursor.execute("""
            SELECT COUNT(*) FROM article_anchor_links
            WHERE anchor_id = ANY(%s)
        """, (anchor_id_list,))
        link_count = cursor.fetchone()[0]

        # Anchor components
        cursor.execute("""
            SELECT COUNT(*) FROM anchor_components
            WHERE anchor_id = ANY(%s)
        """, (anchor_id_list,))
        component_count = cursor.fetchone()[0]

        # Subscriptions
        cursor.execute("""
            SELECT COUNT(*) FROM subscriptions
            WHERE anchor_id = ANY(%s)
        """, (anchor_id_list,))
        subscription_count = cursor.fetchone()[0]

    print("\n" + "-" * 70)
    print("Records that will be deleted:")
    print(f"  - {len(test_anchor_ids)} semantic_anchors")
    print(f"  - {component_count} anchor_components")
    print(f"  - {link_count} article_anchor_links")
    print(f"  - {subscription_count} subscriptions")
    print("-" * 70)

    # Show what will be preserved
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT COUNT(*) FROM semantic_anchors
            WHERE name LIKE 'PROG:%'
        """)
        preserved_count = cursor.fetchone()[0]

    print(f"\n✓ {preserved_count} PROG: anchors will be PRESERVED")
    print("="*70 + "\n")

    return True


def delete_test_anchors(conn, test_anchor_ids, include_chroma=True):
    """Delete test anchor data from PostgreSQL (and optionally ChromaDB)."""
    if not test_anchor_ids:
        return

    anchor_id_list = [aid for aid, _, _ in test_anchor_ids]

    print("\nDeleting from PostgreSQL...")

    with conn.cursor() as cursor:
        # Delete in order to respect foreign key constraints

        # 1. Delete subscriptions (references semantic_anchors)
        print("  - Deleting subscriptions...")
        cursor.execute("""
            DELETE FROM subscriptions
            WHERE anchor_id = ANY(%s)
        """, (anchor_id_list,))
        print(f"    Deleted {cursor.rowcount} subscriptions")

        # 2. Delete article_anchor_links (references semantic_anchors)
        print("  - Deleting article_anchor_links...")
        cursor.execute("""
            DELETE FROM article_anchor_links
            WHERE anchor_id = ANY(%s)
        """, (anchor_id_list,))
        link_count = cursor.rowcount
        print(f"    Deleted {link_count} article_anchor_links")

        # 3. Delete anchor_components (references semantic_anchors)
        print("  - Deleting anchor_components...")
        cursor.execute("""
            DELETE FROM anchor_components
            WHERE anchor_id = ANY(%s)
        """, (anchor_id_list,))
        print(f"    Deleted {cursor.rowcount} anchor_components")

        # 4. Finally delete the anchors themselves
        print("  - Deleting semantic_anchors...")
        cursor.execute("""
            DELETE FROM semantic_anchors
            WHERE id = ANY(%s)
        """, (anchor_id_list,))
        print(f"    Deleted {cursor.rowcount} semantic_anchors")

    # Note: We DON'T delete articles themselves - they're still valuable data
    # We only removed the links between articles and test anchors

    if include_chroma:
        print("\nNote: ChromaDB cleanup not yet implemented.")
        print("Article embeddings remain in ChromaDB (safe to keep).")

    print("\n✓ PostgreSQL cleanup complete!")


def main():
    parser = argparse.ArgumentParser(
        description="Clean up test anchor data (anchors NOT starting with 'PROG:')"
    )
    parser.add_argument(
        '--execute',
        action='store_true',
        help='Actually perform deletion (default is dry-run preview only)'
    )
    parser.add_argument(
        '--no-chroma',
        action='store_true',
        help='Skip ChromaDB cleanup (PostgreSQL only)'
    )

    args = parser.parse_args()

    print("="*70)
    print("TEST ANCHOR CLEANUP SCRIPT")
    print("="*70)
    print("\nTarget: Anchors NOT starting with 'PROG:'")
    print("Preserves: All 'PROG:' anchors and their data")

    if not args.execute:
        print("\nMode: DRY RUN (preview only)")
        print("Use --execute to actually delete data")
    else:
        print("\nMode: EXECUTE (will delete data)")

    # Connect to database
    try:
        conn = get_db_connection()
        print("\n✓ Connected to PostgreSQL database")
    except Exception as e:
        print(f"\n✗ Failed to connect to database: {e}")
        return 1

    try:
        # Get test anchor IDs
        test_anchors = get_test_anchor_ids(conn)

        # Preview what will be deleted
        has_data = preview_deletion(conn, test_anchors)

        if not has_data:
            return 0

        if args.execute:
            # Confirm before deleting
            response = input("\nType 'DELETE' to confirm deletion: ")
            if response != 'DELETE':
                print("\nCancelled. No data was deleted.")
                return 0

            # Perform deletion
            delete_test_anchors(
                conn,
                test_anchors,
                include_chroma=not args.no_chroma
            )

            # Commit changes
            conn.commit()
            print("\n✓ Changes committed to database")

        else:
            print("\nDry run complete. No data was modified.")
            print("Run with --execute to actually delete this data.")

        return 0

    except Exception as e:
        print(f"\n✗ Error: {e}")
        if args.execute:
            conn.rollback()
            print("Changes rolled back.")
        return 1

    finally:
        conn.close()
        print("\nDatabase connection closed.")


if __name__ == "__main__":
    sys.exit(main())
