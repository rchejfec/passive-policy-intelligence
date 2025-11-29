# src/management/testing_manager.py
"""
Contains functions for generating test data for the application.
"""

import os
import csv
import random
from src.management.db_utils import get_db_connection, get_all_component_types

# --- Configuration (Moved from original script) ---
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUTPUT_DIR = os.path.join(ROOT_DIR, 'output')
AUTHOR_NAME = "AutoGen"
ANCHOR_NAME_TAG = "(test3)"

# 3. List the specific tags you want to create individual anchors for.
#    The script will verify these exist in the 'tags' table.
TAGS_TO_INCLUDE = [
    'Employment Insurance',
    'AI governance',
    'Artificial intelligence',
    'Data governance',
    'Cybersecurity'
]

# 4. Set individual program anchors you want to create.
PROGRAMS_TO_INCLUDE = [
    'empowering-canadas-workforce',
    'toward-a-more-equitable-canada',
    'the-community-transformations-project',
    'affordability-action-council',
    'building-new-foundations-for-economic-growth',
    'not real' # Example: This may not exist and will trigger a warning
]
# 5. Manually define complex anchors that combine different components.
#    The script will validate that the specified programs and tags exist.
MANUAL_COMBINATION_ANCHORS = {
    "Complex: Test Anchor A (test2)": {
        "description": "A combination anchor for testing workforce and equity programs.",
        "programs": ["empowering-canadas-workforce", "toward-a-more-equitable-canada"],
        "tags": ["Employment Insurance", "Artificial intelligence"],
        "kb_items": ["https://irpp.org/research-studies/measuring-community-workforce-exposure-to-us-exports/"]
    },
    "Complex: Test Anchor B (test2)": {
        "description": "A combination anchor for testing affordability and equity programs.",
        "programs": ['affordability-action-council', 'toward-a-more-equitable-canada'],
        "tags": [],
        "kb_items": []
    }
}

def generate_test_anchors_csv(output_path=None):
    """Fetches components from the DB and generates a test anchors CSV file."""
    if output_path is None:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        output_path = os.path.join(OUTPUT_DIR, 'test_anchors_generated.csv')

    print("--- Starting Test Anchor Generation ---")
    conn = get_db_connection()
    all_components = get_all_component_types(conn)
    all_kb_items = all_components.get('kb_items', {})
    all_programs = all_components.get('programs', set())
    all_tags = all_components.get('tags', set())

    # (Validation logic from original script is simplified here for brevity,
    # but could be ported over if strict validation is needed again)
    
    anchors_to_write = []
    # Add individual Program anchors
    for program in sorted(PROGRAMS_TO_INCLUDE):
        if program in all_programs:
            anchors_to_write.append({'name': f"PROG: {program} (test2)", 'programs': program})
    # Add individual Tag anchors
    for tag in sorted(TAGS_TO_INCLUDE):
        if tag in all_tags:
            anchors_to_write.append({'name': f"TAG: {tag} (test2)", 'tags': tag})
    # Add manual combination anchors
    for name, components in MANUAL_COMBINATION_ANCHORS.items():
        anchors_to_write.append({
            'name': name, 'description': components.get('description', ''),
            'programs': ','.join(components.get('programs', [])),
            'tags': ','.join(components.get('tags', [])),
            'kb_items': ','.join(components.get('kb_items', []))
        })

    header = ['name', 'description', 'anchor_author', 'programs', 'tags', 'kb_items']
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        for anchor_data in anchors_to_write:
            row = {'anchor_author': AUTHOR_NAME, **anchor_data}
            writer.writerow({k: v for k, v in row.items() if k in header})

    conn.close()
    print(f"\n✅ Successfully generated {len(anchors_to_write)} test anchors to '{output_path}'.")


def generate_test_subscribers_csv(output_path=None):
    """Generates a test subscribers CSV file with subscriptions to active anchors."""
    if output_path is None:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        output_path = os.path.join(OUTPUT_DIR, 'test_subscribers_generated.csv')

    print("--- Starting Test Subscriber Generation ---")
    conn = get_db_connection()
    
    # Fetch active anchors to subscribe users to
    active_anchors = [row[0] for row in conn.execute("SELECT name FROM semantic_anchors WHERE is_active = 1").fetchall()]
    conn.close()

    if not active_anchors:
        print("⚠️  Warning: No active anchors found in the database. Cannot generate subscriptions.")
        return

    subscribers_to_write = [
        {'name': 'Admin User', 'email': 'admin@example.com', 'anchors': random.sample(active_anchors, min(len(active_anchors), 2))},
        {'name': 'Test User Two', 'email': 'test2@example.com', 'anchors': random.sample(active_anchors, min(len(active_anchors), 3))},
        {'name': 'Test User Three', 'email': 'test3@example.com', 'anchors': random.sample(active_anchors, min(len(active_anchors), 1))}
    ]

    header = ['name', 'email', 'anchors']
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        for sub_data in subscribers_to_write:
            row = {
                'name': sub_data.get('name'),
                'email': sub_data.get('email'),
                'anchors': ','.join(sub_data.get('anchors', []))
            }
            writer.writerow(row)
            
    print(f"\n✅ Successfully generated {len(subscribers_to_write)} test subscribers to '{output_path}'.")