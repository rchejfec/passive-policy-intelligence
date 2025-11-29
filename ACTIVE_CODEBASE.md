# Active Codebase Reference

**Last Updated:** 2025-10-12

This document maps the **currently active, production-ready code** in the AI Daily Digest pipeline. Use this as your reference for understanding what's actually being used vs. what's archived/legacy.

---

## Daily Production Pipeline

### Main Orchestrator
**`test_orchestrator.py`** - Runs the complete daily pipeline

**Pipeline Stages:**
```
1. RSS Fetcher      → src/ingestion/rss_fetcher.py
2. Article Indexer  → src/ingestion/index_articles.py
3. Article Analyzer → src/analysis/analyze_articles.py
4. Article Enricher → src/analysis/enrich_articles.py
5. Data Export      → scripts/export_to_parquet.py
6. Teams Delivery   → src/delivery/engine.py
```

**How to Run:**
```bash
python test_orchestrator.py
```

---

## Active Source Modules

### 📥 Ingestion (`src/ingestion/`)

#### Daily Pipeline Modules
- **`rss_fetcher.py`** ✅ ACTIVE
  - Fetches articles from RSS feeds
  - Checks for duplicates via database
  - Handles multiple feed URLs per source
  - Called by: `test_orchestrator.py`

- **`index_articles.py`** ✅ ACTIVE
  - Indexes new articles into ChromaDB
  - Creates vector embeddings (all-MiniLM-L6-v2)
  - Chunks text (350 words, 50 word overlap)
  - Marks articles as `indexed_at`
  - Called by: `test_orchestrator.py`

#### Knowledge Base Management (Manual Use)
- **`index_knowledge_base.py`** ✅ ACTIVE (Manual)
  - Indexes knowledge base items into ChromaDB
  - Used for semantic anchor components
  - Commented out in orchestrator (run when KB changes)
  - Can be uncommented in `test_orchestrator.py` when needed

- **`build_knowledge_base.py`** ✅ ACTIVE (Manual)
  - Builds knowledge_base.csv from RSS feeds
  - Gathers research articles and program documents
  - Run manually when adding new KB sources

- **`add_charters_to_kb.py`** ✅ ACTIVE (Manual)
  - Adds program charters to knowledge_base.csv
  - Scans `user_content/program_project_charters/`
  - **TODO:** Consider adding to `manage.py` CLI

---

### 🔍 Analysis (`src/analysis/`)

- **`analyze_articles.py`** ✅ ACTIVE
  - Calculates similarity between articles and semantic anchors
  - Loads all active anchors and their embeddings
  - Uses Champion V4 algorithm with filtered categories
  - Applies minimum similarity threshold (0.25) for News Media/Misc Research
  - Marks articles as `analyzed_at`
  - Called by: `test_orchestrator.py`

- **`enrich_articles.py`** ✅ ACTIVE
  - Applies tier-based enrichment logic
  - Writes highlight flags directly to PostgreSQL
  - Calculates `is_anchor_highlight` and `is_org_highlight`
  - Uses historical threshold map for dynamic filtering
  - Marks articles as `enrichment_processed_at`
  - Called by: `test_orchestrator.py`

**Enrichment Tiers:**
```
Tier 1 (Premium): Think Tank, AI Research, Research Institute, Non-Profit,
                  Academic, Advocacy, Publication, Business Council
                  → Fixed threshold (0.20)

Tier 2 (Government): Government sources
                     → Dynamic threshold (historical mean per anchor)

Tier 3 (News Media): News Media sources
                     → Strict threshold (historical mean + std dev per anchor)
```

---

### 📤 Data Export (`scripts/`)

- **`export_to_parquet.py`** ✅ ACTIVE
  - Exports optimized Parquet files from PostgreSQL for the Web Portal.
  - Generates 4 files:
    - `morning_paper.parquet` (Last 7 days)
    - `archive.parquet` (All articles)
    - `sources.parquet` (Active sources)
    - `anchors.parquet` (Active anchors)
  - Uses a denormalized schema for fast, client-side querying.
  - Called by: `test_orchestrator.py`

---

### 🌐 Think Tank Intelligence Portal (`portal/`)

- **`portal/src/`** ✅ ACTIVE
  - Source code for the static web portal.
  - Built with **Observable Framework**.
  - **`index.md`**: The "Morning Paper" dashboard (7-day digest).
  - **`archive.md`**: Full archive search with advanced filters.
  - Uses **DuckDB-WASM** to query Parquet files directly in the browser.

- **`portal/src/data/`** ✅ ACTIVE
  - Destination for generated Parquet files.
  - These files are read by the Observable Framework during build or runtime.

**How to Run (Local):**
```bash
cd portal
npm install
npm start
```

---

### 📦 Delivery (`src/delivery/`)

- **`engine.py`** ✅ ACTIVE
  - Core logic for the "Morning Paper" Teams digest.
  - Selects top articles per category based on priority and similarity.
  - Generates Adaptive Cards for Microsoft Teams.
  - Called by: `test_orchestrator.py` (or standalone test)

- **`renderer.py`** ✅ ACTIVE
  - Handles the JSON construction for Adaptive Cards.
  - Defines the visual layout (headers, accordions, buttons).

- **`config.py`** ✅ ACTIVE
  - Configuration settings for the delivery module (e.g., dashboard URLs, section definitions).

---

### 🛠️ Management (`src/management/`)

