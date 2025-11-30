# src/delivery/renderer.py
import re
from datetime import datetime
from src.delivery import config
from typing import Dict, List, Any

def _format_tag(anchor_name: str) -> str:
    """Formats an anchor name into a short tag (e.g., #PROG:AAC).

    Args:
        anchor_name: Full anchor name.

    Returns:
        Formatted tag.
    """
    if not anchor_name: return ""
    if anchor_name.startswith("http"): return "#REF"
    
    if ":" in anchor_name:
        parts = anchor_name.split(":", 1)
        prefix = parts[0].strip().upper()
        body = parts[1].strip()
    else:
        prefix = ""
        body = anchor_name.strip()

    clean_body = re.sub(r'[^a-zA-Z0-9\s\-]', '', body)
    words = re.split(r'[\s\-]+', clean_body)
    
    if len(words) == 1 and len(words[0]) < 10:
        initials = words[0]
    else:
        initials = "".join([w[0].upper() for w in words if w])

    if prefix: return f"#{prefix}:{initials}"
    return f"#{initials}"

def _generate_section_id(title: str) -> str:
    """Generates a safe, unique ID for the collapsible container.

    Args:
        title: Section title.

    Returns:
        Unique ID string.
    """
    return re.sub(r'[^a-zA-Z0-9]', '', title).lower()

def render_digest_card(sections_data: Dict[str, List[Any]], total_articles: int) -> Dict[str, Any]:
    """
    Generates the Microsoft Teams Adaptive Card JSON with Accordion Sections.

    Args:
        sections_data: Dictionary mapping section titles to lists of articles.
        total_articles: Total count of articles processed.

    Returns:
        Dictionary representing the Adaptive Card JSON.
    """
    
    # 1. Header (unchanged)
    card_body = [
        {
            "type": "TextBlock",
            "size": "Large",
            "weight": "Bolder",
            "text": "☕ Daily Intelligence Briefing"
        },
        {
            "type": "TextBlock",
            "size": "Small",
            "isSubtle": True,
            "text": f"{datetime.now().strftime('%B %d, %Y')} | {total_articles} Articles Processed",
            "spacing": "None"
        }
    ]

    # 2. Sections
    for section_title, articles in sections_data.items():
        # Determine Style & IDs
        style = config.SECTIONS.get(section_title, {}).get("color", "Accent")
        section_id = _generate_section_id(section_title)
        is_priority = "Priority" in section_title

        # If non-priority section is empty, skip the entire thing (header and all)
        if not is_priority and not articles:
            continue

        # --- A. Section Header ---
        if is_priority:
            # Priority is ALWAYS VISIBLE -> Standard Text Header
            card_body.append({
                "type": "Container",
                "spacing": "Large",
                "items": [
                    {
                        "type": "TextBlock",
                        "text": section_title,
                        "weight": "Bolder",
                        "size": "Medium",
                        "color": style
                    }
                ]
            })
        else:
            # Others are COLLAPSIBLE -> Button Header
            card_body.append({
                "type": "ActionSet",
                "spacing": "Medium",
                "actions": [
                    {
                        "type": "Action.ToggleVisibility",
                        "title": f"{section_title} ({len(articles)})  ▼",
                        "targetElements": [section_id],
                        "style": "default"
                    }
                ]
            })

        # --- B. Section Content (Articles) ---
        article_items = []

        if not articles and is_priority:
            # Fallback message for empty Priority section
            article_items.append({
                "type": "TextBlock",
                "text": "✅ No Priority Highlights found in the last 24 hours.",
                "size": "Small",
                "isSubtle": True
            })
        elif articles:
            # Loop through articles only if content exists
            for article in articles:
                short_tags = [_format_tag(a) for a in article.anchors[:3]]
                tag_str = " ".join(short_tags)
                
                # STACKED LAYOUT CONTAINER
                article_items.append({
                    "type": "Container",
                    "spacing": "Medium",
                    "items": [
                        # ROW 1: Title
                        {
                            "type": "TextBlock",
                            "text": f"[{article.title}]({article.url})",
                            "wrap": True,
                            "weight": "Bolder",
                            "size": "Default"
                        },
                        # ROW 2: Metadata
                        {
                            "type": "ColumnSet",
                            "spacing": "Small",
                            "columns": [
                                {
                                    "type": "Column",
                                    "width": "stretch",
                                    "items": [
                                        {
                                            "type": "TextBlock",
                                            "text": f"_{article.source_name}_",
                                            "isSubtle": True,
                                            "size": "Small",
                                            "wrap": True
                                        }
                                    ]
                                },
                                {
                                    "type": "Column",
                                    "width": "auto",
                                    "items": [
                                        {
                                            "type": "TextBlock",
                                            "text": tag_str,
                                            "color": "Good",
                                            "size": "Small",
                                            "horizontalAlignment": "Right"
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                })

        # Container that holds the articles
        section_container = {
            "type": "Container",
            "id": section_id,
            "items": article_items,
            "spacing": "None"
        }
        
        if not is_priority:
            section_container["isVisible"] = False

        card_body.append(section_container)


    # 3. Footer / Actions (unchanged)
    card_body.append({
        "type": "ActionSet",
        "spacing": "Large",
        "actions": [
            {
                "type": "Action.OpenUrl",
                "title": "📊 Open Full Dashboard",
                "url": config.DASHBOARD_URL,
                "style": "positive"
            }
        ]
    })
    
    card_body.append({
        "type": "TextBlock",
        "text": "This briefing was generated automatically by the AI Daily Digest Pipeline.",
        "isSubtle": True,
        "size": "Small",
        "horizontalAlignment": "Center",
        "spacing": "Medium"
    })

    # 4. Wrap in Final JSON (unchanged)
    return {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {
                    "type": "AdaptiveCard",
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "version": "1.4",
                    "body": card_body
                }
            }
        ]
    }
