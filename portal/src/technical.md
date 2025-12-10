---
theme: dashboard
title: Technical Documentation
toc: false
---

<link rel="stylesheet" href="theme.css">

# Technical Documentation

<div class="card" style="background: #f0f7ff; border-left: 4px solid #0066cc;">
  This page provides technical implementation details for developers, system administrators, and those interested in the architecture of the Passive Policy Intelligence system.
</div>

## Design Principles

### Local-First Architecture (Data Sovereignty)
The core pipeline runs entirely on user infrastructure using open-source embedding models (sentence-transformers). No external API calls for ranking. No data exfiltration. Content processing stays within the security perimeter -- suitable for on-premises or private cloud deployment.

Storage requirements are minimal: only headlines, links, and occasional summaries are retained. Compute costs are low enough to run on a standard VM (~$10-20/month).

### Explainable Rankings (Not Black Box AI)
This system does not generate text or make autonomous decisions. It ranks existing content using vector similarity scores (0-1 scale). Every score ties back to a specific semantic anchor. No hallucinations. No hidden logic.

LLM usage is optional and limited to creating semantic anchors during setup (via DSPy framework). The framework abstracts the model layer, allowing users to swap public APIs (OpenAI, Anthropic) for private or local models based on security requirements.

### Modular & Interoperable
Components are decoupled:
- **Ingestion Layer**: Swap RSS for web scraping or JSON feeds
- **Embedding Models**: Swap sentence-transformers for domain-specific models
- **Delivery Channels**: Currently Microsoft integration and a web portal, extensible to email, Slack, etc.
- **Database**: Standard PostgreSQL (government-compatible infrastructure)

The web portal is built with Observable Framework—a static site generator requiring no backend servers.

## Technical Pipeline

```
RSS Feeds → Ingestion → Vector Embeddings → Semantic Matching → Tiered Filtering → Delivery
    ↓           ↓              ↓                    ↓                  ↓              ↓
  50+       PostgreSQL    ChromaDB +         Cosine Similarity    Source-Aware     Teams +
 Sources      Database    SentenceXfmrs     vs. Anchors (0-1)     Thresholds      Portal
```

### Component Details

**Ingestion Layer**
- RSS feed parsing using Python's feedparser library
- Google Alerts integration for custom search queries
- PostgreSQL database for article metadata storage
- Scheduled daily updates via cron jobs

**Embedding Layer**
- Sentence-transformers for text vectorization (all-MiniLM-L6-v2 model)
- ChromaDB for vector storage and similarity search
- Local model execution - no API calls required
- Average processing time: ~0.1 seconds per article

**Ranking Layer**
- Cosine similarity calculation between article and anchor embeddings
- Score normalization to 0-1 scale
- Source-aware threshold application
- Historical statistics tracking for dynamic thresholds

**Delivery Layer**
- Microsoft Teams webhook integration
- Email delivery via SMTP
- Observable Framework static site generation
- Power BI integration via PostgreSQL connector

## Semantic Anchors (The Ranking Lens)

Users define policy topics using **Hypothetical Document Embeddings (HyDE)**:

Instead of matching against keyword lists or example documents, the system uses a *hypothetical policy brief* that exemplifies the topic. This brief is generated (via DSPy) from:
- Representative documents (URLs or PDFs)
- Tag combinations (keywords)

The hypothetical document is written to include language semantically similar to target content, improving matching accuracy over simple keyword or phrase-based systems.

**Example**: Instead of searching for "AI governance" or looking for semantic linkages against 10 policy papers, you generate a hypothetical brief that discusses AI governance in the style of your target sources.

The system converts these anchors into vector embeddings and calculates semantic similarity with incoming articles.

### Creating Semantic Anchors

Two methods are available:

1. **Document-Based**: Provide URLs or PDFs of representative policy documents. The system extracts key themes and generates a hypothetical brief.

2. **Tag-Based**: Provide keyword combinations. The system uses DSPy to generate a comprehensive hypothetical brief that incorporates these concepts.

Both methods produce a 500-1000 word hypothetical document that serves as the semantic reference point for ranking incoming content.

## Source-Aware Filtering Logic

Not all sources publish at the same volume or relevance. The system applies **tiered thresholds** to prevent high-volume sources from drowning out authoritative research:

### Tier 1: Low-Volume, High-Relevance Sources
- **Examples**: Think tanks, academic research, industry reports
- **Threshold**: Fixed score > 0.20
- **Rationale**: These sources publish sporadically but are highly targeted to policy topics
- **Typical volume**: 1-5 articles per week per source

