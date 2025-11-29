# --- src/management/db_utils.py ---

"""
Centralized database connection utility for PostgreSQL.
"""

import os
import psycopg2
from dotenv import load_dotenv

# Determine the project root and load the .env file from there
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

def get_db_connection():
    """
    Establishes and returns a connection to the PostgreSQL database.
    
    Reads the connection string from the DATABASE_URL environment variable.
    
    Returns:
        A psycopg2 connection object, or raises an exception if the connection fails.
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