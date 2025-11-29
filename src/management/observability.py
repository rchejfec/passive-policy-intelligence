"""
Observability module for the AI Daily Digest Pipeline.
Handles logging of pipeline runs and metrics to the database.
"""

import psycopg2
from datetime import datetime

def create_observability_table(conn):
    """
    Creates the pipeline_runs table if it doesn't exist.

    Args:
        conn: A psycopg2 connection object.
    """
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS pipeline_runs (
        id SERIAL PRIMARY KEY,
        start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        end_time TIMESTAMP,
        status TEXT,
        articles_fetched INTEGER DEFAULT 0,
        articles_analyzed INTEGER DEFAULT 0,
        highlights_found INTEGER DEFAULT 0
    );
    """
    try:
        with conn.cursor() as cursor:
            cursor.execute(create_table_sql)
        conn.commit()
        print("Observability: 'pipeline_runs' table checked/created.")
    except psycopg2.Error as e:
        print(f"Observability Error: Failed to create table: {e}")
        conn.rollback()

def start_run(conn) -> int:
    """
    Starts a new pipeline run logging entry.

    Args:
        conn: A psycopg2 connection object.

    Returns:
        int: The ID of the new run.
    """
    insert_sql = """
    INSERT INTO pipeline_runs (status, start_time)
    VALUES (%s, %s)
    RETURNING id;
    """
    try:
        with conn.cursor() as cursor:
            cursor.execute(insert_sql, ('RUNNING', datetime.now()))
            run_id = cursor.fetchone()[0]
        conn.commit()
        print(f"Observability: Run started with ID {run_id}.")
        return run_id
    except psycopg2.Error as e:
        print(f"Observability Error: Failed to start run: {e}")
        conn.rollback()
        return -1 # Return invalid ID if failure

def end_run(conn, run_id: int, status: str, metrics_dict: dict):
    """
    Updates the pipeline run entry with end time, status, and metrics.

    Args:
        conn: A psycopg2 connection object.
        run_id: The ID of the run to update.
        status: The final status of the run ('SUCCESS', 'FAILURE').
        metrics_dict: A dictionary containing metrics to log.
                      Expected keys: 'articles_fetched', 'articles_analyzed', 'highlights_found'.
    """
    if run_id == -1:
        print("Observability: Invalid run ID, skipping end_run.")
        return

    update_sql = """
    UPDATE pipeline_runs
    SET end_time = %s,
        status = %s,
        articles_fetched = %s,
        articles_analyzed = %s,
        highlights_found = %s
    WHERE id = %s;
    """

    articles_fetched = metrics_dict.get('articles_fetched', 0)
    articles_analyzed = metrics_dict.get('articles_analyzed', 0)
    highlights_found = metrics_dict.get('highlights_found', 0)

    try:
        with conn.cursor() as cursor:
            cursor.execute(update_sql, (
                datetime.now(),
                status,
                articles_fetched,
                articles_analyzed,
                highlights_found,
                run_id
            ))
        conn.commit()
        print(f"Observability: Run {run_id} ended with status {status}.")
    except psycopg2.Error as e:
        print(f"Observability Error: Failed to end run: {e}")
        conn.rollback()
