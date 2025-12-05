# Contributing to Passive Policy Intelligence

Thank you for your interest in contributing to this project.

## Development Setup

### Prerequisites

- Python 3.10+
- PostgreSQL 14+ (or compatible database)
- [UV](https://docs.astral.sh/uv/) package manager

### Installation

```bash
git clone https://github.com/rchejfec/passive-policy-intelligence.git
cd passive-policy-intelligence

# Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh  # macOS/Linux
# or: powershell -c "irm https://astral.sh/uv/install.ps1 | iex"  # Windows

# Install dependencies
uv sync
source .venv/bin/activate  # macOS/Linux
# or: .venv\Scripts\activate  # Windows

# Configure database
cp .env.example .env
# Edit .env with your database credentials

# Initialize database
python scripts/setup/setup_database.py
```

## Project Structure

```
.
├── src/
│   ├── ingestion/     # RSS fetching and article indexing
│   ├── analysis/      # Vector similarity and enrichment
│   ├── delivery/      # Teams digest and portal export
│   └── management/    # CLI tools and database utilities
├── scripts/           # Utility scripts for setup and maintenance
├── portal/            # Observable Framework web portal
└── test_orchestrator.py  # Main pipeline orchestrator
```

## Running the Pipeline

### Full Pipeline

```bash
python test_orchestrator.py
```

This executes all stages: ingestion → indexing → analysis → enrichment → delivery.

### Individual Components

For development, you can test individual modules:

```bash
python -m src.ingestion.rss_fetcher
python -m src.analysis.analyze_articles
```

### Management CLI

The `manage.py` script provides tools for managing the system:

```bash
python manage.py anchors list       # View semantic anchors
python manage.py anchors create     # Add a new anchor interactively
python manage.py sources list       # View configured RSS sources (not yet implemented in manage.py)
```

## Code Style

This project uses:
- **Black** for code formatting (line length: 100)
- **Ruff** for linting
- **Type hints** where appropriate

Run formatting:
```bash
uv run black src/
uv run ruff check src/
```

## Adding Dependencies

```bash
uv add <package-name>
```

This updates `pyproject.toml` and `uv.lock`.

## Testing

The project currently uses manual testing via the orchestrator. Unit tests can be added in `tests/`:

```bash
uv run pytest tests/
```

## Architecture Overview

### Pipeline Flow

1. **RSS Fetcher** - Pulls articles from configured sources
2. **Article Indexer** - Creates vector embeddings (sentence-transformers)
3. **Article Analyzer** - Calculates similarity to semantic anchors
4. **Article Enricher** - Applies source-aware thresholds
5. **Data Export** - Generates parquet files for the portal
6. **Delivery Engine** - Sends Teams digest notifications

### Key Technologies

- **ChromaDB** - Local vector database for embeddings
- **sentence-transformers** - Embedding model (all-MiniLM-L6-v2)
- **PostgreSQL** - Relational data storage
- **Observable Framework** - Web portal
- **DSPy** - HyDE anchor generation

### Extending the System

**Adding a new data source:**
1. Create a new fetcher in `src/ingestion/`
2. Follow the pattern in `rss_fetcher.py`
3. Add to `test_orchestrator.py`

**Adding a delivery channel:**
1. Create a new module in `src/delivery/`
2. Implement the delivery logic (see `engine.py` for Teams example)
3. Configure in `.env` and call from orchestrator

**Swapping the embedding model:**
1. Edit `src/analysis/analyze_articles.py`
2. Change the model name in sentence-transformers initialization
3. Re-index articles to update embeddings

## Pull Request Guidelines

- Keep changes focused and atomic
- Include tests for new functionality
- Update documentation as needed
- Follow existing code style
- Provide clear commit messages

## Questions or Issues?

- Check [README.md](README.md) for setup instructions
- Review [docs/](docs/) for technical details
- Open an issue on GitHub for bugs or feature requests

## License

By contributing, you agree that your contributions will be licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0).
