#!/usr/bin/env python3
"""
Check DEMO Anchor Highlighting Compliance

Verifies whether DEMO anchor article links are correctly flagged according to
the enrichment rules defined in enrich_articles.py.
"""

import os
import sys

# Add project root to path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from src.management.db_utils import get_db_connection

# Tier definitions from enrich_articles.py
TIER1_CATEGORIES = [
    'Think Tank', 'AI Research', 'Research Institute', 'Non-Profit',
    'Academic', 'Advocacy', 'Publication', 'Business Council'
]
TIER2_CATEGORY = 'Government'
TIER3_CATEGORY = 'News & Media'


def check_tier1_compliance(conn):
    """Check if Tier 1 sources with abs(score) > 0.20 are flagged as highlights."""
    print("\n" + "=" * 70)
    print("TIER 1 COMPLIANCE CHECK (Think Tank, etc. - threshold = 0.20)")
    print("=" * 70)

    with conn.cursor() as cursor:
        # Get all DEMO links from Tier 1 categories
        cursor.execute("""
            SELECT
                sa.name as anchor_name,
                src.category,
                ABS(aal.similarity_score) as abs_score,
                aal.is_anchor_highlight,
                a.title,
                aal.similarity_score
            FROM article_anchor_links aal
            JOIN semantic_anchors sa ON aal.anchor_id = sa.id
            JOIN articles a ON aal.article_id = a.id
            JOIN sources src ON a.source_id = src.id
            WHERE sa.name LIKE 'DEMO:%'
              AND src.category IN ('Think Tank', 'AI Research', 'Research Institute', 'Non-Profit',
                                   'Academic', 'Advocacy', 'Publication', 'Business Council')
            ORDER BY ABS(aal.similarity_score) DESC
        """)

        results = cursor.fetchall()

        if not results:
            print("No DEMO links found in Tier 1 categories!")
            return

        total = len(results)
        should_be_highlighted = [r for r in results if r[2] > 0.20]
        should_not_be_highlighted = [r for r in results if r[2] <= 0.20]

        correctly_highlighted = [r for r in should_be_highlighted if r[3] is True]
        incorrectly_not_highlighted = [r for r in should_be_highlighted if r[3] is not True]

        correctly_not_highlighted = [r for r in should_not_be_highlighted if r[3] is not True]
        incorrectly_highlighted = [r for r in should_not_be_highlighted if r[3] is True]

        print(f"\nTotal DEMO links in Tier 1: {total:,}")
        print(f"Links with abs(score) > 0.20: {len(should_be_highlighted):,}")
        print(f"Links with abs(score) <= 0.20: {len(should_not_be_highlighted):,}")

        print(f"\nCORRECTLY flagged as highlights: {len(correctly_highlighted):,}")
        print(f"INCORRECTLY NOT flagged (should be): {len(incorrectly_not_highlighted):,}")
        print(f"CORRECTLY NOT flagged: {len(correctly_not_highlighted):,}")
        print(f"INCORRECTLY flagged (should not be): {len(incorrectly_highlighted):,}")

        if incorrectly_not_highlighted:
            print(f"\n!!! PROBLEM: {len(incorrectly_not_highlighted)} DEMO links should be highlighted but aren't:")
            print(f"{'Anchor':<50s} | {'Category':<20s} | {'Abs Score':>10s} | {'Highlighted':>11s}")
            print("-" * 95)
            for anchor, category, abs_score, is_hl, title, raw_score in incorrectly_not_highlighted[:10]:
                print(f"{anchor:<50s} | {category:<20s} | {abs_score:>10.4f} | {str(is_hl):>11s}")

        if incorrectly_highlighted:
            print(f"\n!!! PROBLEM: {len(incorrectly_highlighted)} DEMO links are highlighted but shouldn't be:")
            print(f"{'Anchor':<50s} | {'Category':<20s} | {'Abs Score':>10s} | {'Highlighted':>11s}")
            print("-" * 95)
            for anchor, category, abs_score, is_hl, title, raw_score in incorrectly_highlighted[:10]:
                print(f"{anchor:<50s} | {category:<20s} | {abs_score:>10.4f} | {str(is_hl):>11s}")

        # Show distribution
        print(f"\n--- Score Distribution for Tier 1 DEMO Links ---")
        cursor.execute("""
            SELECT
                src.category,
                COUNT(*) as total,
                COUNT(CASE WHEN ABS(aal.similarity_score) > 0.20 THEN 1 END) as above_threshold,
                COUNT(CASE WHEN aal.is_anchor_highlight = true THEN 1 END) as flagged,
                AVG(ABS(aal.similarity_score)) as avg_abs_score,
                MAX(ABS(aal.similarity_score)) as max_abs_score
            FROM article_anchor_links aal
            JOIN semantic_anchors sa ON aal.anchor_id = sa.id
            JOIN articles a ON aal.article_id = a.id
            JOIN sources src ON a.source_id = src.id
            WHERE sa.name LIKE 'DEMO:%'
              AND src.category IN ('Think Tank', 'AI Research', 'Research Institute', 'Non-Profit',
                                   'Academic', 'Advocacy', 'Publication', 'Business Council')
            GROUP BY src.category
            ORDER BY total DESC
        """)

        print(f"{'Category':<30s} | {'Total':>6s} | {'Above 0.20':>10s} | {'Flagged':>7s} | {'Avg Abs':>8s} | {'Max Abs':>8s}")
        print("-" * 85)
        for category, total, above, flagged, avg_abs, max_abs in cursor.fetchall():
            print(f"{category:<30s} | {total:>6,d} | {above:>10,d} | {flagged:>7,d} | {avg_abs:>8.4f} | {max_abs:>8.4f}")


