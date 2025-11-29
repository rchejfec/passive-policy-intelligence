# src/delivery/config.py

# --- DASHBOARD SETTINGS ---
# The link for the "Open Full Dashboard" button
DASHBOARD_URL = "https://app.powerbi.com/links/iz2soIgITg?ctid=bcfac97a-4f44-44db-ab46-b8d571daddb4&pbi_source=linkShare"

# --- SCOPE SETTINGS ---
# Filter articles by specific anchors (Exact Name Match)
# Example: ["AI Regulation", "Canada-US Relations"]
ALLOWED_ANCHORS = None 

# Filter articles by Anchor Type (Prefix Match)
# Example: ["PROG"] will only include articles linked to a Program.
# Example: ["PROG", "PROJECT"] excludes general "TAG" matches.
# Set to None to allow ALL types.
ALLOWED_ANCHOR_TYPES = ["PROG"]  # <--- NEW SETTING

# --- SECTION MAPPING & STYLING ---
# Define the Category mapping AND the visual style for each section headers
# Colors: "Attention" (Red), "Good" (Green), "Warning" (Yellow), "Accent" (Blue), "Default" (Black)
SECTIONS = {
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
        "categories": ["News Media", "Publication", "Business Council", "Advocacy", "Podcast", "Blog"],
        "color": "Default"
    }
}

# --- THRESHOLDS & LIMITS ---
MIN_SCORE = 0.40
ITEMS_PER_SECTION = 2
LOOKBACK_HOURS = 60