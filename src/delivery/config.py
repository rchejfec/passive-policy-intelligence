# src/delivery/config.py
from typing import List, Optional, Dict, Any

# --- DASHBOARD SETTINGS ---
# The link for the "Open Full Dashboard" button
# DEMO MODE: Points to the Observable Framework web portal
DASHBOARD_URL: str = "https://rchejfec.github.io/passive-policy-intelligence/"

# --- SCOPE SETTINGS ---
# Filter articles by specific anchors (Exact Name Match)
# Example: ["AI Regulation", "Canada-US Relations"]
ALLOWED_ANCHORS: Optional[List[str]] = None

# Filter articles by Anchor Type (Prefix Match)
# Example: ["DEMO"] for G7 GovAI Challenge demo semantic anchors
# Example: ["PROG"] will only include articles linked to a Program.
# Example: ["PROG", "PROJECT"] excludes general "TAG" matches.
# Set to None to allow ALL types.
ALLOWED_ANCHOR_TYPES: Optional[List[str]] = ["DEMO"]  # <--- DEMO MODE: Using DEMO semantic anchors

# --- SECTION MAPPING & STYLING ---
# Define the Category mapping AND the visual style for each section headers
# Colors: "Attention" (Red), "Good" (Green), "Warning" (Yellow), "Accent" (Blue), "Default" (Black)
SECTIONS: Dict[str, Dict[str, Any]] = {
    "🚨 Priority Highlights": {
        "categories": [], # Special case: Uses is_org_highlight flag
        "color": "Default" 
    },
    "🧠 Think Tanks & Research": {
        "categories": ["Think Tank", "Research Institute", "Academic", "AI Research", "Non-Profit"],
        "color": "Default"
    },
    "🏛️ Governments": {
        "categories": ["Government"],
        "color": "Default"
    },
    "🗞️ Media & Industry": {
        "categories": ["News & Media", "Publication", "Business Council", "Advocacy", "Podcast", "Blog"],
        "color": "Default"
    }
}

# --- THRESHOLDS & LIMITS ---
MIN_SCORE: float = 0.40
ITEMS_PER_SECTION: int = 2
LOOKBACK_HOURS: int = 60
