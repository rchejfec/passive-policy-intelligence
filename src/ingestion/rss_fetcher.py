# rss_fetcher.py (Refactored for Orchestrator)

"""Fetches and parses RSS feeds, storing new articles in the database."""
import feedparser
import os
from datetime import datetime
from time import mktime
import requests
import psycopg2
import psycopg2.extensions
from typing import List, Dict, Any, Tuple, Optional

# CHANGED: This import is now only used when the script is run standalone for testing.
from src.management.db_utils import get_db_connection

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# --- Database Functions ---
# CHANGED: All functions now accept a 'conn' object.

def get_active_feeds(conn: psycopg2.extensions.connection) -> List[Dict[str, Any]]:
    """Retrieves all active feed URLs from the sources table.

    Args:
        conn: Active database connection.

    Returns:
        List of dictionaries containing source information.
    """
    with conn.cursor() as cursor:
        cursor.execute("SELECT id, name, feed_url, social_feed_url, ga_feed_url FROM sources WHERE is_active = TRUE")
        sources = [dict(zip([column[0] for column in cursor.description], row)) for row in cursor.fetchall()]
    print(f"Found {len(sources)} active sources to check.")
    return sources

def article_exists(conn: psycopg2.extensions.connection, link: str) -> bool:
    """Checks if an article with the given link already exists in the database.

    Args:
        conn: Active database connection.
        link: URL of the article to check.

    Returns:
        True if article exists, False otherwise.
    """
    with conn.cursor() as cursor:
        cursor.execute("SELECT id FROM articles WHERE link = %s", (link,))
        exists = cursor.fetchone() is not None
    return exists

def add_article_to_db(conn: psycopg2.extensions.connection, source_id: int, title: str, link: str, summary: str, published_date: str, retrieved_from_url: str) -> None:
    """Inserts a new article into the articles table, ignoring duplicates.

    Args:
        conn: Active database connection.
        source_id: ID of the source.
        title: Article title.
        link: Article URL.
        summary: Article summary.
        published_date: Date published.
        retrieved_from_url: URL where the article was found (feed URL).
    """
    with conn.cursor() as cursor:
        # CHANGED: Using ON CONFLICT for efficient duplicate handling in PostgreSQL.
        cursor.execute("""
            INSERT INTO articles (source_id, title, link, summary, published_date, retrieved_from_url)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (link) DO NOTHING
        """, (source_id, title, link, summary, published_date, retrieved_from_url))

# --- Feed Parsing Function ---
# CHANGED: This function now accepts a 'conn' object to pass down.

def fetch_and_process_feed(conn: psycopg2.extensions.connection, source_id: int, source_name: str, feed_url: str) -> Tuple[int, str]:
    """Fetches a single RSS feed and adds new articles to the database.

    Args:
        conn: Active database connection.
        source_id: ID of the source.
        source_name: Name of the source.
        feed_url: URL of the RSS feed.

    Returns:
        Tuple containing count of new articles found and status message.
    """
    if not feed_url:
        return 0, "Skipped (empty URL)"
        
    print(f"\nFetching feed for '{source_name}' from {feed_url}...")
    
    try:
        response = requests.get(feed_url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        feed = feedparser.parse(response.content)
    except requests.exceptions.RequestException as e:
        return 0, f"Failed to fetch: {e}"

    if not feed.entries:
        return 0, "Success (no entries)"

    new_articles_found = 0
    for entry in feed.entries:
        link = entry.get('link')
        title = entry.get('title', 'No Title')
        
        if not link:
            continue

        if not article_exists(conn, link):
            print(f"  [NEW] Found new article: {title}")
            new_articles_found += 1
            summary = entry.get('summary', '')
            published_struct = entry.get('published_parsed')
            published_date = datetime.fromtimestamp(mktime(published_struct)).strftime('%Y-%m-%d %H:%M:%S') if published_struct else datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            add_article_to_db(conn, source_id, title, link, summary, published_date, feed_url)
            
    return new_articles_found, "Success"

# --- Main Execution Logic ---
# CHANGED: The main logic is wrapped in a function that accepts a connection.

def main(conn: psycopg2.extensions.connection) -> Optional[int]:
    """Main execution logic for the RSS fetcher.

    Args:
        conn: Active database connection.

    Returns:
        Total number of new articles added, or None if failed (though implementation returns early on some failures).

    Raises:
        psycopg2.Error: If database error occurs.
    """
    print("--- Running RSS Fetcher ---")
    
    try:
        active_sources = get_active_feeds(conn)
        
        if not active_sources:
            print("No active sources found. Skipping.")
            return 0 # Return 0 instead of None for consistency
            
        total_new_articles = 0
        
        for source in active_sources:
            urls = [source['feed_url'], source['social_feed_url'], source['ga_feed_url']]
            for url in filter(None, urls): # filter(None, ...) neatly removes empty/None URLs
                new_articles, status = fetch_and_process_feed(conn, source['id'], source['name'], url)
                if "Success" in status:
                    total_new_articles += new_articles
        
        # The orchestrator will handle the final commit, but for clarity, we can commit here.
        conn.commit()
        print(f"\nRSS Fetcher finished. {total_new_articles} new articles added.")

        return total_new_articles

    except psycopg2.Error as e:
        print(f"A database error occurred in RSS Fetcher: {e}")
        # The orchestrator will handle rollback.
        raise

# This block allows the script to be run standalone for testing.
if __name__ == "__main__":
    connection = None
    print("--- Running rss_fetcher.py standalone for testing ---")
    try:
        connection = get_db_connection()
        main(connection)
    except Exception as e:
        print(f"An error occurred during standalone execution: {e}")
    finally:
        if connection:
            connection.close()
            print("Standalone execution finished. Connection closed.")