def check_tier2_compliance(conn):
    """Check if Tier 2 (Government) sources follow dynamic threshold rules."""
    print("\n" + "=" * 70)
    print("TIER 2 COMPLIANCE CHECK (Government - threshold = anchor mean)")
    print("=" * 70)

    with conn.cursor() as cursor:
        # Calculate mean per anchor for Government sources
        cursor.execute("""
            SELECT
                sa.name as anchor_name,
                AVG(ABS(aal.similarity_score)) as mean_abs_score
            FROM article_anchor_links aal
            JOIN semantic_anchors sa ON aal.anchor_id = sa.id
            JOIN articles a ON aal.article_id = a.id
            JOIN sources src ON a.source_id = src.id
            WHERE sa.name LIKE 'DEMO:%'
              AND src.category = 'Government'
            GROUP BY sa.name
        """)

        thresholds = {row[0]: row[1] for row in cursor.fetchall()}

        if not thresholds:
            print("No DEMO links found in Government category!")
            return

        print("\nAnchor-specific thresholds:")
        for anchor, threshold in thresholds.items():
            print(f"  {anchor}: {threshold:.4f}")

        # Check compliance
        cursor.execute("""
            SELECT
                sa.name as anchor_name,
                ABS(aal.similarity_score) as abs_score,
                aal.is_anchor_highlight,
                a.title
            FROM article_anchor_links aal
            JOIN semantic_anchors sa ON aal.anchor_id = sa.id
            JOIN articles a ON aal.article_id = a.id
            JOIN sources src ON a.source_id = src.id
            WHERE sa.name LIKE 'DEMO:%'
              AND src.category = 'Government'
        """)

        results = cursor.fetchall()
        total = len(results)
        errors = 0

        for anchor_name, abs_score, is_hl, title in results:
            threshold = thresholds.get(anchor_name, float('inf'))
            should_be_highlighted = abs_score > threshold

            if should_be_highlighted and not is_hl:
                errors += 1
            elif not should_be_highlighted and is_hl:
                errors += 1

        print(f"\nTotal DEMO Government links: {total:,}")
        print(f"Compliance errors: {errors:,}")

        if errors == 0:
            print("All Government DEMO links follow the threshold rules correctly!")


