"""Minimal RSS link archiver — no DB, no pipeline.

Reads feeds from user_content/ConsolidatedRSSFeeds.csv and appends
new links to data/rss_archive.csv once per run (deduped by URL).
"""

import csv
from datetime import datetime, timezone
from pathlib import Path
from time import mktime

import feedparser
import requests

FEEDS_CSV = Path(__file__).parent.parent / "user_content" / "ConsolidatedRSSFeeds.csv"
ARCHIVE_CSV = Path(__file__).parent.parent / "archive" / "rss_archive.csv"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/91.0.4472.124 Safari/537.36"
    )
}

FIELDS = ["date_fetched", "source_name", "category", "title", "link", "published_date", "feed_url"]


def load_existing_links() -> set:
    if not ARCHIVE_CSV.exists():
        return set()
    with open(ARCHIVE_CSV, newline="", encoding="utf-8") as f:
        return {row["link"] for row in csv.DictReader(f)}


def load_sources() -> list:
    with open(FEEDS_CSV, newline="", encoding="utf-8") as f:
        return [
            {
                "name": row["Source Name"],
                "category": row["Category"],
                "urls": [u for u in [row["Feed URL"], row["Socials Feed URL"], row["GA Feed URL"]] if u.strip()],
            }
            for row in csv.DictReader(f)
        ]


def fetch_entries(url: str) -> list:
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        return feedparser.parse(r.content).entries
    except Exception as e:
        print(f"  [SKIP] {url}: {e}")
        return []


def main():
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    seen = load_existing_links()
    new_rows = []

    for source in load_sources():
        for url in source["urls"]:
            for entry in fetch_entries(url):
                link = entry.get("link", "").strip()
                if not link or link in seen:
                    continue
                seen.add(link)
                ps = entry.get("published_parsed")
                new_rows.append({
                    "date_fetched": now,
                    "source_name": source["name"],
                    "category": source["category"],
                    "title": entry.get("title", "").strip(),
                    "link": link,
                    "published_date": datetime.fromtimestamp(mktime(ps)).strftime("%Y-%m-%d %H:%M:%S") if ps else "",
                    "feed_url": url,
                })

    if not new_rows:
        print("No new links found.")
        return

    ARCHIVE_CSV.parent.mkdir(exist_ok=True)
    write_header = not ARCHIVE_CSV.exists()
    with open(ARCHIVE_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if write_header:
            writer.writeheader()
        writer.writerows(new_rows)

    print(f"Archived {len(new_rows)} new links to {ARCHIVE_CSV}.")


if __name__ == "__main__":
    main()
