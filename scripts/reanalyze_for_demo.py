#!/usr/bin/env python3
"""
Re-analyze Articles for Demo

Re-runs semantic analysis on recent articles using DEMO: anchors only.
Clears existing article_anchor_links and regenerates matches.

Usage:
    python scripts/reanalyze_for_demo.py --months 3
    python scripts/reanalyze_for_demo.py --months 2 --dry-run
    python scripts/reanalyze_for_demo.py --since 2025-10-01
"""

import os
import sys
import argparse
from datetime import datetime, timedelta

# Add project root to path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from src.management.db_utils import get_db_connection
from src.analysis import analyze_articles


def get_demo_anchor_count(conn):
    """Get count of active DEMO: anchors."""
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT COUNT(*)
            FROM semantic_anchors
            WHERE name LIKE 'DEMO:%' AND is_active = true
        """)
        return cursor.fetchone()[0]


def get_articles_to_analyze(conn, months=None, since_date=None):
    """Get articles from the specified time period."""
    with conn.cursor() as cursor:
        if since_date:
            cursor.execute("""
                SELECT COUNT(*), MIN(published_date), MAX(published_date)
                FROM articles
                WHERE published_date >= %s
                  AND indexed_at IS NOT NULL
            """, (since_date,))
        else:
            cutoff_date = datetime.now() - timedelta(days=months * 30)
            cursor.execute("""
                SELECT COUNT(*), MIN(published_date), MAX(published_date)
                FROM articles
                WHERE published_date >= %s
                  AND indexed_at IS NOT NULL
            """, (cutoff_date,))

        count, min_date, max_date = cursor.fetchone()

    return {
        'count': count,
        'min_date': min_date,
        'max_date': max_date
    }


def clear_existing_demo_links(conn, dry_run=False):
    """Clear existing article_anchor_links for DEMO: anchors."""
    print(f"\n🧹 Clearing existing DEMO: anchor links...")

    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT COUNT(*)
            FROM article_anchor_links aal
            JOIN semantic_anchors sa ON aal.anchor_id = sa.id
            WHERE sa.name LIKE 'DEMO:%'
        """)
        existing_count = cursor.fetchone()[0]

    if existing_count == 0:
        print("   ℹ️  No existing DEMO: links found")
        return

    print(f"   Found {existing_count:,} existing DEMO: article links")

    if dry_run:
        print("   [DRY RUN] Would delete these links")
        return

    with conn.cursor() as cursor:
        cursor.execute("""
            DELETE FROM article_anchor_links
            WHERE anchor_id IN (
                SELECT id FROM semantic_anchors WHERE name LIKE 'DEMO:%'
            )
        """)
        conn.commit()

    print(f"   ✓ Deleted {existing_count:,} existing links")


def reset_analyzed_timestamps(conn, months=None, since_date=None, dry_run=False):
    """Clear analyzed_at timestamps so articles will be re-analyzed."""
    print(f"\n🔄 Resetting analyzed_at timestamps...")

    if since_date:
        where_clause = "published_date >= %s"
        params = (since_date,)
    else:
        cutoff_date = datetime.now() - timedelta(days=months * 30)
        where_clause = "published_date >= %s"
        params = (cutoff_date,)

    with conn.cursor() as cursor:
        cursor.execute(f"""
            SELECT COUNT(*)
            FROM articles
            WHERE {where_clause}
              AND analyzed_at IS NOT NULL
        """, params)
        count = cursor.fetchone()[0]

    if count == 0:
        print("   ℹ️  No articles need timestamp reset")
        return

    print(f"   Found {count:,} articles with analyzed_at timestamps")

    if dry_run:
        print("   [DRY RUN] Would reset analyzed_at to NULL for these articles")
        return

    with conn.cursor() as cursor:
        cursor.execute(f"""
            UPDATE articles
            SET analyzed_at = NULL
            WHERE {where_clause}
              AND analyzed_at IS NOT NULL
        """, params)
        conn.commit()

    print(f"   ✓ Reset {count:,} analyzed_at timestamps")


def run_analysis(conn, dry_run=False, max_retries=10):
    """Run the analysis module to generate new matches with auto-retry on connection loss."""
    print(f"\n🔍 Running semantic analysis...")

    if dry_run:
        print("   [DRY RUN] Would run analysis module")
        return

    # Auto-retry loop for connection drops
    for attempt in range(1, max_retries + 1):
        try:
            print(f"   Starting analyze_articles.main() (attempt {attempt}/{max_retries})...")
            analyze_articles.main(conn)
            print("   ✓ Analysis complete")
            return  # Success!
        except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
            if "server closed the connection" in str(e) or "connection already closed" in str(e):
                print(f"   ⚠️  Connection dropped (attempt {attempt}/{max_retries})")
                if attempt < max_retries:
                    import time
                    wait_time = 10
                    print(f"   ⏳ Waiting {wait_time}s before reconnecting...")
                    time.sleep(wait_time)

                    # Get fresh connection
                    try:
                        conn.close()
                    except:
                        pass
                    conn = get_db_connection()
                    print("   ✓ Reconnected to database")
                    continue
                else:
                    print(f"   ❌ Max retries reached. Giving up.")
                    raise
            else:
                # Different error, don't retry
                print(f"   ❌ Analysis failed: {e}")
                raise
        except Exception as e:
            print(f"   ❌ Analysis failed: {e}")
            raise


