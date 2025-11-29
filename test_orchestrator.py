# test_orchestrator.py
import os
import sys
import psycopg2
from src.management import db_utils

try:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:
    SCRIPT_DIR = os.path.abspath('')
ROOT_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

# We will import the script modules here as we refactor them
# from src.ingestion import index_knowledge_base
from src.ingestion import rss_fetcher
from src.ingestion import index_articles
from src.analysis import analyze_articles
from src.analysis import enrich_articles
from src.delivery import engine as delivery_engine
from src.management import observability

def run_pipeline():
    """
    Main orchestrator function to run the data pipeline steps sequentially.
    """
    conn = None
    run_id = -1
    metrics = {
        'articles_fetched': 0,
        'articles_analyzed': 0,
        'highlights_found': 0
    }
    status = 'FAILURE' # Default to failure until success

    print("--- ORCHESTRATOR: Starting Pipeline ---")
    try:
        # 1. Establish a single database connection for the entire pipeline
        conn = db_utils.get_db_connection()
        print("ORCHESTRATOR: Database connection successful.")

        # Initialize observability
        observability.create_observability_table(conn)
        run_id = observability.start_run(conn)

        # print("\n--- STEP ONLY WHEN FLAGGED: Running Knowledge Base Indexer ---")
        # index_knowledge_base.main(conn)

        # --- PIPELINE STEPS ---
        # We will uncomment and test these one by one.
        
        print("\n--- STEP: Running RSS Fetcher ---")
        metrics['articles_fetched'] = rss_fetcher.main(conn) or 0

        print("\n--- STEP: Running Article Indexer ---")
        index_articles.main(conn)

        print("\n--- STEP: Running Article Analyzer ---")
        metrics['articles_analyzed'] = analyze_articles.main(conn) or 0

        print("\n--- STEP: Running Article Enricher ---")
        metrics['highlights_found'] = enrich_articles.main(conn) or 0
        
        # ... inside run_pipeline() ...
        print("\n--- STEP: Running Delivery Engine ---")
        delivery_engine.main(conn)

        # ADDED: Commit the transaction only after all steps succeed.
        print("\nORCHESTRATOR: All steps completed, committing transaction...")
        conn.commit()

        # Export data to parquet files for portal (after successful commit)
        print("\n--- STEP: Running Data Export ---")
        import subprocess
        export_script = os.path.join(SCRIPT_DIR, 'scripts', 'export_to_parquet.py')
        result = subprocess.run([sys.executable, export_script], capture_output=True, text=True)
        if result.returncode != 0:
            print(f"WARNING: Data export failed: {result.stderr}")
            print("Pipeline completed but portal data may not be updated.")
        else:
            print(result.stdout)

        status = 'SUCCESS'
        print("ORCHESTRATOR: Transaction committed successfully.")

    except psycopg2.Error as db_error:
        print(f"\nFATAL: A database error occurred in the orchestrator: {db_error}")
        if conn:
            # Rollback any pending transactions if an error occurs
            conn.rollback()

    except Exception as e:
        print(f"\nFATAL: An error occurred in the orchestrator: {e}")
        if conn:
            print("ORCHESTRATOR: Rolling back transaction...")
            conn.rollback()

    finally:
        if conn and run_id != -1:
            try:
                observability.end_run(conn, run_id, status, metrics)
            except Exception as e:
                print(f"ORCHESTRATOR: Failed to log run completion: {e}")

        # 4. Ensure the connection is always closed
        if conn:
            conn.close()
            print("\nORCHESTRATOR: Database connection closed.")
        print("--- ORCHESTRATOR: Pipeline Finished ---")


if __name__ == "__main__":
    run_pipeline()