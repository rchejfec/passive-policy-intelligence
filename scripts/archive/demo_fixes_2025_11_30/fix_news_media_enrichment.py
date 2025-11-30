#!/usr/bin/env python3
"""
Fix News & Media Enrichment

Re-enriches News & Media articles now that the code has been updated
to use the correct category name.
"""

import os
import sys

# Add project root to path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from src.management.db_utils import get_db_connection
from src.analysis.enrich_articles import main as enrich_main


def main():
    print("=" * 70)
    print("FIX NEWS & MEDIA ENRICHMENT")
    print("=" * 70)

    conn = get_db_connection()
    print("Connected to PostgreSQL database")

    try:
        # Check how many News & Media articles exist
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(DISTINCT a.id)
                FROM articles a
                JOIN sources src ON a.source_id = src.id
                WHERE src.category = 'News & Media'
                  AND a.enrichment_processed_at IS NOT NULL
            """)

            count = cursor.fetchone()[0]
            print(f"\nFound {count:,} News & Media articles that have been enriched")

            if count == 0:
                print("No News & Media articles to re-enrich!")
                return

        # Reset enrichment for News & Media articles
        print("\nResetting enrichment status for News & Media articles...")
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE articles
                SET enrichment_processed_at = NULL
                WHERE id IN (
                    SELECT a.id
                    FROM articles a
                    JOIN sources src ON a.source_id = src.id
                    WHERE src.category = 'News & Media'
                )
            """)
            conn.commit()

        print(f"Reset enrichment status for {count:,} articles")

        # Re-run enrichment
        print("\n" + "=" * 70)
        print("RE-RUNNING ENRICHMENT ENGINE")
        print("=" * 70)

        highlights_found = enrich_main(conn)
        conn.commit()

        print(f"\nEnrichment complete! Found {highlights_found:,} org highlights")

        # Verify results
        print("\n" + "=" * 70)
        print("VERIFICATION")
        print("=" * 70)

        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT
                    COUNT(*) as total,
                    COUNT(CASE WHEN aal.is_anchor_highlight IS NULL THEN 1 END) as null_count,
                    COUNT(CASE WHEN aal.is_anchor_highlight = true THEN 1 END) as true_count
                FROM article_anchor_links aal
                JOIN articles a ON aal.article_id = a.id
                JOIN sources src ON a.source_id = src.id
                WHERE src.category = 'News & Media'
            """)

            total, null_count, true_count = cursor.fetchone()

            print(f"Total News & Media links: {total:,}")
            print(f"NULL (not processed): {null_count:,}")
            print(f"TRUE (highlighted): {true_count:,}")

            if null_count == 0:
                print("\nSUCCESS: All News & Media links have been processed!")
            else:
                print(f"\nWARNING: {null_count:,} News & Media links still not processed")

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
