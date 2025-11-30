#!/usr/bin/env python3
"""Check status of DEMO semantic anchors and their analysis."""

import os
import sys
from datetime import datetime, timedelta

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from src.management.db_utils import get_db_connection


def main():
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Check DEMO anchors exist
        print('=' * 70)
        print('DEMO ANCHORS')
        print('=' * 70)
        cursor.execute('''
            SELECT id, name, is_active, created_at
            FROM semantic_anchors
            WHERE name LIKE 'DEMO:%'
            ORDER BY name
        ''')
        anchors = cursor.fetchall()
        if anchors:
            for anchor_id, name, is_active, created_at in anchors:
                print(f'{anchor_id:3d} | {name:50s} | Active: {is_active} | {created_at}')
        else:
            print('NO DEMO ANCHORS FOUND!')
            return

        # Check article_anchor_links for DEMO anchors
        print('\n' + '=' * 70)
        print('ARTICLE ANCHOR LINKS FOR DEMO ANCHORS')
        print('=' * 70)
        cursor.execute('''
            SELECT sa.name, COUNT(*) as link_count,
                   AVG(aal.similarity_score) as avg_score,
                   MIN(aal.similarity_score) as min_score,
                   MAX(aal.similarity_score) as max_score
            FROM article_anchor_links aal
            JOIN semantic_anchors sa ON aal.anchor_id = sa.id
            WHERE sa.name LIKE 'DEMO:%'
            GROUP BY sa.id, sa.name
            ORDER BY sa.name
        ''')
        results = cursor.fetchall()
        if results:
            print(f'{"Anchor Name":<50s} | {"Links":>6s} | {"Avg":>6s} | {"Min":>6s} | {"Max":>6s}')
            print('-' * 70)
            for name, count, avg_score, min_score, max_score in results:
                print(f'{name:<50s} | {count:6,d} | {avg_score:6.3f} | {min_score:6.3f} | {max_score:6.3f}')
        else:
            print('NO LINKS FOUND!')

        # Check total link count (skip enrichment check as column may not exist)
        print('\n' + '=' * 70)
        print('TOTAL LINK COUNT')
        print('=' * 70)
        cursor.execute('''
            SELECT COUNT(*)
            FROM article_anchor_links aal
            JOIN semantic_anchors sa ON aal.anchor_id = sa.id
            WHERE sa.name LIKE 'DEMO:%'
        ''')
        total = cursor.fetchone()[0]
        print(f'Total DEMO links: {total:,}')

        # Check analyzed_at status for recent articles
        print('\n' + '=' * 70)
        print('RECENT ARTICLES (last 3 months)')
        print('=' * 70)
        cutoff = datetime.now() - timedelta(days=90)
        cursor.execute('''
            SELECT
                COUNT(*) as total,
                COUNT(CASE WHEN analyzed_at IS NOT NULL THEN 1 END) as analyzed,
                COUNT(CASE WHEN analyzed_at IS NULL THEN 1 END) as not_analyzed,
                MIN(published_date) as min_date,
                MAX(published_date) as max_date
            FROM articles
            WHERE published_date >= %s
              AND indexed_at IS NOT NULL
        ''', (cutoff,))

        total, analyzed, not_analyzed, min_date, max_date = cursor.fetchone()
        print(f'Total articles: {total:,}')
        print(f'Analyzed: {analyzed:,}')
        print(f'Not analyzed: {not_analyzed:,}')
        print(f'Date range: {min_date} to {max_date}')

        # Sample some links to see details
        print('\n' + '=' * 70)
        print('SAMPLE LINKS (first 5)')
        print('=' * 70)
        cursor.execute('''
            SELECT
                sa.name,
                a.title,
                aal.similarity_score,
                aal.enriched_at,
                aal.created_at
            FROM article_anchor_links aal
            JOIN semantic_anchors sa ON aal.anchor_id = sa.id
            JOIN articles a ON aal.article_id = a.id
            WHERE sa.name LIKE 'DEMO:%'
            ORDER BY aal.created_at DESC
            LIMIT 5
        ''')
        for name, title, score, enriched_at, created_at in cursor.fetchall():
            print(f'\nAnchor: {name}')
            print(f'Article: {title[:60]}...')
            print(f'Score: {score:.4f}')
            print(f'Created: {created_at}')
            print(f'Enriched: {enriched_at if enriched_at else "NOT ENRICHED"}')

    finally:
        conn.close()


if __name__ == "__main__":
    main()