#### Core Utilities
- **`db_utils.py`** ✅ ACTIVE
  - PostgreSQL connection management
  - Reads `DATABASE_URL` from `.env`
  - Helper functions: `get_db_connection()`, `slugify()`, `get_all_component_types()`
  - Used by: ALL modules

#### CLI Management Tools (via `manage.py`)
- **`subscriber_manager.py`** ✅ ACTIVE
  - List, add, import, delete subscribers
  - Manage subscriptions to semantic anchors
  - CSV import functionality

- **`anchor_manager.py`** ✅ ACTIVE
  - List, create, import, delete semantic anchors
  - Interactive wizard for anchor creation
  - Template generation for bulk imports
  - Manages anchor components (tags, KB items, programs)

- **`system_manager.py`** ✅ ACTIVE
  - System-level maintenance tasks
  - Reset analysis data
  - Reset enrichment timestamps
  - Reset anchor/subscriber data
  - **DANGER:** Destructive operations with confirmation

- **`testing_manager.py`** ✅ ACTIVE
  - Generate test data files
  - Create sample anchors and subscribers
  - Useful for development/testing

---

### 🔬 Evaluation (`src/evaluation/`) ❌ ARCHIVED

**Status:** All files moved to `archive/experimental/`

These were research scripts used during development. Insights from these experiments are now implemented in the production code.

---

## Management CLI Tool

### Main CLI
**`manage.py`** - Master CLI for system administration

**Command Structure:**
```bash
python manage.py <command> <subcommand> [options]
```

### Available Commands

#### Subscriber Management
```bash
python manage.py subscribers list
python manage.py subscribers add --email "user@example.com" --name "Name"
python manage.py subscribers import --file "path/to/subscribers.csv"
python manage.py subscribers delete  # Interactive wizard
```

#### Anchor Management
```bash
python manage.py anchors list
python manage.py anchors create  # Interactive wizard
python manage.py anchors template  # Generate CSV template
python manage.py anchors import --file "path/to/anchors.csv"
python manage.py anchors delete  # Interactive wizard
```

#### System Maintenance
```bash
python manage.py system reset-analysis  # Reset all analysis timestamps
python manage.py system reset-enrichment [--limit N] [--offset N]
python manage.py system reset-anchors  # Delete all anchors
python manage.py system reset-subscribers  # Delete all subscribers
```

#### Testing Utilities
```bash
python manage.py testing generate-anchors [--output path]
python manage.py testing generate-subscribers [--output path]
```

---

## Database Schema

### Core Tables (Active)
- **`sources`** - RSS feed sources and metadata
- **`articles`** - Ingested articles with pipeline timestamps
- **`knowledge_base`** - Semantic anchor component items
- **`tags`** - Tag definitions with embeddings
- **`semantic_anchors`** - User-defined topics of interest
- **`anchor_components`** - Components that make up each anchor
- **`article_anchor_links`** - Similarity scores between articles and anchors
- **`subscribers`** - Email distribution list
- **`subscriptions`** - Subscriber-to-anchor relationships

### Key Pipeline Timestamps
Articles flow through the pipeline via these timestamp fields:
```
created_at              → Article ingested
indexed_at              → Embedded in ChromaDB
analyzed_at             → Linked to semantic anchors
enrichment_processed_at → Highlight flags calculated
```

---

## External Dependencies

### Vector Database
- **ChromaDB** (Persistent)
  - Location: `data/chroma_db/`
  - Collection: `irpp_research`
  - Embedding Model: `all-MiniLM-L6-v2`

### Configuration
- **`.env`** file (required)
  - `DATABASE_URL` - PostgreSQL connection string

### Python Packages
See [requirements.txt](requirements.txt) for full list

---

## Legacy Code (ARCHIVED)

### What's Been Archived
All legacy code has been moved to the `archive/` directory:

- **SQLite implementations** (`*_sq.py` files)
- **JSON packaging layer** (web delivery)
- **Experimental evaluation scripts**
- **Old Notebooks** (`archive/notebooks/`)

### Why Files Were Archived
1. ✅ Not imported by any active code
2. ✅ Replaced by PostgreSQL versions
3. ✅ No longer part of production pipeline
4. ✅ Kept for historical reference only

**See:** [archive/README.md](archive/README.md) for details

---

## Development Workflow

### Running the Daily Pipeline
1. Ensure PostgreSQL is accessible (check `.env`)
2. Ensure ChromaDB data exists (`data/chroma_db/`)
3. Run: `python test_orchestrator.py`

### Adding New Semantic Anchors
1. Run: `python manage.py anchors create`
2. Follow the interactive wizard
3. Anchors become active immediately

### Updating Knowledge Base
1. Edit `user_content/knowledge_base.csv` (or use `build_knowledge_base.py`)
2. Uncomment KB indexer in `test_orchestrator.py`
3. Run the pipeline once
4. Comment it back out

### Managing Subscribers
1. Use `python manage.py subscribers add` or `import`
2. Subscribers will receive digests based on their subscriptions

---

## Questions?

- **Is this file active?** → Check if it's listed in this document
- **Where's the code?** → Search for the file in `src/` or check `archive/`
- **How do I run it?** → See the command examples above
- **What calls this module?** → Check the "Called by:" annotations

---

*This document reflects the codebase as of 2025-10-12*
*For historical context, see: [archive/README.md](archive/README.md)*
