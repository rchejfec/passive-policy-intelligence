#!/usr/bin/env python3
"""
Explore Highlighting Patterns Script

Analyzes the current highlighting patterns in the database to understand:
1. How many highlights exist (anchor vs org)
2. Distribution by anchor, source category, and score ranges
3. Current enrichment coverage
4. Patterns in what gets highlighted

This helps inform any adjustments to the highlighting logic.
"""

import os
import sys
from datetime import datetime, timedelta

# Add project root to path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from src.management.db_utils import get_db_connection


def print_section(title):
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def explore_enrichment_coverage(conn):
    """Check how many articles have been enriched."""
    print_section("ENRICHMENT COVERAGE")

    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT
                COUNT(*) as total_articles,
                COUNT(CASE WHEN analyzed_at IS NOT NULL THEN 1 END) as analyzed,
                COUNT(CASE WHEN enrichment_processed_at IS NOT NULL THEN 1 END) as enriched,
                COUNT(CASE WHEN is_org_highlight = true THEN 1 END) as org_highlights
            FROM articles
        """)

        total, analyzed, enriched, org_highlights = cursor.fetchone()

        print(f"Total articles:           {total:>10,}")
        print(f"Analyzed:                 {analyzed:>10,} ({100*analyzed/total if total > 0 else 0:.1f}%)")
        print(f"Enriched:                 {enriched:>10,} ({100*enriched/total if total > 0 else 0:.1f}%)")
        print(f"Org highlights:           {org_highlights:>10,} ({100*org_highlights/total if total > 0 else 0:.1f}%)")


def explore_anchor_highlights_summary(conn):
    """Get summary statistics on anchor highlights."""
    print_section("ANCHOR HIGHLIGHTS SUMMARY")

    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT
                COUNT(*) as total_links,
                COUNT(CASE WHEN is_anchor_highlight = true THEN 1 END) as highlighted_links,
                AVG(CASE WHEN is_anchor_highlight = true THEN similarity_score END) as avg_highlighted_score,
                MIN(CASE WHEN is_anchor_highlight = true THEN similarity_score END) as min_highlighted_score,
                MAX(CASE WHEN is_anchor_highlight = true THEN similarity_score END) as max_highlighted_score
            FROM article_anchor_links
        """)

        total, highlighted, avg_score, min_score, max_score = cursor.fetchone()

        print(f"Total article-anchor links:  {total:>10,}")
        print(f"Highlighted links:           {highlighted:>10,} ({100*highlighted/total if total > 0 else 0:.1f}%)")
        if highlighted > 0:
            print(f"Avg score (highlighted):     {avg_score:>10.4f}")
            print(f"Min score (highlighted):     {min_score:>10.4f}")
            print(f"Max score (highlighted):     {max_score:>10.4f}")


def explore_highlights_by_anchor(conn):
    """Break down highlights by semantic anchor."""
    print_section("HIGHLIGHTS BY SEMANTIC ANCHOR")

    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT
                sa.name,
                COUNT(*) as total_links,
                COUNT(CASE WHEN aal.is_anchor_highlight = true THEN 1 END) as highlighted,
                AVG(aal.similarity_score) as avg_score,
                AVG(CASE WHEN aal.is_anchor_highlight = true THEN aal.similarity_score END) as avg_highlighted_score
            FROM article_anchor_links aal
            JOIN semantic_anchors sa ON aal.anchor_id = sa.id
            WHERE sa.is_active = true
            GROUP BY sa.id, sa.name
            ORDER BY highlighted DESC
            LIMIT 20
        """)

        results = cursor.fetchall()

        if results:
            print(f"{'Anchor Name':<50s} | {'Total':>6s} | {'Highlights':>10s} | {'% Highlight':>11s} | {'Avg Score':>9s} | {'Avg HL Score':>12s}")
            print("-" * 110)

            for name, total, highlighted, avg_score, avg_hl_score in results:
                pct = 100 * highlighted / total if total > 0 else 0
                avg_hl_str = f"{avg_hl_score:.4f}" if avg_hl_score else "N/A"
                print(f"{name:<50s} | {total:>6,d} | {highlighted:>10,d} | {pct:>10.1f}% | {avg_score:>9.4f} | {avg_hl_str:>12s}")
        else:
            print("No anchor highlight data found.")


def explore_highlights_by_category(conn):
    """Break down highlights by source category."""
    print_section("HIGHLIGHTS BY SOURCE CATEGORY")

    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT
                src.category,
                COUNT(*) as total_links,
                COUNT(CASE WHEN aal.is_anchor_highlight = true THEN 1 END) as highlighted,
                AVG(aal.similarity_score) as avg_score,
                AVG(CASE WHEN aal.is_anchor_highlight = true THEN aal.similarity_score END) as avg_highlighted_score
            FROM article_anchor_links aal
            JOIN articles a ON aal.article_id = a.id
            JOIN sources src ON a.source_id = src.id
            GROUP BY src.category
            ORDER BY highlighted DESC
        """)

        results = cursor.fetchall()

        if results:
            print(f"{'Category':<30s} | {'Total':>8s} | {'Highlights':>10s} | {'% Highlight':>11s} | {'Avg Score':>9s} | {'Avg HL Score':>12s}")
            print("-" * 95)

            for category, total, highlighted, avg_score, avg_hl_score in results:
                pct = 100 * highlighted / total if total > 0 else 0
                avg_hl_str = f"{avg_hl_score:.4f}" if avg_hl_score else "N/A"
                print(f"{category:<30s} | {total:>8,d} | {highlighted:>10,d} | {pct:>10.1f}% | {avg_score:>9.4f} | {avg_hl_str:>12s}")
        else:
            print("No category highlight data found.")


