# src/management/db_utils.py

"""
Centralized database connection utility for PostgreSQL.
"""

import os
import psycopg2
import psycopg2.extensions
from typing import Dict, Any, Set
from dotenv import load_dotenv

# Determine the project root and load the .env file from there
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

def get_db_connection() -> psycopg2.extensions.connection:
    """Establish connection to PostgreSQL database.

    Reads the connection string from the DATABASE_URL environment variable.

    Returns:
        Active PostgreSQL database connection.

    Raises:
        ValueError: If DATABASE_URL environment variable is not set.
        psycopg2.OperationalError: If connection to database fails.
    """
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL environment variable not set. Please check your .env file.")
    
    try:
        conn = psycopg2.connect(db_url)
        return conn
    except psycopg2.OperationalError as e:
        # Provide a more user-friendly error message
        print(f"FATAL: Could not connect to the database: {e}")
        raise

def slugify(text: str) -> str:
    """Converts text to a simplified, comparable format.

    Args:
        text: Text to slugify.

    Returns:
        Slugified text.
    """
    if not text:
        return ""
    return text.lower().strip()

def get_all_component_types(conn: psycopg2.extensions.connection) -> Dict[str, Any]:
    """Fetches all component types (programs, tags, kb_items).

    Args:
        conn: Database connection.

    Returns:
        Dict containing sets of programs, tags, and kb_items.
    """
    components = {
        'programs': set(),
        'tags': set(),
        'kb_items': {}
    }

    try:
        with conn.cursor() as cursor:
            # Fetch tags
            # We use a nested try/except block to handle cases where tables might not exist yet
            # allowing the function to return partial data instead of crashing.
            try:
                cursor.execute("SELECT tag_name FROM tags")
                components['tags'] = {row[0] for row in cursor.fetchall()}
            except psycopg2.Error:
                conn.rollback()

            # Fetch programs
            try:
                cursor.execute("SELECT DISTINCT program_tag FROM knowledge_base WHERE program_tag IS NOT NULL")
                components['programs'] = {row[0] for row in cursor.fetchall()}
            except psycopg2.Error:
                conn.rollback()

            # Fetch kb_items
            try:
                cursor.execute("SELECT source_location, product_name FROM knowledge_base")
                components['kb_items'] = {row[0]: row[1] for row in cursor.fetchall()}
            except psycopg2.Error:
                conn.rollback()

    except psycopg2.Error as e:
        print(f"Error fetching components: {e}")
        # Return what we have or empty structure

    return components
