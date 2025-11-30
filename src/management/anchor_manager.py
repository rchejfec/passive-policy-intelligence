# src/management/anchor_manager.py
"""Handles admin features on semantic_anchors and anchor_components tables in the db"""

import sqlite3
import csv
import sys
import questionary
from questionary import Choice
from typing import Optional, List, Tuple, Dict, Any, Set
from src.management.db_utils import get_db_connection, get_all_component_types

# --- NEW: Helper for case-insensitive matching ---
def _slugify(text: str) -> str:
    """Converts text to a simplified, comparable format.

    Args:
        text: The input string to slugify.

    Returns:
        The slugified string (lowercase and stripped).
    """
    return text.lower().strip()

# --- Core Database & Helper Functions ---

def _create_anchor_in_db(name: str, description: str, author: str, programs: List[str], tags: List[str], kb_items: List[str]) -> Optional[int]:
    """Writes a new anchor and its components to the database.

    Args:
        name: Name of the anchor.
        description: Description of the anchor.
        author: Author of the anchor.
        programs: List of associated programs.
        tags: List of associated tags.
        kb_items: List of associated KB items.

    Returns:
        The ID of the newly created anchor, or None if creation failed or skipped.
    """
    if not programs and not tags and not kb_items:
        print(f"❌ Error for anchor '{name}': Cannot create an anchor with no components. Please add at least one program, tag, or KB item.")
        return None

    conn = get_db_connection()
    try:
        with conn:
            # MODIFIED: Check for uniqueness against ALL anchors (active or inactive).
            if conn.execute("SELECT id FROM semantic_anchors WHERE name = ?", (name,)).fetchone():
                print(f"⚠️  Skipping: An anchor named '{name}' already exists in the database.")
                return None

            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO semantic_anchors (name, description, anchor_author) VALUES (?, ?, ?)",
                (name, description, author)
            )
            anchor_id = cursor.lastrowid

            components = []
            if programs:
                components.extend([("program", p, anchor_id) for p in programs])
            if tags:
                components.extend([("tag", t, anchor_id) for t in tags])
            if kb_items:
                components.extend([("kb_item", i, anchor_id) for i in kb_items])
            
            if components:
                cursor.executemany(
                    "INSERT INTO anchor_components (component_type, component_id, anchor_id) VALUES (?, ?, ?)",
                    components
                )
            print(f"✅ Successfully created anchor '{name}' with ID {anchor_id}.")
            return anchor_id

    except Exception as e:
        print(f"❌ An unexpected error occurred while creating anchor '{name}': {e}")
    finally:
        if conn:
            conn.close()
    return None


def _get_all_components() -> Tuple[List[str], List[str], List[str]]:
    """Fetches all possible component values from the database using the centralized utility.

    Returns:
        A tuple containing sorted lists of programs, tags, and KB items.
    """
    conn = get_db_connection()
    try:
        # One call to the centralized utility function
        all_components = get_all_component_types(conn)

        # Unpack the results into sorted lists for the interactive wizards
        programs = sorted(list(all_components.get('programs', set())))
        tags = sorted(list(all_components.get('tags', set())))
        
        # For kb_items, the wizards need the friendly product names (the values of the dict)
        kb_items = sorted(list(all_components.get('kb_items', {}).values()))
        
        return programs, tags, kb_items
    finally:
        if conn:
            conn.close()
# --- Public Command Functions ---
# list_anchors() and generate_template_csv() remain the same

