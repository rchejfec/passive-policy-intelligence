"""
Export PostgreSQL data to Parquet files for Observable Framework portal.

This script exports data from the AI Daily Digest PostgreSQL database into
optimized parquet files for consumption by the Think Tank Intelligence Portal.

Files Generated:
- morning_paper.parquet: Articles from last 7 days (denormalized with anchors)
- archive.parquet: All historical articles (denormalized with anchors)
- sources.parquet: Source metadata
- anchors.parquet: Semantic anchor definitions

Usage:
    python scripts/export_to_parquet.py
    python scripts/export_to_parquet.py --days 14  # Custom time window
"""

import os
import sys
import argparse
import pandas as pd
from datetime import datetime, timedelta

# Path setup
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from src.management.db_utils import get_db_connection

# Configuration
OUTPUT_DIR = os.path.join(ROOT_DIR, 'portal', 'src', 'data')
DEFAULT_MORNING_PAPER_DAYS = 7


def export_morning_paper(conn, days=DEFAULT_MORNING_PAPER_DAYS):
    """
    Export recent articles with their anchor matches for the morning paper view.

    This creates a denormalized view where each article-anchor match is a row.
    Only includes analyzed articles from the last N days.

    Args:
        conn: PostgreSQL connection object
        days: Number of days to look back (default: 7)

    Returns:
        int: Number of article-anchor pairs exported
    """
    print(f"Exporting morning paper data (last {days} days)...")

    query = """
    SELECT
        a.id as article_id,
        a.title,
        a.link,
        a.created_at,
        s.id as source_id,
        s.name as source_name,
        s.category as source_category,
        sa.id as anchor_id,
        sa.name as anchor_name,
        aal.similarity_score,
        aal.is_anchor_highlight,
        aal.is_org_highlight
    FROM articles a
    JOIN sources s ON a.source_id = s.id
    JOIN article_anchor_links aal ON a.id = aal.article_id
    JOIN semantic_anchors sa ON aal.anchor_id = sa.id
    WHERE a.created_at >= NOW() - INTERVAL '%s days'
      AND a.analyzed_at IS NOT NULL
      AND sa.is_active = true
    ORDER BY a.created_at DESC, aal.similarity_score DESC
    """

    df = pd.read_sql_query(query, conn, params=(days,))

    output_path = os.path.join(OUTPUT_DIR, 'morning_paper.parquet')
    df.to_parquet(output_path, index=False, engine='pyarrow')

    unique_articles = df['article_id'].nunique() if not df.empty else 0
    print(f"✓ Exported {len(df)} article-anchor pairs ({unique_articles} unique articles)")
    print(f"  File: {output_path}")

    return len(df)


def export_archive(conn):
    """
    Export all historical articles with their anchor matches for archive view.

    Same denormalized structure as morning paper, but includes all time.

    Args:
        conn: PostgreSQL connection object

    Returns:
        int: Number of article-anchor pairs exported
    """
    print("Exporting archive data (all articles)...")

    query = """
    SELECT
        a.id as article_id,
        a.title,
        a.link,
        a.created_at,
        s.id as source_id,
        s.name as source_name,
        s.category as source_category,
        sa.id as anchor_id,
        sa.name as anchor_name,
        aal.similarity_score,
        aal.is_anchor_highlight,
        aal.is_org_highlight
    FROM articles a
    JOIN sources s ON a.source_id = s.id
    JOIN article_anchor_links aal ON a.id = aal.article_id
    JOIN semantic_anchors sa ON aal.anchor_id = sa.id
    WHERE a.analyzed_at IS NOT NULL
      AND sa.is_active = true
    ORDER BY a.created_at DESC
    """

    df = pd.read_sql_query(query, conn)

    output_path = os.path.join(OUTPUT_DIR, 'archive.parquet')
    df.to_parquet(output_path, index=False, engine='pyarrow')

    unique_articles = df['article_id'].nunique() if not df.empty else 0
    print(f"✓ Exported {len(df)} article-anchor pairs ({unique_articles} unique articles)")
    print(f"  File: {output_path}")

    return len(df)


def export_sources(conn):
    """
    Export source metadata for transparency and filtering.

    Args:
        conn: PostgreSQL connection object

    Returns:
        int: Number of sources exported
    """
    print("Exporting sources metadata...")

    query = """
    SELECT
        id as source_id,
        name as source_name,
        category as source_category,
        site_url as url,
        bias_lean,
        tags,
        is_active
    FROM sources
    WHERE is_active = true
    ORDER BY source_name
    """

    df = pd.read_sql_query(query, conn)

    output_path = os.path.join(OUTPUT_DIR, 'sources.parquet')
    df.to_parquet(output_path, index=False, engine='pyarrow')

    print(f"✓ Exported {len(df)} sources")
    print(f"  File: {output_path}")

    return len(df)


def export_anchors(conn):
    """
    Export semantic anchor definitions for UI and filtering.

    Args:
        conn: PostgreSQL connection object

    Returns:
        int: Number of anchors exported
    """
    print("Exporting semantic anchors...")

    query = """
    SELECT
        id as anchor_id,
        name as anchor_name,
        description as anchor_description,
        anchor_author,
        created_at
    FROM semantic_anchors
    WHERE is_active = true
    ORDER BY name
    """

    df = pd.read_sql_query(query, conn)

    output_path = os.path.join(OUTPUT_DIR, 'anchors.parquet')
    df.to_parquet(output_path, index=False, engine='pyarrow')

    print(f"✓ Exported {len(df)} anchors")
    print(f"  File: {output_path}")

    return len(df)


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description='Export PostgreSQL data to Parquet files for Think Tank Portal'
    )
    parser.add_argument(
        '--days',
        type=int,
        default=DEFAULT_MORNING_PAPER_DAYS,
        help=f'Days to include in morning paper (default: {DEFAULT_MORNING_PAPER_DAYS})'
    )
    args = parser.parse_args()

    print("=" * 60)
    print("Think Tank Intelligence Portal - Data Export")
    print("=" * 60)

    # Ensure output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    conn = None
    try:
        conn = get_db_connection()
        print("✓ Database connection established\n")

        # Export all data files
        export_morning_paper(conn, args.days)
        print()

        export_archive(conn)
        print()

        export_sources(conn)
        print()

        export_anchors(conn)
        print()

        print("=" * 60)
        print("✓ Export completed successfully")
        print(f"Output directory: {OUTPUT_DIR}")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Export failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    main()