### Tier 2: Medium-Volume Sources
- **Examples**: Government press releases, specialized news sites
- **Threshold**: Score > Historical Mean for that source
- **Rationale**: Frequent publishers with generally relevant content
- **Typical volume**: 5-20 articles per week per source

### Tier 3: High-Volume, Broad Sources
- **Examples**: Major news media outlets
- **Threshold**: Score > Mean + 1 Standard Deviation
- **Rationale**: Extremely high-volume sources need strong semantic matches to avoid overwhelming the digest
- **Typical volume**: 50+ articles per day per source

### Why This Matters

A think tank report with a 0.25 similarity score surfaces in the digest. A news article needs a 0.40+ score to compete. This ensures relevant research doesn't get buried by daily news cycles.

The threshold calculation happens daily based on rolling 30-day statistics, allowing the system to adapt to changing source patterns.

## Deployment Options

### Infrastructure Requirements

**Minimum Specifications**:
- 2 CPU cores
- 4GB RAM
- 20GB storage
- Linux/Windows server
- Python 3.8+ runtime

**Network Requirements**:
- Outbound HTTPS for RSS feeds
- SMTP access for email delivery (optional)
- Webhook access for Teams/Slack (optional)

### Deployment Models

**On-Premises Deployment**
- Suitable for Protected B data
- Runs on departmental servers
- No external API dependencies
- Air-gap compatible with manual source updates

**Private Cloud Deployment**
- Azure/AWS VM deployment
- Data residency controls
- Automated scaling options
- Integration with cloud-native services

**Hybrid Deployment**
- Analysis pipeline on-premises
- Portal hosted publicly (metadata only)
- API gateway for secure data exposure
- Best for public-facing demos with sensitive source data

### Security Considerations

- All processing happens within your security perimeter
- No data transmitted to third-party APIs for ranking
- Optional encryption at rest for PostgreSQL
- Role-based access control for portal views
- Audit logging for all system operations

## Model Architecture & Abstraction

### Embedding Models

The system uses sentence-transformers by default but supports custom models:

**Default Model**: all-MiniLM-L6-v2
- 22M parameters
- 384-dimensional embeddings
- Fast inference (~0.1s per document)
- Multilingual support

**Alternative Models**:
- all-mpnet-base-v2 (better accuracy, slower)
- Domain-specific models (legal, medical, etc.)
- Custom fine-tuned models

**Swapping Models**: Update the model configuration in `config.yaml`:
```yaml
embedding_model: "sentence-transformers/all-MiniLM-L6-v2"
```

### LLM Integration (Optional)

DSPy framework provides LLM abstraction for semantic anchor generation:

**Supported Providers**:
- OpenAI (GPT-4, GPT-3.5)
- Anthropic (Claude)
- Local models (Llama, Mistral via Ollama)
- Azure OpenAI

**Configuration Example**:
```python
import dspy
dspy.settings.configure(
    lm=dspy.OpenAI(model="gpt-4"),
    # or
    lm=dspy.OllamaLocal(model="llama2")
)
```

LLM usage is limited to one-time anchor creation. No LLM calls during daily ranking operations.

## Data Schema

### Articles Table (PostgreSQL)

```sql
CREATE TABLE articles (
    article_id UUID PRIMARY KEY,
    title TEXT NOT NULL,
    link TEXT UNIQUE NOT NULL,
    source_name TEXT NOT NULL,
    source_category TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL,
    ingested_at TIMESTAMP DEFAULT NOW()
);
```

### Semantic Matches Table

```sql
CREATE TABLE semantic_matches (
    match_id UUID PRIMARY KEY,
    article_id UUID REFERENCES articles(article_id),
    anchor_name TEXT NOT NULL,
    similarity_score FLOAT NOT NULL,
    normalized_score FLOAT NOT NULL,
    is_org_highlight BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Source Configuration Table

```sql
CREATE TABLE sources (
    source_id UUID PRIMARY KEY,
    source_name TEXT UNIQUE NOT NULL,
    source_url TEXT NOT NULL,
    source_category TEXT NOT NULL,
    tier INTEGER NOT NULL CHECK (tier IN (1, 2, 3)),
    is_active BOOLEAN DEFAULT TRUE
);
```

## Performance Characteristics

### Processing Metrics (Based on Demo Usage)

- **Daily article ingestion**: 200-500 articles
- **Processing time per article**: ~0.15 seconds
- **Total daily processing time**: 1-2 minutes
- **Database size growth**: ~5MB per month
- **Vector database size**: ~50MB for 10,000 articles

### Scalability

The system scales linearly with source count:
- 50 sources: 200-500 articles/day
- 100 sources: 400-1000 articles/day
- 500 sources: 2000-5000 articles/day (requires 8GB RAM)

ChromaDB handles millions of vectors efficiently. PostgreSQL can be sharded for extremely large deployments.

## Integration Options

### Microsoft Teams Integration

Webhook-based delivery:
```python
import requests
webhook_url = "https://outlook.office.com/webhook/..."
payload = {
    "text": "Daily Policy Digest",
    "sections": [...]
}
requests.post(webhook_url, json=payload)
```

### Email Integration

SMTP delivery with HTML formatting:
```python
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