def list_anchors() -> None:
    """Lists all ACTIVE semantic anchors and their components."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        # MODIFIED: Added 'WHERE sa.is_active = 1' to only show active anchors.
        cursor.execute("SELECT id, name, description, anchor_author FROM semantic_anchors WHERE is_active = 1 ORDER BY name")
        anchors = cursor.fetchall()

        if not anchors:
            print("No active semantic anchors found.")
            return

        print("--- Active Semantic Anchors ---")
        for anchor in anchors:
            anchor_id, name, description, author = anchor
            print(f"\n[ID: {anchor_id}] {name}" + (f" (by {author})" if author else ""))
            if description:
                print(f"  Description: {description}")
            
            cursor.execute("SELECT component_type, component_id FROM anchor_components WHERE anchor_id = ?", (anchor_id,))
            components = cursor.fetchall()
            if components:
                print("  Components:")
                for comp_type, comp_value in components:
                    print(f"    - {comp_type.capitalize()}: {comp_value}")
            else:
                print("  Components: (none)")
        print("\n------------------------")
    finally:
        if conn:
            conn.close()

def generate_template_csv() -> None:
    """Prints a CSV template string to standard output."""
    header = ['name', 'description', 'anchor_author', 'programs', 'tags', 'kb_items']
    sample_row = ['Sample AI Anchor', 'A sample description', 'Your Name', 'AI-Gov,Digital-ID', 'Ethics,Policy', 'Some Program Name']
    
    writer = csv.writer(sys.stdout)
    writer.writerow(header)
    writer.writerow(sample_row)
    print("\n# CSV template printed above. Redirect to a file with '> anchor_template.csv'", file=sys.stderr)

def create_anchors_from_file(file_path: str) -> None:
    """Creates anchors in bulk from a specified CSV file with validation.

    Args:
        file_path: Path to the CSV file containing anchor definitions.
    """
    print("Starting bulk import with validation...")
    
    # --- REVISED LOGIC ---
    # Step 1: Fetch all valid components directly from the centralized utility.
    conn = get_db_connection()
    try:
        all_components = get_all_component_types(conn)
    finally:
        if conn:
            conn.close()

    # Create sets for fast and accurate validation.
    valid_programs = all_components.get('programs', set())
    valid_tags = all_components.get('tags', set())
    # The valid KB item IDs are the KEYS of the 'kb_items' dictionary.
    valid_kb_item_ids = all_components.get('kb_items', {}).keys()
    # --- END REVISED LOGIC ---

    try:
        with open(file_path, mode='r', encoding='utf-8-sig') as infile:
            reader = csv.DictReader(infile)
            for row in reader:
                name = row.get('name', '').strip()
                if not name:
                    continue
                
                desc = row.get('description', '').strip()
                author = row.get('anchor_author', '').strip()
                
                # Step 2: Validate each component from the CSV
                programs_in_csv = [p.strip() for p in row.get('programs', '').split(',') if p.strip()]
                tags_in_csv = [t.strip() for t in row.get('tags', '').split(',') if t.strip()]
                kb_items_in_csv = [i.strip() for i in row.get('kb_items', '').split(',') if i.strip()]

                validated_programs = []
                for p in programs_in_csv:
                    if p in valid_programs:
                        validated_programs.append(p)
                    else:
                        print(f"⚠️  Warning for anchor '{name}': Program '{p}' not found. Skipping.")
                
                validated_tags = []
                for t in tags_in_csv:
                    if t in valid_tags:
                        validated_tags.append(t)
                    else:
                        print(f"⚠️  Warning for anchor '{name}': Tag '{t}' not found. Skipping.")
                        
                validated_kb_items = []
                for i in kb_items_in_csv:
                    # We now check directly against the set of valid source_locations
                    if i in valid_kb_item_ids:
                        validated_kb_items.append(i)
                    else:
                        print(f"⚠️  Warning for anchor '{name}': KB Item '{i}' not found. Skipping.")

                # Step 3: Create the anchor with only the validated components
                _create_anchor_in_db(name, desc, author, validated_programs, validated_tags, validated_kb_items)

    except FileNotFoundError:
        print(f"❌ Error: File not found at '{file_path}'")
    except Exception as e:
        print(f"❌ An error occurred while processing the file: {e}")

# create_anchor_interactive() remains the same
def create_anchor_interactive() -> None:
    """Launches an interactive wizard to create a single semantic anchor."""
    print("Launching interactive anchor creation wizard...")
    
    while True:
        name = questionary.text("Anchor Name:").ask()
        if not name:
            if questionary.confirm("Cancel anchor creation?").ask(): return
            else: continue
        name = name.strip()
        conn = get_db_connection()
        # MODIFIED: Check for uniqueness against ALL anchors (active or inactive).
        exists = conn.execute("SELECT id FROM semantic_anchors WHERE name = ?", (name,)).fetchone()
        conn.close()
        if exists:
            print(f"⚠️  An anchor named '{name}' already exists in the database. Please choose a different name.")
        else:
            break

    # Description and Author
    description = questionary.text("Description (optional):").ask()
    author = questionary.text("Author (optional):").ask()

    # Component selection
    selected_programs, selected_tags, selected_kb_items = [], [], []
    all_programs, all_tags, all_kb_items = _get_all_components()

    while True:
        # (The rest of the function logic remains unchanged)
        # Display current state
        print("\n--- Current Anchor ---")
        print(f"Name: {name}")
        print(f"Programs: {selected_programs or 'None'}")
        print(f"Tags: {selected_tags or 'None'}")
        print(f"KB Items: {selected_kb_items or 'None'}")
        print("----------------------")

        action = questionary.select(
            "What would you like to do?",
            choices=[
                "Add Programs",
                "Add Tags (Autocomplete)",
                "Add KB Items (Autocomplete)",
                "Remove Components",
                "Finish and Save Anchor",
                "Cancel"
            ]).ask()

        if action == "Add Programs":
            program_choices = [
                Choice(title=p, checked=p in selected_programs) for p in all_programs
            ]
            to_add = questionary.checkbox("Select programs:", choices=program_choices).ask()
            if to_add is not None: selected_programs = sorted(list(set(to_add)))
        
        elif action == "Add Tags (Autocomplete)":
            tag_to_add = questionary.autocomplete("Select a tag:", choices=all_tags).ask()
            if tag_to_add and tag_to_add not in selected_tags: selected_tags.append(tag_to_add)

        elif action == "Add KB Items (Autocomplete)":
            item_to_add = questionary.autocomplete("Select a KB Item:", choices=all_kb_items).ask()
            if item_to_add and item_to_add not in selected_kb_items: selected_kb_items.append(item_to_add)

        elif action == "Remove Components":
            all_selected = [f"Program: {p}" for p in selected_programs] + \
                           [f"Tag: {t}" for t in selected_tags] + \
                           [f"KB Item: {i}" for i in selected_kb_items]
            if not all_selected:
                print("No components to remove.")
                continue
            
            to_remove = questionary.checkbox("Select components to remove:", choices=all_selected).ask()
            if to_remove:
                for item in to_remove:
                    item_type, item_value = item.split(': ', 1)
                    if item_type == "Program": selected_programs.remove(item_value)
                    elif item_type == "Tag": selected_tags.remove(item_value)
                    elif item_type == "KB Item": selected_kb_items.remove(item_value)

        elif action == "Finish and Save Anchor":
            _create_anchor_in_db(name, description, author, selected_programs, selected_tags, selected_kb_items)
            break

        elif action == "Cancel" or action is None:
            if questionary.confirm("Are you sure you want to cancel?").ask():
                print("Anchor creation cancelled.")
                break
            

def delete_anchors_interactive() -> None:
    """Launches an interactive wizard to DEACTIVATE one or more semantic anchors.

    This performs a soft delete by setting the 'is_active' flag to 0.
    """
    conn = get_db_connection()
    try:
        # MODIFIED: Only fetch active anchors to be deactivated.
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, anchor_author FROM semantic_anchors WHERE is_active = 1 ORDER BY name")
        anchors = cursor.fetchall()
    finally:
        if conn:
            conn.close()

    if not anchors:
        print("No active anchors to deactivate.")
        return

    choices = [Choice(title=f"{name} (ID: {id})" + (f" by {author}" if author else ""), value=id) for id, name, author in anchors]

    selected_ids = questionary.checkbox(
        "Select anchors to DEACTIVATE (they will be hidden but their history preserved):",
        choices=choices
    ).ask()

    if not selected_ids:
        print("No anchors selected. Operation cancelled.")
        return

    print("\nYou have selected the following anchors for deactivation:")
    for choice in choices:
        if choice.value in selected_ids:
            print(f" - {choice.title}")

    # MODIFIED: Updated confirmation text for clarity.
    confirm = questionary.confirm(
        f"Are you sure you want to deactivate these {len(selected_ids)} anchor(s)? They will no longer be used in analysis.",
        default=False
    ).ask()

    if confirm:
        conn = get_db_connection()
        try:
            with conn:
                placeholders = ', '.join('?' for _ in selected_ids)
                # MODIFIED: Perform an UPDATE (soft delete) instead of a DELETE.
                conn.execute(f"UPDATE semantic_anchors SET is_active = 0 WHERE id IN ({placeholders})", selected_ids)
            print(f"\n✅ Successfully deactivated {len(selected_ids)} anchor(s).")
        except Exception as e:
            print(f"❌ An error occurred during deactivation: {e}")
        finally:
            if conn:
                conn.close()
    else:
        print("Deactivation cancelled.")
