
import os
import sys
import psycopg2

# Ensure src is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.management import db_utils

def verify_data():
    print("--- Verifying Observability Data ---")
    try:
        conn = db_utils.get_db_connection()
        with conn.cursor() as cursor:
            # Check if table exists
            cursor.execute("""
                SELECT exists (
                    SELECT FROM information_schema.tables
                    WHERE  table_schema = 'public'
                    AND    table_name   = 'pipeline_runs'
                );
            """)
            table_exists = cursor.fetchone()[0]

            if not table_exists:
                print("FAILURE: Table 'pipeline_runs' does not exist.")
                return

            print("SUCCESS: Table 'pipeline_runs' exists.")

            # Get the last 5 runs
            cursor.execute("""
                SELECT id, start_time, end_time, status,
                       articles_fetched, articles_analyzed, highlights_found
                FROM pipeline_runs
                ORDER BY id DESC
                LIMIT 5
            """)
            rows = cursor.fetchall()

            if not rows:
                print("Table is empty. No runs recorded yet.")
            else:
                print(f"\nFound {len(rows)} recent runs:")
                print(f"{'ID':<5} | {'Status':<10} | {'Fetched':<8} | {'Analyzed':<9} | {'Highlights':<10} | {'Start Time'}")
                print("-" * 80)
                for row in rows:
                    # Handle potential None values for formatting
                    start_time = row[1].strftime('%Y-%m-%d %H:%M:%S') if row[1] else 'N/A'
                    print(f"{row[0]:<5} | {row[3]:<10} | {row[4]:<8} | {row[5]:<9} | {row[6]:<10} | {start_time}")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    verify_data()