msg = MIMEMultipart('alternative')
msg['Subject'] = "Daily Policy Digest"
html_content = render_digest_template(articles)
msg.attach(MIMEText(html_content, 'html'))
```

### Power BI Integration

Direct PostgreSQL connection via native connector. No custom API required.

### Custom API Integration

The system exposes a simple REST API for custom integrations:
```
GET /api/articles?anchor={anchor_name}&days={n}
GET /api/anchors
GET /api/sources
```

## Maintenance & Operations

### Routine Tasks

**Daily** (Automated):
- RSS feed ingestion
- Embedding generation
- Similarity scoring
- Threshold calculation
- Delivery notifications

**Weekly** (Manual):
- Review source health
- Check for feed failures
- Validate delivery success

**Monthly** (Manual):
- Update semantic anchors if needed
- Review and adjust tier thresholds
- Archive old data (optional)

### Monitoring

Key metrics to track:
- Articles ingested per day
- Processing time trends
- Source failure rates
- Similarity score distributions
- User engagement (portal analytics)

### Backup & Recovery

**Database Backup**:
```bash
pg_dump ppi_database > backup_$(date +%Y%m%d).sql
```

**Vector Database Backup**:
ChromaDB persists to disk automatically. Copy the data directory for backups.

**Configuration Backup**:
Version control all YAML configuration files and anchor definitions.

## Open Source Components

All core dependencies are open source:

- **Python 3.8+**: Runtime environment
- **PostgreSQL 13+**: Relational database
- **ChromaDB**: Vector database
- **sentence-transformers**: Embedding models
- **feedparser**: RSS parsing
- **Observable Framework**: Portal generation
- **DSPy**: LLM abstraction (optional)

No proprietary software required. No vendor lock-in.

## Repository & Documentation

**GitHub Repository**: [https://github.com/rchejfec/passive-policy-intelligence](https://github.com/rchejfec/passive-policy-intelligence)

**Installation Guide**: See `README.md` in repository
**Configuration Guide**: See `docs/configuration.md`
**API Documentation**: See `docs/api.md`

---

## Related Pages

<div class="grid grid-cols-3" style="gap: 1rem; margin-top: 1rem;">
  <div class="card" style="text-align: center;">
    <h3>📋 Demo Overview</h3>
    <p>Non-technical overview of the system and why it matters</p>
    <a href="./demo" style="text-decoration: none;">
      <div style="background: #0066cc; color: white; padding: 0.5rem; margin-top: 0.5rem; font-weight: bold;">
        VIEW OVERVIEW →
      </div>
    </a>
  </div>

  <div class="card" style="text-align: center;">
    <h3>📊 Daily Review</h3>
    <p>See the system in action with live data</p>
    <a href="./index" style="text-decoration: none;">
      <div style="background: #0066cc; color: white; padding: 0.5rem; margin-top: 0.5rem; font-weight: bold;">
        VIEW DIGEST →
      </div>
    </a>
  </div>

  <div class="card" style="text-align: center;">
    <h3>🔍 Sources</h3>
    <p>Complete list of monitored sources and semantic anchors</p>
    <a href="./sources" style="text-decoration: none;">
      <div style="background: #0066cc; color: white; padding: 0.5rem; margin-top: 0.5rem; font-weight: bold;">
        VIEW SOURCES →
      </div>
    </a>
  </div>
</div>

---

<div class="card" style="background: #fff3cd; border-left: 4px solid #856404; margin-top: 2rem;">
  <strong>📅 G7 GovAI Grand Challenge Demo</strong><br/>
  Passive Policy Intelligence | Built with Observable Framework
</div>
