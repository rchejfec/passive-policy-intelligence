"""
Cleanup Script: Remove duplicate article-anchor links.

This script identifies and removes duplicate entries where the same article
is linked to the same anchor multiple times (based on matching title).

Strategy:
- Within each anchor, find articles with duplicate titles
- Keep the link with the HIGHEST similarity score
- Delete the duplicates

Safety features:
- Dry-run mode by default
- Shows duplicates before deleting
- Preserves highest-scoring link
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


def find_duplicate_links(conn):
    """
    Find duplicate article-anchor links where articles have same title
    within the same anchor.

    Returns:
        List of tuples: (link_id_to_delete, article_id, anchor_id, title, score)
    """
    with conn.cursor() as cursor:
        # Find duplicates: same title + same anchor, keep highest score
        cursor.execute("""
            WITH ranked_links AS (
                SELECT
                    aal.id as link_id,
                    aal.article_id,
                    aal.anchor_id,
                    a.title,
                    aal.similarity_score,
                    sa.name as anchor_name,
                    ROW_NUMBER() OVER (
                        PARTITION BY aal.anchor_id, a.title
                        ORDER BY aal.similarity_score DESC, aal.id ASC
                    ) as rank
                FROM article_anchor_links aal
                JOIN articles a ON aal.article_id = a.id
                JOIN semantic_anchors sa ON aal.anchor_id = sa.id
            )
            SELECT
                link_id,
                article_id,
                anchor_id,
                anchor_name,
                title,
                similarity_score,
                rank
            FROM ranked_links
            WHERE rank > 1
            ORDER BY anchor_id, title, rank
        """)

        duplicates = cursor.fetchall()

    return duplicates


def preview_duplicate_deletion(conn):
    """Show what duplicate links will be deleted."""
    print("\n" + "="*80)
    print("DUPLICATE LINK DELETION PREVIEW")
    print("="*80)

    duplicates = find_duplicate_links(conn)

    if not duplicates:
        print("\n✓ No duplicate links found. Database is clean!")
        return False

    print(f"\nFound {len(duplicates)} duplicate links to remove:")
    print("-" * 80)

    # Group by anchor for clearer display
    current_anchor = None
    current_title = None
    duplicate_count_by_anchor = {}

    for link_id, article_id, anchor_id, anchor_name, title, score, rank in duplicates:
        duplicate_count_by_anchor[anchor_name] = duplicate_count_by_anchor.get(anchor_name, 0) + 1

        if anchor_name != current_anchor:
            if current_anchor is not None:
                print()  # Blank line between anchors
            current_anchor = anchor_name
            current_title = None
            print(f"\nAnchor: {anchor_name} (ID: {anchor_id})")
            print("  " + "-" * 76)

        if title != current_title:
            current_title = title
            print(f"\n  Duplicate article: '{title[:60]}{'...' if len(title) > 60 else ''}'")

        print(f"    → DELETE Link ID {link_id:5d} (Article {article_id:5d}, Score: {score:.4f}, Rank: {rank})")

    print("\n" + "-" * 80)
    print("\nSummary by anchor:")
    for anchor_name, count in sorted(duplicate_count_by_anchor.items()):
        print(f"  - {anchor_name}: {count} duplicate(s)")

    print("\n" + "=" * 80)
    print(f"\nTotal duplicate links to delete: {len(duplicates)}")
    print("="*80 + "\n")

    return True


def delete_duplicate_links(conn):
    """Delete duplicate article-anchor links, keeping highest score."""
    duplicates = find_duplicate_links(conn)

    if not duplicates:
        return 0

    link_ids_to_delete = [dup[0] for dup in duplicates]

    print("\nDeleting duplicate links from PostgreSQL...")

    with conn.cursor() as cursor:
        cursor.execute("""
            DELETE FROM article_anchor_links
            WHERE id = ANY(%s)
        """, (link_ids_to_delete,))

        deleted_count = cursor.rowcount

    print(f"  ✓ Deleted {deleted_count} duplicate links")

    return deleted_count


def verify_cleanup(conn):
    """Verify that no duplicates remain."""
    print("\nVerifying cleanup...")

    with conn.cursor() as cursor:
        # Check for any remaining duplicates
        cursor.execute("""
            SELECT anchor_id, a.title, COUNT(*) as dup_count
            FROM article_anchor_links aal
            JOIN articles a ON aal.article_id = a.id
            GROUP BY anchor_id, a.title
            HAVING COUNT(*) > 1
        """)

        remaining_dups = cursor.fetchall()

    if remaining_dups:
        print(f"  ⚠ WARNING: {len(remaining_dups)} duplicate groups still exist!")
        for anchor_id, title, count in remaining_dups[:5]:
            print(f"    - Anchor {anchor_id}: '{title[:50]}...' ({count} copies)")
        return False
    else:
        print("  ✓ No duplicates found - database is clean!")
        return True


def main():
    parser = argparse.ArgumentParser(
        description="Remove duplicate article-anchor links (same title + same anchor)"
    )
    parser.add_argument(
        '--execute',
        action='store_true',
        help='Actually perform deletion (default is dry-run preview only)'
    )

    args = parser.parse_args()

    print("="*80)
    print("DUPLICATE LINK CLEANUP SCRIPT")
    print("="*80)
    print("\nStrategy: Keep link with HIGHEST similarity score per (anchor, title) pair")

    if not args.execute:
        print("\nMode: DRY RUN (preview only)")
        print("Use --execute to actually delete duplicates")
    else:
        print("\nMode: EXECUTE (will delete duplicates)")

    # Connect to database
    try:
        conn = get_db_connection()
        print("\n✓ Connected to PostgreSQL database")
    except Exception as e:
        print(f"\n✗ Failed to connect to database: {e}")
        return 1

    try:
        # Preview what will be deleted
        has_duplicates = preview_duplicate_deletion(conn)

        if not has_duplicates:
            return 0

        if args.execute:
            # Confirm before deleting
            response = input("\nType 'DELETE' to confirm removal of duplicates: ")
            if response != 'DELETE':
                print("\nCancelled. No data was deleted.")
                return 0

            # Perform deletion
            deleted_count = delete_duplicate_links(conn)

            # Commit changes
            conn.commit()
            print(f"\n✓ Changes committed to database ({deleted_count} links deleted)")

            # Verify
            verify_cleanup(conn)

        else:
            print("\nDry run complete. No data was modified.")
            print("Run with --execute to actually delete duplicates.")

        return 0

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        if args.execute:
            conn.rollback()
            print("\nChanges rolled back.")
        return 1

    finally:
        conn.close()
        print("\nDatabase connection closed.")


if __name__ == "__main__":
    sys.exit(main())