def explore_highlight_thresholds(conn):
    """Analyze what scores are getting highlighted by category."""
    print_section("HIGHLIGHT SCORE THRESHOLDS BY CATEGORY")

    with conn.cursor() as cursor:
        # Look at Tier 1 (Think Tank, etc.) - should be > 0.20
        cursor.execute("""
            SELECT
                src.category,
                MIN(CASE WHEN aal.is_anchor_highlight = true THEN ABS(aal.similarity_score) END) as min_highlighted,
                MAX(CASE WHEN aal.is_anchor_highlight = false THEN ABS(aal.similarity_score) END) as max_not_highlighted
            FROM article_anchor_links aal
            JOIN articles a ON aal.article_id = a.id
            JOIN sources src ON a.source_id = src.id
            WHERE src.category IN ('Think Tank', 'AI Research', 'Research Institute', 'Non-Profit',
                                   'Academic', 'Advocacy', 'Publication', 'Business Council')
            GROUP BY src.category
        """)

        print("\nTIER 1 CATEGORIES (threshold = 0.20):")
        print(f"{'Category':<30s} | {'Min Highlighted':>15s} | {'Max Not Highlighted':>20s}")
        print("-" * 70)

        for category, min_hl, max_not_hl in cursor.fetchall():
            min_str = f"{min_hl:.4f}" if min_hl else "N/A"
            max_str = f"{max_not_hl:.4f}" if max_not_hl else "N/A"
            print(f"{category:<30s} | {min_str:>15s} | {max_str:>20s}")

        # Look at Government (Tier 2)
        cursor.execute("""
            SELECT
                MIN(CASE WHEN aal.is_anchor_highlight = true THEN ABS(aal.similarity_score) END) as min_highlighted,
                MAX(CASE WHEN aal.is_anchor_highlight = false THEN ABS(aal.similarity_score) END) as max_not_highlighted
            FROM article_anchor_links aal
            JOIN articles a ON aal.article_id = a.id
            JOIN sources src ON a.source_id = src.id
            WHERE src.category = 'Government'
        """)

        print("\nTIER 2 (Government - threshold = anchor mean):")
        row = cursor.fetchone()
        if row:
            min_hl, max_not_hl = row
            print(f"Min highlighted:      {min_hl:.4f}" if min_hl else "N/A")
            print(f"Max not highlighted:  {max_not_hl:.4f}" if max_not_hl else "N/A")

        # Look at News & Media (Tier 3)
        cursor.execute("""
            SELECT
                MIN(CASE WHEN aal.is_anchor_highlight = true THEN ABS(aal.similarity_score) END) as min_highlighted,
                MAX(CASE WHEN aal.is_anchor_highlight = false THEN ABS(aal.similarity_score) END) as max_not_highlighted
            FROM article_anchor_links aal
            JOIN articles a ON aal.article_id = a.id
            JOIN sources src ON a.source_id = src.id
            WHERE src.category = 'News & Media'
        """)

        print("\nTIER 3 (News Media - threshold = anchor mean + std):")
        row = cursor.fetchone()
        if row:
            min_hl, max_not_hl = row
            print(f"Min highlighted:      {min_hl:.4f}" if min_hl else "N/A")
            print(f"Max not highlighted:  {max_not_hl:.4f}" if max_not_hl else "N/A")


