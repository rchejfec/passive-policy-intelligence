#!/usr/bin/env python3
"""
Test script for digest delivery - generates the adaptive card JSON without sending to Teams.
This allows you to preview the card structure and validate the demo branding.
"""
import os
import sys
import json
from datetime import datetime

# Fix Windows console encoding for Unicode characters
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

sys.path.append(os.path.dirname(__file__))
from src.management.db_utils import get_db_connection
from src.delivery import engine

def test_digest_generation(dry_run=True):
    """
    Test the digest generation with demo data.

    Args:
        dry_run: If True, only generates and prints the JSON without sending to Teams.
    """
    print("=" * 80)
    print("TESTING: Passive Policy Intelligence (PPI) Digest - DEMO MODE")
    print("=" * 80)

    conn = get_db_connection()

    try:
        # Fetch candidates
        print("\n1. Fetching candidate articles from database...")
        raw_df = engine.fetch_candidates(conn)

        if raw_df.empty:
            print("   ⚠️  No articles found in the last 60 hours.")
            print("   This is normal if the database doesn't have recent demo data.")
            return

        print(f"   ✓ Found {len(raw_df)} article-anchor pairs")

        # Process articles
        print("\n2. Processing and aggregating articles...")
        all_articles = engine.process_articles(raw_df)
        print(f"   ✓ Processed {len(all_articles)} unique articles")

        # Filter by scope (DEMO anchors)
        print("\n3. Filtering by DEMO semantic anchors...")
        filtered_articles = engine.filter_by_scope(all_articles)

        if not filtered_articles:
            print("   ⚠️  No articles matched DEMO semantic anchors.")
            print("   Check that your database has articles linked to anchors prefixed with 'DEMO:'")
            return

        print(f"   ✓ Filtered to {len(filtered_articles)} articles matching DEMO anchors")

        # Select content for sections
        print("\n4. Selecting content for digest sections...")
        final_sections = engine.select_content(filtered_articles)

        total_items = sum(len(v) for v in final_sections.values())
        print(f"   ✓ Selected {total_items} articles across {len(final_sections)} sections")

        for section_title, articles in final_sections.items():
            if articles:
                print(f"      • {section_title}: {len(articles)} articles")

        # Generate the adaptive card
        print("\n5. Generating Adaptive Card JSON...")
        from src.delivery import renderer
        card_payload = renderer.render_digest_card(final_sections, len(all_articles))

        print("   ✓ Card generated successfully")

        # Display card preview
        print("\n" + "=" * 80)
        print("ADAPTIVE CARD PREVIEW")
        print("=" * 80)

        # Extract key information from the card
        card_body = card_payload["attachments"][0]["content"]["body"]

        print("\n📋 CARD HEADER:")
        for item in card_body[:3]:  # First 3 items are the header
            if item.get("type") == "TextBlock":
                print(f"   {item.get('text')}")

        print("\n📊 SECTIONS:")
        section_count = 0
        for item in card_body:
            if item.get("type") == "ActionSet" and "actions" in item:
                for action in item["actions"]:
                    if action.get("type") == "Action.ToggleVisibility":
                        print(f"   • {action.get('title')}")
                        section_count += 1
            elif item.get("type") == "Container" and any("Priority" in str(i) for i in card_body if isinstance(i, dict)):
                if section_count == 0:  # Priority section
                    print(f"   • 🚨 Priority Highlights (always visible)")
                    section_count += 1

        print("\n🔗 ACTION BUTTON:")
        for item in card_body:
            if item.get("type") == "ActionSet" and item.get("spacing") == "Large":
                for action in item["actions"]:
                    if action.get("type") == "Action.OpenUrl":
                        print(f"   {action.get('title')}")
                        print(f"   URL: {action.get('url')}")

        print("\n" + "=" * 80)
        print("FULL JSON OUTPUT (for testing in Adaptive Cards Designer)")
        print("https://adaptivecards.io/designer/")
        print("=" * 80)
        print(json.dumps(card_payload, indent=2))

        if dry_run:
            print("\n" + "=" * 80)
            print("✅ DRY RUN COMPLETE - No message sent to Teams")
            print("=" * 80)
            print("\nTo send to Teams, set TEAMS_WEBHOOK_URL in .env and run:")
            print("python src/delivery/engine.py")

    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        import traceback
        traceback.print_exc()

    finally:
        conn.close()

if __name__ == "__main__":
    test_digest_generation(dry_run=True)
