# -*- coding: utf-8 -*-
"""Builds a knowledge base from web articles and local drafts.

This script orchestrates the entire data ingestion process for the Personal
AI-Powered Daily Digest. It performs two main functions:

1.  **Gathers Raw Articles**: It reads from a manifest of RSS feeds and
    other sources, fetches the content from each URL, and compiles a raw
    list of articles. (This step can be skipped if the raw data already exists).
2.  **Enriches and Cleans Data**: It processes the raw article data, extracting
    a clean "product name" from the source URL and ensuring all data is
    consistently formatted.

The final output is a single, clean CSV file, `knowledge_base.csv`, which
serves as the definitive manifest for the indexing process.
"""

import csv
import os
from urllib.parse import urlparse
import feedparser
import requests
from bs4 import BeautifulSoup
import time
from typing import List, Dict, Any

# --- CONFIGURATION ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
USER_CONTENT_DIR = os.path.join(SCRIPT_DIR, '../..', 'user_content')
SOURCES_CSV = os.path.join(USER_CONTENT_DIR, 'ConsolidatedRSSFeeds.csv')
OUTPUT_CSV = os.path.join(USER_CONTENT_DIR, 'knowledge_base.csv')

# --- MAIN FUNCTIONS ---

def extract_product_name_from_url(url: str) -> str:
    """Extracts a human-readable 'product name' from a URL.

    This function takes a URL, extracts the last significant segment of its
    path, replaces hyphens with spaces, and capitalizes the first letter
    of each word to create a more presentable name.

    Args:
        url (str): The input URL string.

    Returns:
        str: A cleaned, capitalized string representing the product name,
             or an empty string if no meaningful segment can be extracted.
    """
    try:
        # Handle local file paths gracefully
        if not url.startswith(('http://', 'https://')):
            # For local paths, just use the filename without extension
            base = os.path.basename(url)
            return os.path.splitext(base)[0].replace('-', ' ').title()

        parsed_url = urlparse(url)
        path = parsed_url.path

        if path.endswith('/'):
            path = path.rstrip('/')
        
        last_segment = os.path.basename(path)

        if last_segment:
            name_with_spaces = last_segment.replace('-', ' ')
            return name_with_spaces.title()
        else:
            domain_name = parsed_url.netloc
            if domain_name.startswith('www.'):
                domain_name = domain_name[4:]
            return domain_name.split('.')[0].replace('-', ' ').title()

    except Exception as e:
        print(f"Error extracting product name from URL '{url}': {e}")
        return ""


def gather_raw_articles_from_sources(sources_csv_path: str) -> List[Dict[str, Any]]:
    """Scrapes articles from sources listed in a CSV file.

    Reads a CSV file containing RSS feeds and direct web links, fetches
    the content from each, and compiles a list of articles with their
    metadata.

    Args:
        sources_csv_path (str): The full path to the sources CSV file.

    Returns:
        list[dict]: A list of dictionaries, where each dictionary represents
                    an article with its source and other metadata.
    """
    print(f"Gathering raw articles from sources defined in: {sources_csv_path}")
    articles = []
    processed_urls = set()

    with open(sources_csv_path, mode='r', encoding='utf-8') as infile:
        reader = csv.DictReader(infile)
        for row in reader:
            source_type = row.get('type', 'web') # Default to 'web'
            url = row.get('url')
            program_tag = row.get('program_tag')
            program_name = row.get('program_name')
            status = row.get('status', 'active')
            initiative_type = row.get('initiative_type')
            
            if not url:
                continue

            if source_type == 'rss':
                feed = feedparser.parse(url)
                for entry in feed.entries:
                    entry_url = entry.link
                    if entry_url not in processed_urls:
                        articles.append({
                            'source_location': entry_url,
                            'source_type': 'web',
                            'program_tag': program_tag,
                            'program_name': program_name,
                            'status': status,
                            'initiative_type': initiative_type,
                        })
                        processed_urls.add(entry_url)
            else: # For 'web', 'oped', 'pdf', etc.
                if url not in processed_urls:
                    articles.append({
                        'source_location': url,
                        'source_type': source_type,
                        'program_tag': program_tag,
                        'program_name': program_name,
                        'status': status,
                        'initiative_type': initiative_type,
                    })
                    processed_urls.add(url)
            
            # A polite delay to avoid overwhelming the servers
            time.sleep(1)

    print(f"Found {len(articles)} raw articles.")
    return articles


def enrich_and_save_knowledge_base(articles: List[Dict[str, Any]], output_csv_path: str) -> None:
    """Enriches article data with product names and saves it to a CSV.

    Takes a list of raw article data, adds a 'product_name' column based
    on the source URL, and writes the final, clean data to a CSV file.

    Args:
        articles (list[dict]): The list of raw article dictionaries.
        output_csv_path (str): The full path for the final output CSV file.
    """
    updated_rows = []
    fieldnames = [
        'source_location', 'source_type', 'program_tag',
        'program_name', 'status', 'initiative_type', 'product_name'
    ]

    print("Enriching articles with product names...")
    for article in articles:
        source_location = article.get('source_location')
        if source_location:
            product_name = extract_product_name_from_url(source_location)
            article['product_name'] = product_name
        else:
            article['product_name'] = ""
        
        updated_rows.append(article)
    
    print(f"Writing final knowledge base to: {output_csv_path}")
    try:
        with open(output_csv_path, mode='w', encoding='utf-8', newline='') as outfile:
            writer = csv.DictWriter(outfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(updated_rows)
        print(f"Successfully created the final knowledge base with {len(updated_rows)} entries.")
    except Exception as e:
        print(f"An error occurred while writing the CSV: {e}")

def read_existing_knowledge_base(file_path: str) -> List[Dict[str, Any]]:
    """Reads an existing knowledge base CSV into a list of dictionaries.

    Args:
        file_path: Path to CSV file.

    Returns:
        List of dictionaries representing CSV rows.
    """
    articles = []
    try:
        with open(file_path, mode='r', encoding='utf-8') as infile:
            reader = csv.DictReader(infile)
            for row in reader:
                articles.append(row)
    except FileNotFoundError:
        print(f"Error: Could not find file at {file_path}")
    return articles

def main() -> None:
    """Main function to run the knowledge base build process."""
    print("--- Starting Knowledge Base Build Process ---")

    # --- Step 1: Gather Raw Articles ---
    # This function scrapes all sources. If you have the raw data and only
    # want to re-run the enrichment, you can comment out this line.
    # raw_articles = gather_raw_articles_from_sources(SOURCES_CSV)
    
    existing_kb_path = OUTPUT_CSV
    raw_articles = read_existing_knowledge_base(existing_kb_path)

    # --- Step 2: Enrich and Save the Final Knowledge Base ---
    if raw_articles:
        enrich_and_save_knowledge_base(raw_articles, OUTPUT_CSV)
    else:
        print("No articles were gathered. Halting process.")

    print("--- Knowledge Base Build Process Complete ---")


if __name__ == "__main__":
    main()
