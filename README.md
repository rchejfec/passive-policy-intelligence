# Passive Policy Intelligence (PPI)

An automated environmental scanning pipeline for policy intelligence.

> This project is a submission to Canada's [G7 GovAI Grand Challenge](https://www.canada.ca/en/government/system/digital-government/digital-government-innovations/responsible-use-ai/ai-grand-challenge.html) (Problem Statement 1: Information Management).
>
> **Live Demo**: [view the web portal](https://rchejfec.github.io/passive-policy-intelligence/)

## Overview

PPI automates the discovery, ranking, and delivery of relevant content from diverse sources. The system:

- **Ingests** articles from RSS feeds of government publications, media and research outlets
- **Ranks** content using semantic similarity to user-defined topics
- **Delivers** insights through configurable channels (web portal, Teams, email)

## Key feature: Semantic Anchors with HyDE

Traditional content filtering relies on keyword matching or manual curation. This system uses **Semantic Anchors** -- policy topics defined through Hypothetical Document Embeddings (HyDE):

1. User provides representative documents or phrases for a topic (e.g., "AI governance")
2. System generates a hypothetical policy brief that exemplifies the topic
3. Incoming articles are scored against this embedding using local sentence-transformers
4. Results are filtered using source-aware thresholds to balance signal and noise

This approach improves precision without requiring large training datasets or external AI APIs.

## Architecture

The system is built as a modular pipeline suitable for self-hosted deployment:

```mermaid
graph LR
    A[Ingestion] -->|RSS/Feeds| B[Vector Analysis]
    B -->|Similarity Scores| C[Enrichment]
    C -->|Ranked Items| D[Delivery]
    D -->|Portal/Teams| E[User]
    C -->|Archive| F[PostgreSQL]
```

### Components

**Ingestion Layer** ([src/ingestion](src/ingestion))
- RSS feed monitoring with deduplication
- Extensible to other data sources (APIs, web scraping)

**Analysis Layer** ([src/analysis](src/analysis))
- Local embedding generation (sentence-transformers)
- Semantic similarity calculation against anchors
- Source-aware filtering (tiered thresholds by source type)

**Delivery Layer** ([src/delivery](src/delivery))
- Web portal (Observable Framework + DuckDB-WASM)
- Microsoft Teams integration (Adaptive Cards)
- Extensible to Slack, email, or custom endpoints

**Data Storage**
- PostgreSQL for relational data and audit trail
- ChromaDB for vector embeddings

### Delivery Layer 

Teams Digest |  Power BI Archive
---------------- | -------------
![](docs/images/screenshot_teams.png) | ![](docs/images/screenshot_powerbi.png)


## Data Sovereignty

The pipeline is designed for secure, on-premises deployment:

- **No external AI APIs**: Embedding models run locally
- **No data exfiltration**: All processing occurs within your environment
- **Full audit trail**: Every article and score is logged in PostgreSQL
- **Transparent rankings**: Scores are traceable with no black-box decisions

## Getting Started

### Prerequisites

- Python 3.10+
- PostgreSQL 14+ (or any PostgreSQL-compatible database)

### Installation

**1. Clone and install dependencies**

This project uses [UV](https://docs.astral.sh/uv/) for dependency management:

```bash
git clone https://github.com/rchejfec/passive-policy-intelligence.git
cd passive-policy-intelligence

# Install UV if needed
curl -LsSf https://astral.sh/uv/install.sh | sh  # macOS/Linux
# or: powershell -c "irm https://astral.sh/uv/install.ps1 | iex"  # Windows

# Install dependencies
uv sync
source .venv/bin/activate  # macOS/Linux
# or: .venv\Scripts\activate  # Windows
```

**2. Configure database**

Copy `.env.example` to `.env` and set your PostgreSQL connection string:

```bash
cp .env.example .env
```

Edit `.env`:
```
DATABASE_URL=postgresql://user:password@localhost:5432/ppi
```

For the demo, PostgreSQL was used on Azure Database for PostgreSQL. To use a different database (e.g., SQLite for testing), you would need to modify the connection logic in `src/management/db_utils.py`.

**3. Initialize database**

```bash
python scripts/setup/setup_database.py
```

This creates the schema and seeds data sources.

### Running the Pipeline

**Execute the full pipeline:**

```bash
python test_orchestrator.py
```

This runs all stages: ingestion → indexing → analysis → enrichment → delivery.

For the demo, a wrapper script (`run_pipeline.ps1` / `run_pipeline.sh`) adds Teams notifications. You can customize this for your environment.

**Manage semantic anchors and sources:**

```bash
python manage.py anchors list       # View configured topics
python manage.py anchors create     # Add a new topic (interactive)
python manage.py sources list       # View RSS sources
```

**View results:**

The web portal source is in `portal/`. After running the pipeline, parquet files are exported to `portal/src/data/`. Build and deploy:

```bash
cd portal
npm install
npm run build
npm run deploy  # Or serve locally with: npm run dev
```

## Configuration

### Adding RSS Sources

Sources are managed in the PostgreSQL `sources` table. Use the management CLI:

```bash
python manage.py sources add --name "Example Think Tank" --url "https://example.org/feed.xml"
```

Or directly edit the database.

### Creating Semantic Anchors

Anchors can be created through:
1. **Interactive CLI**: `python manage.py anchors create`
2. **Bulk import**: `python manage.py anchors import --file anchors.csv`
3. **HyDE generation**: Use `scripts/batch_create_anchors.py` with DSPy for hypothetical document generation

For the demo, anchor generation used OpenAI's API through DSPy. To swap providers, configure DSPy to use a different LLM (Anthropic, local models, etc.) in the generation scripts.

### Delivery Channels

The delivery engine supports multiple outputs:

- **Web Portal**: Static Observable Framework site (see `portal/`)
- **Microsoft Teams**: Configure `TEAMS_WEBHOOK_URL` in `.env`
- **Email**: Extensible via SMTP (not yet implemented)

For the demo, Teams delivery was used. To add Slack, extend `src/delivery/engine.py` with a Slack webhook adapter.

## Technical Details

**Embedding Model**: `all-MiniLM-L6-v2` (384-dim, ~80MB)
- Fast inference on CPU
- Swappable via sentence-transformers API

**Source-Aware Filtering**:
- Think tanks / research: Score > 0.20 (fixed threshold)
- Government: Score > Historical Mean (dynamic)
- News media: Score > Mean + 1 Std Dev (strict)

This prevents high-volume sources from dominating results while surfacing relevant research.

**DSPy Integration**: Used for HyDE anchor generation. Supports multiple LLM backends (OpenAI, Anthropic, local models).

## Project Structure

```
.
├── src/
│   ├── ingestion/     # RSS fetching, article indexing
│   ├── analysis/      # Semantic similarity, enrichment
│   ├── delivery/      # Teams, portal export
│   └── management/    # CLI tools, database utilities
├── scripts/           # Setup, maintenance, data export
├── portal/            # Observable Framework web portal
├── docs/              # Additional documentation
└── test_orchestrator.py  # Main pipeline entrypoint
```

## Documentation

- **[docs/200_Architecture.md](docs/200_Architecture.md)** - Detailed technical architecture
- **[docs/300_Think-Tank-Portal.md](docs/300_Think-Tank-Portal.md)** - Web portal design
- **[docs/500_Database-Schema.md](docs/500_Database-Schema.md)** - Database schema reference
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Development setup and guidelines

## Deployment Considerations

The demo runs on an Azure B1s VM (1 vCPU, 1GB RAM, ~$10/month). Key considerations:

- **Scheduling**: Use cron (Linux) or Task Scheduler (Windows) to run `test_orchestrator.py` daily
- **Memory**: PyTorch and sentence-transformers require ~1.5GB during embedding generation
- **Storage**: ChromaDB grows with corpus size (~1GB per 10k articles indexed)

For production, consider:
- Separating ChromaDB to persistent storage
- Using connection pooling for PostgreSQL
- Implementing rate limiting for RSS feeds
- Adding log rotation

## License

This project is licensed under the **Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0)**. See [LICENSE](LICENSE) for details.

## Citation

If you use this work, please cite:

```
Passive Policy Intelligence: Automated Environmental Scanning for Policy Work
Developed for the G7 GovAI Grand Challenge 2025
https://github.com/rchejfec/passive-policy-intelligence
```

## Contact

For questions or collaboration inquiries related to this project, please open an issue on GitHub.

---

**Developed for the G7 GovAI Grand Challenge 2025**
