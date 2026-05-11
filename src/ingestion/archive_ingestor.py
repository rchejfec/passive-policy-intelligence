# src/ingestion/archive_ingestor.py
"""Ingests links from archive/rss_archive.csv into the articles table.

Runs after the live RSS fetch. Sets created_at to the archive's date_fetched
so the delivery engine's lookback filter naturally excludes old content.
Duplicate links are silently skipped via ON CONFLICT.
"""

import csv
import os
import psycopg2
import psycopg2.extensions
from pathlib import Path
from typing import Optional

from src.management.db_utils import get_db_connection

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
ARCHIVE_CSV = Path(ROOT_DIR) / "archive" / "rss_archive.csv"


def main(conn: psycopg2.extensions.connection) -> Optional[int]:
    """Ingests unprocessed archive links into the articles table.

    Args:
        conn: Active database connection.

    Returns:
        Number of new articles inserted, or None on failure.
    """
    print("--- Running Archive Ingestor ---")

    if not ARCHIVE_CSV.exists():
        print("No archive file found, skipping.")
        return 0

    with conn.cursor() as cur:
        cur.execute("SELECT name, id FROM sources")
        source_map = {name: sid for name, sid in cur.fetchall()}

    with open(ARCHIVE_CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    inserted = 0
    skipped_no_source = set()

    with conn.cursor() as cur:
        for row in rows:
            source_id = source_map.get(row["source_name"])
            if source_id is None:
                skipped_no_source.add(row["source_name"])
                continue

            cur.execute("""
                INSERT INTO articles
                    (source_id, title, link, published_date, retrieved_from_url, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (link) DO NOTHING
            """, (
                source_id,
                row["title"],
                row["link"],
                row["published_date"] or None,
                row["feed_url"],
                row["date_fetched"],
            ))

            if cur.rowcount == 1:
                inserted += 1

    if skipped_no_source:
        print(f"  Skipped {len(skipped_no_source)} unrecognized sources: {', '.join(sorted(skipped_no_source))}")

    print(f"Archive Ingestor finished. {inserted} new articles added from archive.")
    return inserted


if __name__ == "__main__":
    connection = None
    try:
        connection = get_db_connection()
        main(connection)
        connection.commit()
    except Exception as e:
        print(f"An error occurred during standalone execution: {e}")
        if connection:
            connection.rollback()
    finally:
        if connection:
            connection.close()