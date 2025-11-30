#!/usr/bin/env python3
"""
Fix DEMO Anchor Enrichment

Quick fix to reset enrichment status for articles with DEMO anchor links,
then re-run enrichment to properly flag highlights.
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
from src.analysis.enrich_articles import main as enrich_main


def reset_demo_enrichment(conn, dry_run=False):
    """Reset enrichment_processed_at for articles that have DEMO anchor links."""
    print("\n" + "=" * 70)
    print("RESETTING ENRICHMENT STATUS FOR DEMO ARTICLES")
    print("=" * 70)

    with conn.cursor() as cursor:
        # First, check how many articles we're dealing with
        cursor.execute("""
            SELECT COUNT(DISTINCT a.id)
            FROM articles a
            JOIN article_anchor_links aal ON a.id = aal.article_id
            JOIN semantic_anchors sa ON aal.anchor_id = sa.id
            WHERE sa.name LIKE 'DEMO:%'
              AND a.enrichment_processed_at IS NOT NULL
        """)

        count = cursor.fetchone()[0]
        print(f"\nFound {count:,} articles with DEMO links that have been enriched")

        if count == 0:
            print("No articles to reset!")
            return 0

        if dry_run:
            print("\n[DRY RUN] Would reset enrichment_processed_at for these articles")
            return count

        # Reset enrichment_processed_at
        cursor.execute("""
            UPDATE articles
            SET enrichment_processed_at = NULL
            WHERE id IN (
                SELECT DISTINCT a.id
                FROM articles a
                JOIN article_anchor_links aal ON a.id = aal.article_id
                JOIN semantic_anchors sa ON aal.anchor_id = sa.id
                WHERE sa.name LIKE 'DEMO:%'
            )
        """)

        conn.commit()
        print(f"\nReset enrichment status for {count:,} articles")

        return count


def main():
    parser = argparse.ArgumentParser(description='Fix DEMO anchor enrichment')
    parser.add_argument('--dry-run', action='store_true',
                       help='Preview actions without making changes')
    args = parser.parse_args()

    print("=" * 70)
    print("FIX DEMO ANCHOR ENRICHMENT")
    print("=" * 70)
    print(f"Mode: {'DRY RUN (preview only)' if args.dry_run else 'EXECUTE'}")
    print()

    conn = get_db_connection()
    print("Connected to PostgreSQL database")

    try:
        # Step 1: Reset enrichment status
        count = reset_demo_enrichment(conn, dry_run=args.dry_run)

        if args.dry_run:
            print("\n" + "=" * 70)
            print("DRY RUN COMPLETE - No changes were made")
            print(f"Would reset {count:,} articles and then re-run enrichment")
            print("Run without --dry-run to execute")
            print("=" * 70)
            return

        # Step 2: Re-run enrichment
        if count > 0:
            print("\n" + "=" * 70)
            print("RE-RUNNING ENRICHMENT ENGINE")
            print("=" * 70)

            highlights_found = enrich_main(conn)
            conn.commit()

            print(f"\nEnrichment complete! Found {highlights_found:,} org highlights")

        # Step 3: Verify results
        print("\n" + "=" * 70)
        print("VERIFICATION")
        print("=" * 70)

        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT
                    COUNT(*) as total,
                    COUNT(CASE WHEN is_anchor_highlight IS NULL THEN 1 END) as null_count,
                    COUNT(CASE WHEN is_anchor_highlight = true THEN 1 END) as true_count,
                    COUNT(CASE WHEN is_anchor_highlight = false THEN 1 END) as false_count
                FROM article_anchor_links aal
                JOIN semantic_anchors sa ON aal.anchor_id = sa.id
                WHERE sa.name LIKE 'DEMO:%'
            """)

            total, null_count, true_count, false_count = cursor.fetchone()

            print(f"Total DEMO links: {total:,}")
            print(f"NULL (not processed): {null_count:,}")
            print(f"TRUE (highlighted): {true_count:,}")
            print(f"FALSE (not highlighted): {false_count:,}")

            if null_count == 0:
                print("\nSUCCESS: All DEMO links have been processed!")
            else:
                print(f"\nWARNING: {null_count:,} DEMO links still not processed")

        print("\n" + "=" * 70)
        print("FIX COMPLETE")
        print("=" * 70)

    except Exception as e:
        print(f"\nERROR: {e}")
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