def get_analysis_results(conn):
    """Get summary of analysis results."""
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT
                sa.name,
                COUNT(*) as article_count,
                AVG(aal.similarity_score) as avg_score,
                MAX(aal.similarity_score) as max_score
            FROM article_anchor_links aal
            JOIN semantic_anchors sa ON aal.anchor_id = sa.id
            WHERE sa.name LIKE 'DEMO:%'
            GROUP BY sa.id, sa.name
            ORDER BY sa.name
        """)
        return cursor.fetchall()


def main():
    parser = argparse.ArgumentParser(description='Re-analyze articles for demo presentation')
    parser.add_argument('--months', type=int, default=3,
                       help='Number of months to analyze (default: 3)')
    parser.add_argument('--days', type=int,
                       help='Number of days to analyze (for testing)')
    parser.add_argument('--since', type=str,
                       help='Analyze articles since date (YYYY-MM-DD)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Preview actions without making changes')
    parser.add_argument('--resume', action='store_true',
                       help='Resume from interruption (skip clearing links and resetting timestamps)')
    args = parser.parse_args()

    print("=" * 70)
    print("RE-ANALYZE ARTICLES FOR DEMO")
    print("=" * 70)
    print(f"Mode: {'DRY RUN (preview only)' if args.dry_run else 'EXECUTE'}")
    print(f"Resume: {'Yes (preserving existing links)' if args.resume else 'No (fresh start)'}")

    # Determine time period
    if args.since:
        print(f"Period: Since {args.since}")
        since_date = datetime.strptime(args.since, '%Y-%m-%d').date()
        months = None
    elif args.days:
        cutoff_date = datetime.now() - timedelta(days=args.days)
        print(f"Period: Last {args.days} days (since {cutoff_date.date()})")
        since_date = cutoff_date.date()
        months = None
    else:
        print(f"Period: Last {args.months} months")
        since_date = None
        months = args.months
    print()

    # Connect to database
    conn = get_db_connection()
    print("✓ Connected to PostgreSQL database")

    try:
        # Verify demo anchors exist
        demo_count = get_demo_anchor_count(conn)
        if demo_count == 0:
            print("\n❌ ERROR: No active DEMO: anchors found")
            print("   Run setup_demo_anchors.py first")
            return

        print(f"✓ Found {demo_count} active DEMO: anchors")

        # Get article stats
        article_stats = get_articles_to_analyze(conn, months=months, since_date=since_date)
        print(f"\n📊 Article Analysis Scope:")
        print(f"   Articles to analyze: {article_stats['count']:,}")
        print(f"   Date range: {article_stats['min_date']} to {article_stats['max_date']}")

        if article_stats['count'] == 0:
            print("\n❌ ERROR: No articles found in specified period")
            return

        # Only clear and reset on fresh start (not on resume)
        if not args.resume:
            # Clear existing demo links
            clear_existing_demo_links(conn, dry_run=args.dry_run)

            # Reset analyzed_at timestamps so articles will be re-analyzed
            reset_analyzed_timestamps(conn, months=months, since_date=since_date, dry_run=args.dry_run)
        else:
            print("\n⏭️  Resuming from previous run (skipping clear and reset)")

        # Run analysis
        if not args.dry_run:
            run_analysis(conn, dry_run=args.dry_run)

            # Get results
            results = get_analysis_results(conn)

            print("\n" + "=" * 70)
            print("✅ ANALYSIS COMPLETE")
            print("=" * 70)
            print(f"\nResults by anchor:")
            print(f"{'Anchor Name':<50} {'Matches':>10} {'Avg Score':>12} {'Max Score':>12}")
            print("-" * 86)
            for name, count, avg_score, max_score in results:
                print(f"{name:<50} {count:>10,} {avg_score:>12.4f} {max_score:>12.4f}")

            total_matches = sum(row[1] for row in results)
            print("-" * 86)
            print(f"{'TOTAL':<50} {total_matches:>10,}")
            print("\n" + "=" * 70)
        else:
            print("\n" + "=" * 70)
            print("DRY RUN COMPLETE - No changes were made")
            print("Run without --dry-run to execute")
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