def explore_demo_anchors(conn):
    """Special analysis for DEMO anchors."""
    print_section("DEMO ANCHORS ANALYSIS")

    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT
                sa.name,
                COUNT(*) as total_links,
                COUNT(CASE WHEN aal.is_anchor_highlight = true THEN 1 END) as highlighted,
                MIN(aal.similarity_score) as min_score,
                MAX(aal.similarity_score) as max_score,
                AVG(aal.similarity_score) as avg_score,
                AVG(CASE WHEN aal.is_anchor_highlight = true THEN aal.similarity_score END) as avg_highlighted_score
            FROM article_anchor_links aal
            JOIN semantic_anchors sa ON aal.anchor_id = sa.id
            WHERE sa.name LIKE 'DEMO:%'
            GROUP BY sa.id, sa.name
            ORDER BY sa.name
        """)

        results = cursor.fetchall()

        if results:
            print(f"{'Anchor Name':<50s} | {'Total':>6s} | {'Highlights':>10s} | {'Min':>7s} | {'Max':>7s} | {'Avg':>7s} | {'Avg HL':>7s}")
            print("-" * 110)

            for name, total, highlighted, min_s, max_s, avg_s, avg_hl in results:
                avg_hl_str = f"{avg_hl:.4f}" if avg_hl else "N/A"
                print(f"{name:<50s} | {total:>6,d} | {highlighted:>10,d} | {min_s:>7.3f} | {max_s:>7.3f} | {avg_s:>7.3f} | {avg_hl_str:>7s}")
        else:
            print("No DEMO anchors found.")

        # Check if any DEMO articles have been enriched
        cursor.execute("""
            SELECT COUNT(DISTINCT aal.article_id)
            FROM article_anchor_links aal
            JOIN semantic_anchors sa ON aal.anchor_id = sa.id
            JOIN articles a ON aal.article_id = a.id
            WHERE sa.name LIKE 'DEMO:%'
              AND a.enrichment_processed_at IS NOT NULL
        """)

        enriched_count = cursor.fetchone()[0]
        print(f"\nDEMO articles enriched: {enriched_count:,}")


def explore_sample_highlights(conn):
    """Show sample highlighted articles."""
    print_section("SAMPLE HIGHLIGHTED ARTICLES")

    with conn.cursor() as cursor:
        # Sample anchor highlights
        print("\n--- Sample Anchor Highlights ---")
        cursor.execute("""
            SELECT
                sa.name as anchor,
                a.title,
                src.category,
                aal.similarity_score
            FROM article_anchor_links aal
            JOIN semantic_anchors sa ON aal.anchor_id = sa.id
            JOIN articles a ON aal.article_id = a.id
            JOIN sources src ON a.source_id = src.id
            WHERE aal.is_anchor_highlight = true
            ORDER BY RANDOM()
            LIMIT 5
        """)

        for anchor, title, category, score in cursor.fetchall():
            print(f"\nAnchor: {anchor}")
            print(f"Title: {title[:70]}...")
            print(f"Category: {category} | Score: {score:.4f}")

        # Sample org highlights
        print("\n--- Sample Org Highlights ---")
        cursor.execute("""
            SELECT
                a.title,
                src.category,
                MAX(aal.similarity_score) as max_score
            FROM articles a
            JOIN sources src ON a.source_id = src.id
            JOIN article_anchor_links aal ON a.id = aal.article_id
            WHERE a.is_org_highlight = true
            GROUP BY a.id, a.title, src.category
            ORDER BY RANDOM()
            LIMIT 5
        """)

        for title, category, max_score in cursor.fetchall():
            print(f"\nTitle: {title[:70]}...")
            print(f"Category: {category} | Max Score: {max_score:.4f}")


def main():
    print("=" * 70)
    print("HIGHLIGHTING PATTERN EXPLORATION")
    print("=" * 70)
    print(f"Run at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    conn = get_db_connection()
    print("Connected to PostgreSQL database")

    try:
        explore_enrichment_coverage(conn)
        explore_anchor_highlights_summary(conn)
        explore_highlights_by_anchor(conn)
        explore_highlights_by_category(conn)
        explore_highlight_thresholds(conn)
        explore_demo_anchors(conn)
        explore_sample_highlights(conn)

        print("\n" + "=" * 70)
        print("EXPLORATION COMPLETE")
        print("=" * 70)

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if conn:
            conn.close()
            print("\nDatabase connection closed")


if __name__ == "__main__":
    main()
