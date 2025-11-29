"""
Manages the integration of program charters into the knowledge base.

This script is designed to be both runnable from the command line and
importable as a module. It scans a specified directory for program charter
markdown files, parses them to extract metadata, and adds them as new entries
to the knowledge_base.csv file.

It ensures that charters are not duplicated and safely handles file paths
and ID generation.
"""

#TODO: add check if program exists logic; 
#       ensure path is aligned with indexing script
#       create sample script to update chroma

import os
import re
import pandas as pd
from typing import Any

def slugify(text: str) -> str:
    """
    Converts a string into a URL-friendly "slug".
    Example: "The Affordability Action Council" -> "the-affordability-action-council"

    Args:
        text: Input string.

    Returns:
        Slugified string.
    """
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s-]', '', text)  # Remove special characters
    text = re.sub(r'[\s-]+', '-', text)      # Replace spaces and hyphens with a single hyphen
    return text.strip('-')

def update_kb_with_charters(kb_path: str, charters_dir: str) -> None:
    """
    Scans a directory for program charter files and adds them to the knowledge base CSV.

    Args:
        kb_path (str): The file path to the knowledge_base.csv file.
        charters_dir (str): The directory containing the program charter .md files.
    """
    print("--- Starting: Update Knowledge Base with Program Charters ---")
    
    # --- 1. Load the existing Knowledge Base ---
    try:
        kb_df = pd.read_csv(kb_path)
        print(f"Successfully loaded '{os.path.basename(kb_path)}' with {len(kb_df)} rows.")
    except FileNotFoundError:
        print(f"Error: Knowledge base file not found at '{kb_path}'")
        return

    # --- 2. Scan for charter files ---
    try:
        charter_files = [f for f in os.listdir(charters_dir) if f.endswith('.md')]
        if not charter_files:
            print("No new charter files found.")
            return
        print(f"Found {len(charter_files)} charter files in '{charters_dir}'.")
    except FileNotFoundError:
        print(f"Error: Charters directory not found at '{charters_dir}'")
        return

    # --- 3. Process each charter file ---
    new_charters = []
    for filename in charter_files:
        match = re.search(r'Program Charter - (.*)\.md', filename)
        if not match:
            print(f"Warning: Skipping file with unexpected name format: {filename}")
            continue
            
        program_name = match.group(1).strip()
        program_tag = slugify(program_name)
        source_location = os.path.join('user_content', os.path.basename(charters_dir), filename).replace('\\', '/')

        # Check if a charter for this program already exists
        # This is more robust than the previous check
        mask = (kb_df['program_tag'] == program_tag) & (kb_df['source_type'] == 'program_charter')
        if mask.any():
            print(f"Skipping '{program_name}', a charter already exists for this program.")
            continue

        print(f"Processing new charter for program: '{program_name}'")
        new_charters.append({
            'source_location': source_location,
            'source_type': 'program_charter',
            'program_tag': program_tag,
            'program_name': program_name,
            'status': 'published',
            'initiative_type': 'program',
            'product_name': f"Program Charter: {program_name}"
        })

    # --- 4. Add new charters and save ---
    if new_charters:
        new_charters_df = pd.DataFrame(new_charters)
        updated_kb_df = pd.concat([kb_df, new_charters_df], ignore_index=True)
        
        # **FIXED ID GENERATION**
        # Regenerate the ID column for the entire DataFrame to ensure it's clean and sequential.
        updated_kb_df['id'] = range(1, len(updated_kb_df) + 1)
        
        # Reorder columns to have 'id' first, if it wasn't already
        cols = ['id'] + [col for col in updated_kb_df.columns if col != 'id']
        updated_kb_df = updated_kb_df[cols]
        
        updated_kb_df.to_csv(kb_path, index=False)
        print(f"\nSuccessfully added {len(new_charters)} new charters to the knowledge base.")
        print(f"'{os.path.basename(kb_path)}' has been updated.")
    else:
        print("\nNo new charters to add. Knowledge base is already up to date.")
        
    print("--- Finished ---")


if __name__ == '__main__':
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(os.path.dirname(script_dir))
    
    KNOWLEDGE_BASE_PATH = os.path.join(root_dir, 'user_content', 'knowledge_base.csv')
    CHARTERS_DIR_PATH = os.path.join(root_dir, 'user_content', 'program_project_charters')
    
    update_kb_with_charters(KNOWLEDGE_BASE_PATH, CHARTERS_DIR_PATH)