def check_tier3_compliance(conn):
    """Check if Tier 3 (News & Media) sources follow dynamic threshold rules."""
    print("\n" + "=" * 70)
    print("TIER 3 COMPLIANCE CHECK (News & Media - threshold = mean + std)")
    print("=" * 70)

    with conn.cursor() as cursor:
        # Calculate mean + std per anchor for News & Media sources
        cursor.execute("""
            SELECT
                sa.name as anchor_name,
                AVG(ABS(aal.similarity_score)) as mean_abs_score,
                STDDEV(ABS(aal.similarity_score)) as std_abs_score
            FROM article_anchor_links aal
            JOIN semantic_anchors sa ON aal.anchor_id = sa.id
            JOIN articles a ON aal.article_id = a.id
            JOIN sources src ON a.source_id = src.id
            WHERE sa.name LIKE 'DEMO:%'
              AND src.category = 'News & Media'
            GROUP BY sa.name
        """)

        thresholds = {row[0]: (row[1] + (row[2] if row[2] else 0)) for row in cursor.fetchall()}

        if not thresholds:
            print("No DEMO links found in News & Media category!")
            return

        print("\nAnchor-specific thresholds (mean + std):")
        for anchor, threshold in thresholds.items():
            print(f"  {anchor}: {threshold:.4f}")

        # Check compliance
        cursor.execute("""
            SELECT
                sa.name as anchor_name,
                ABS(aal.similarity_score) as abs_score,
                aal.is_anchor_highlight,
                a.title
            FROM article_anchor_links aal
            JOIN semantic_anchors sa ON aal.anchor_id = sa.id
            JOIN articles a ON aal.article_id = a.id
            JOIN sources src ON a.source_id = src.id
            WHERE sa.name LIKE 'DEMO:%'
              AND src.category = 'News & Media'
        """)

        results = cursor.fetchall()
        total = len(results)
        errors = 0

        for anchor_name, abs_score, is_hl, title in results:
            threshold = thresholds.get(anchor_name, float('inf'))
            should_be_highlighted = abs_score > threshold

            if should_be_highlighted and not is_hl:
                errors += 1
            elif not should_be_highlighted and is_hl:
                errors += 1

        print(f"\nTotal DEMO News & Media links: {total:,}")
        print(f"Compliance errors: {errors:,}")

        if errors == 0:
            print("All News & Media DEMO links follow the threshold rules correctly!")


def check_enrichment_status(conn):
    """Check if DEMO articles have been enriched."""
    print("\n" + "=" * 70)
    print("ENRICHMENT STATUS FOR DEMO ARTICLES")
    print("=" * 70)

    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT
                COUNT(DISTINCT a.id) as total_demo_articles,
                COUNT(DISTINCT CASE WHEN a.enrichment_processed_at IS NOT NULL THEN a.id END) as enriched,
                COUNT(DISTINCT CASE WHEN a.enrichment_processed_at IS NULL THEN a.id END) as not_enriched
            FROM articles a
            JOIN article_anchor_links aal ON a.id = aal.article_id
            JOIN semantic_anchors sa ON aal.anchor_id = sa.id
            WHERE sa.name LIKE 'DEMO:%'
        """)

        total, enriched, not_enriched = cursor.fetchone()

        print(f"Total DEMO articles: {total:,}")
        print(f"Enriched: {enriched:,} ({100*enriched/total if total > 0 else 0:.1f}%)")
        print(f"Not enriched: {not_enriched:,} ({100*not_enriched/total if total > 0 else 0:.1f}%)")

        if not_enriched > 0:
            print(f"\n!!! WARNING: {not_enriched:,} DEMO articles have not been enriched yet!")
            print("Run the enrichment engine to flag highlights.")


def main():
    print("=" * 70)
    print("DEMO ANCHOR HIGHLIGHTING COMPLIANCE CHECK")
    print("=" * 70)

    conn = get_db_connection()
    print("Connected to PostgreSQL database")

    try:
        check_enrichment_status(conn)
        check_tier1_compliance(conn)
        check_tier2_compliance(conn)
        check_tier3_compliance(conn)

        print("\n" + "=" * 70)
        print("COMPLIANCE CHECK COMPLETE")
        print("=" * 70)

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if conn:
            conn.close()
            print("\nDatabase connection closed")


if __name__ == "__main__":
    main()
