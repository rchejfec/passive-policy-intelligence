#!/usr/bin/env python3
"""
Demo Cleanup Script

Prepares database for demo by:
1. Creating normalized score view (0-1 scale, dynamic max per anchor)
2. Updating source categories from CSV file

Usage:
    python scripts/demo_cleanup.py --update-categories sources_for_recategorization.csv
    python scripts/demo_cleanup.py --create-normalized-view
    python scripts/demo_cleanup.py --all sources_for_recategorization.csv
"""

import os
import sys
import csv
import argparse

# Add project root to path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from src.management.db_utils import get_db_connection


def create_normalized_score_view(conn, dry_run=False):
    """Create a view with normalized similarity scores (0-1 scale)."""
    print("\n" + "=" * 70)
    print("CREATING NORMALIZED SCORE VIEW")
    print("=" * 70)

    view_sql = """
        CREATE OR REPLACE VIEW article_anchor_links_normalized AS
        SELECT
            aal.id,
            aal.article_id,
            aal.anchor_id,
            aal.similarity_score,
            aal.linked_at,
            aal.is_org_highlight,
            aal.is_anchor_highlight,
            CASE
                WHEN anchor_max.max_score > 0 THEN
                    GREATEST(0, aal.similarity_score) / anchor_max.max_score
                ELSE 0
            END AS normalized_score
        FROM article_anchor_links aal
        CROSS JOIN LATERAL (
            SELECT MAX(similarity_score) as max_score
            FROM article_anchor_links
            WHERE anchor_id = aal.anchor_id
        ) anchor_max
    """

    if dry_run:
        print("\n[DRY RUN] Would create view with SQL:")
        print(view_sql)
        return

    with conn.cursor() as cursor:
        cursor.execute(view_sql)
        conn.commit()

    print("\n✓ Created view: article_anchor_links_normalized")
    print("  - Normalized scores: 0 to 1 (0 = worst, 1 = best per anchor)")
    print("  - Negatives clamped to 0")
    print("  - Dynamic max: recalculates per anchor on each query")

    # Test the view
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT
                sa.name,
                COUNT(*) as link_count,
                MIN(aaln.similarity_score) as min_raw,
                MAX(aaln.similarity_score) as max_raw,
                MIN(aaln.normalized_score) as min_norm,
                MAX(aaln.normalized_score) as max_norm
            FROM article_anchor_links_normalized aaln
            JOIN semantic_anchors sa ON aaln.anchor_id = sa.id
            WHERE sa.name LIKE 'DEMO:%'
            GROUP BY sa.name
            ORDER BY sa.name
        """)

        print("\n" + "=" * 70)
        print("VERIFICATION (DEMO Anchors)")
        print("=" * 70)
        print(f"{'Anchor Name':<50s} | {'Links':>6s} | {'Raw Range':>15s} | {'Norm Range':>15s}")
        print("-" * 90)

        for name, count, min_raw, max_raw, min_norm, max_norm in cursor.fetchall():
            raw_range = f"{min_raw:.3f} to {max_raw:.3f}"
            norm_range = f"{min_norm:.3f} to {max_norm:.3f}"
            print(f"{name:<50s} | {count:>6,d} | {raw_range:>15s} | {norm_range:>15s}")


def update_source_categories(conn, csv_path, dry_run=False):
    """Update source categories from CSV file."""
    print("\n" + "=" * 70)
    print("UPDATING SOURCE CATEGORIES")
    print("=" * 70)

    if not os.path.exists(csv_path):
        print(f"\n❌ ERROR: File not found: {csv_path}")
        return

    # Read CSV
    updates = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        # Check which column name was used
        fieldnames = reader.fieldnames
        category_col = None
        for col in ['FINAL CATEGORY', 'new_category', 'final_category']:
            if col in fieldnames:
                category_col = col
                break

        if not category_col:
            raise ValueError(f"Could not find category column. Available columns: {fieldnames}")

        print(f"Using category column: '{category_col}'")

        for row in reader:
            source_id = int(row['source_id'])
            new_category = row[category_col].strip()
            if new_category:  # Only update if new_category is specified
                updates.append((new_category, source_id))

    if not updates:
        print("\n⚠️  No updates found in CSV (new_category column is empty)")
        return

    print(f"\nFound {len(updates):,} sources to update")

    # Get category statistics
    category_counts = {}
    for new_cat, _ in updates:
        category_counts[new_cat] = category_counts.get(new_cat, 0) + 1

    print("\nNew category distribution:")
    for cat, count in sorted(category_counts.items()):
        print(f"  {cat:<30s}: {count:>6,d} sources")

    if dry_run:
        print("\n[DRY RUN] Would update source categories")
        return

    # Perform updates
    with conn.cursor() as cursor:
        cursor.executemany("""
            UPDATE sources
            SET category = %s
            WHERE id = %s
        """, updates)
        conn.commit()

    print(f"\n✓ Updated {len(updates):,} source categories")

    # Verify
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT category, COUNT(*) as count
            FROM sources
            WHERE category IS NOT NULL
            GROUP BY category
            ORDER BY count DESC
        """)

        print("\n" + "=" * 70)
        print("VERIFICATION (All Categories)")
        print("=" * 70)
        print(f"{'Category':<30s} | {'Count':>10s}")
        print("-" * 44)

        for category, count in cursor.fetchall():
            print(f"{category:<30s} | {count:>10,d}")


def main():
    parser = argparse.ArgumentParser(description='Demo cleanup: normalize scores and update categories')
    parser.add_argument('--create-normalized-view', action='store_true',
                       help='Create normalized score view')
    parser.add_argument('--update-categories', type=str, metavar='CSV_FILE',
                       help='Update source categories from CSV file')
    parser.add_argument('--all', type=str, metavar='CSV_FILE',
                       help='Run all cleanup tasks (view + categories)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Preview actions without making changes')
    args = parser.parse_args()

    if not any([args.create_normalized_view, args.update_categories, args.all]):
        parser.print_help()
        return

    print("=" * 70)
    print("DEMO CLEANUP SCRIPT")
    print("=" * 70)
    print(f"Mode: {'DRY RUN (preview only)' if args.dry_run else 'EXECUTE'}")
    print()

    # Connect to database
    conn = get_db_connection()
    print("✓ Connected to PostgreSQL database")

    try:
        if args.all:
            # Run all tasks
            create_normalized_score_view(conn, dry_run=args.dry_run)
            update_source_categories(conn, args.all, dry_run=args.dry_run)
        else:
            # Run individual tasks
            if args.create_normalized_view:
                create_normalized_score_view(conn, dry_run=args.dry_run)

            if args.update_categories:
                update_source_categories(conn, args.update_categories, dry_run=args.dry_run)

        print("\n" + "=" * 70)
        if args.dry_run:
            print("DRY RUN COMPLETE - No changes were made")
            print("Run without --dry-run to execute")
        else:
            print("✅ CLEANUP COMPLETE")
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
