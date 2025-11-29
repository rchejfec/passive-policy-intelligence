# src/management/subscriber_manager.py
"""Handles admin features on subscribers and subscriptions tables in the db"""

import sqlite3
import csv
import questionary
from questionary import Choice  # <-- Add this import line
from src.management.db_utils import get_db_connection, slugify

def list_subscribers():
    """Lists all subscribers and their ACTIVE anchor subscriptions."""
    conn = get_db_connection()
    try:
        # MODIFIED: The final LEFT JOIN now also checks if the anchor is active.
        query = """
        SELECT s.id, s.email, s.name, GROUP_CONCAT(sa.name, '; ')
        FROM subscribers s
        LEFT JOIN subscriptions sub ON s.id = sub.subscriber_id
        LEFT JOIN semantic_anchors sa ON sub.anchor_id = sa.id AND sa.is_active = 1
        GROUP BY s.id, s.email, s.name
        ORDER BY s.id;
        """
        subscribers = conn.execute(query).fetchall()

        if not subscribers:
            print("No subscribers found.")
            return

        print("--- Subscribers (showing active subscriptions only) ---")
        for sub_id, email, name, anchors in subscribers:
            print(f"\n[ID: {sub_id}] {name} <{email}>")
            if anchors:
                print(f"  Subscriptions: {anchors}")
            else:
                print("  Subscriptions: (none)")
        print("\n-------------------")

    finally:
        if conn:
            conn.close()

def add_subscriber(email: str, name: str, override: bool = False, conn: sqlite3.Connection = None):
    """Adds or updates a single subscriber, returns their ID. Can use an existing db connection."""
    # If no connection is passed, create a temporary one.
    close_conn_after = False
    if conn is None:
        conn = get_db_connection()
        close_conn_after = True

    subscriber_id = None
    try:
        with conn:
            existing = conn.execute("SELECT id FROM subscribers WHERE email = ?", (email,)).fetchone()
            
            if existing:
                subscriber_id = existing[0]
                if override:
                    conn.execute("UPDATE subscribers SET name = ? WHERE id = ?", (name, subscriber_id))
                    print(f"✅ Updated subscriber: {name} <{email}>")
                else:
                    print(f"⚠️  Skipped: Subscriber <{email}> already exists. Use --override to update.")
            else:
                cursor = conn.execute("INSERT INTO subscribers (email, name) VALUES (?, ?)", (email, name))
                subscriber_id = cursor.lastrowid
                print(f"✅ Added subscriber: {name} <{email}>")
        
        # Re-fetch ID if it was an update and we didn't have it
        if subscriber_id is None and existing:
             subscriber_id = existing[0]
        
        return subscriber_id
    except Exception as e:
        print(f"❌ An error occurred while adding subscriber {email}: {e}")
    finally:
        if close_conn_after and conn:
            conn.close()
    return subscriber_id


def import_subscribers_from_file(file_path: str):
    """Imports subscribers and their subscriptions from a CSV file."""
    print("Starting subscriber import with validation...")
    conn = get_db_connection() # Open one connection for the whole process
    try:
        # MODIFIED: Only fetch active anchors for validation.
        anchor_map = {slugify(name): id for id, name in conn.execute("SELECT id, name FROM semantic_anchors WHERE is_active = 1").fetchall()}

        with open(file_path, mode='r', encoding='utf-8-sig') as infile:
            reader = csv.DictReader(infile)
            for row in reader:
                email = row.get('email', '').strip()
                name = row.get('name', '').strip()
                if not email or not name:
                    continue

                # Pass the existing connection to the add_subscriber function
                subscriber_id = add_subscriber(email, name, override=True, conn=conn)

                if not subscriber_id:
                    continue
                
                anchors_in_csv = [a.strip() for a in row.get('anchors', '').split(',') if a.strip()]
                for anchor_name in anchors_in_csv:
                    slug_anchor = slugify(anchor_name)
                    if slug_anchor in anchor_map:
                        anchor_id = anchor_map[slug_anchor]
                        conn.execute(
                            "INSERT OR IGNORE INTO subscriptions (subscriber_id, anchor_id) VALUES (?, ?)",
                            (subscriber_id, anchor_id)
                        )
                    else:
                        print(f"⚠️  Warning for subscriber '{email}': Active anchor '{anchor_name}' not found. Skipping subscription.")
        conn.commit() # Commit all changes at the very end
    except FileNotFoundError:
        print(f"❌ Error: File not found at '{file_path}'")
    except Exception as e:
        print(f"❌ An error occurred during import: {e}")
    finally:
        if conn:
            conn.close() # Close the single connection


## Add this entire function to the end of the file.

def delete_subscribers_interactive():
    """Launches an interactive wizard to delete one or more subscribers."""
    conn = get_db_connection()
    try:
        subscribers = conn.execute("SELECT id, name, email FROM subscribers ORDER BY name").fetchall()
    finally:
        if conn:
            conn.close()

    if not subscribers:
        print("No subscribers to delete.")
        return

    choices = [Choice(title=f"{name} <{email}> (ID: {id})", value=id) for id, name, email in subscribers]

    selected_ids = questionary.checkbox(
        "Select subscribers to delete (use spacebar to select, enter to confirm):",
        choices=choices
    ).ask()

    if not selected_ids:
        print("No subscribers selected. Deletion cancelled.")
        return

    print("\nYou have selected the following subscribers for deletion:")
    for choice in choices:
        if choice.value in selected_ids:
            print(f" - {choice.title}")
    
    confirm = questionary.confirm(
        f"Are you sure you want to permanently delete these {len(selected_ids)} subscriber(s)? This action cannot be undone.",
        default=False
    ).ask()

    if confirm:
        conn = get_db_connection()
        try:
            with conn:
                placeholders = ', '.join('?' for _ in selected_ids)
                conn.execute(f"DELETE FROM subscribers WHERE id IN ({placeholders})", selected_ids)
            print(f"\n✅ Successfully deleted {len(selected_ids)} subscriber(s).")
        except Exception as e:
            print(f"❌ An error occurred during deletion: {e}")
        finally:
            if conn:
                conn.close()
    else:
        print("Deletion cancelled.")