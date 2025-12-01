---
theme: dashboard
title: Demo Overview
toc: false
---

<link rel="stylesheet" href="theme.css">

# Passive Policy Intelligence (PPI)

<div class="card" style="background: #f0f7ff; border-left: 4px solid #0066cc;">
  <strong>G7 GovAI Grand Challenge Submission</strong> | 
  <a href="https://github.com/rchejfec/passive-policy-intelligence" target="_blank">GitHub Repo</a><br/>
  
  This project addresses <a href="https://impact.canada.ca/en/challenges/g7-govAI" target="_blank">Problem Statement 1: Information Management</a> by automating the daily search, ranking, and archiving of policy-relevant content.
  <br/><br/>
  <span style="font-size: 0.9em; color: #444;">
    By <strong>Ricardo Chejfec</strong>
  </span>
</div>

## The Problem

Policy analysts manually track dozens of sources (government portals, think tanks, research institutions, media outlets) to stay current on their mandates. This creates two problems:

1. **Time waste**: Hours spent searching for updates that may not exist
2. **Missed signals**: Critical information buried in high-volume feeds


## The Solution

An automated **passive listener** that ingests, ranks, and archives policy intelligence without manual searching. The system:

1. **Ingests** articles daily from user-defined RSS feeds and Google Alerts
2. **Ranks** content by semantic similarity to user-defined policy topics ("semantic anchors")
3. **Filters** using source-aware thresholds to surface relevant over noise
4. **Delivers** daily updates (Microsoft Teams, Email) and searchable archive (this demo, Microsft Power BI).  

**This demo** has monitored 50+ sources daily for the past month, ranking content against four hypothetical policy topics. See the [sources page](./sources) for the full list.

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


## How It Works

### Technical Pipeline

```
RSS Feeds → Ingestion → Vector Embeddings → Semantic Matching → Tiered Filtering → Delivery
    ↓           ↓              ↓                    ↓                  ↓              ↓
  50+       PostgreSQL    ChromaDB +         Cosine Similarity    Source-Aware     Teams +
 Sources      Database    SentenceXfmrs     vs. Anchors (0-1)     Thresholds      Portal
```

### Semantic Anchors (The Ranking Lens)

Users define policy topics using **Hypothetical Document Embeddings (HyDE)**:

Instead of matching against keyword lists or example documents, the system uses a *hypothetical policy brief* that exemplifies the topic. This brief is generated (via DSPy) from:
- Representative documents (URLs or PDFs)
- Tag combinations (keywords)

The hypothetical document is written to include language semantically similar to target content, improving matching accuracy over simple keyword or phrase-based systems.

**Example**: Instead of searching for "AI governance" or looking for semantic linkages against 10 policy papers, you generate a hypothetical brief that discusses AI governance in the style of your target sources.

The system converts these anchors into vector embeddings and calculates semantic similarity with incoming articles.

### Source-Aware Filtering Logic

Not all sources publish at the same volume or relevance. The system applies **tiered thresholds** to prevent high-volume sources from drowning out authoritative research:

- **Tier 1 (Low-volume, high-relevance sources)**
  - In this demo: Think tanks, academic research, industry reports
  - Fixed threshold: Score > 0.20
  - *Rationale*: These sources publish sporadically but are highly targeted to policy topics

- **Tier 2 (Medium-volume sources)**
  - In this demo: Government press releases
  - Relative threshold: Score > Historical Mean
  - *Rationale*: Frequent publishers with generally relevant content

- **Tier 3 (High-volume, broad sources)**
  - In this demo: News media
  - Strict threshold: Score > Mean + 1 Standard Deviation
  - *Rationale*: Extremely high-volume sources need strong semantic matches to avoid overwhelming the digest

**Why this matters**: A think tank report with a 0.25 similarity score surfaces in the digest. A news article needs a 0.40+ score to compete. This ensures relevant research doesn't get buried by daily news cycles.

## Interoperability & Deployment

### Deployment Options

The system runs on user infrastructure (local server or private cloud VM):
- **On-Premises**: Departmental servers for Protected B data
- **Private Cloud**: Azure/AWS VMs with data residency controls
- **Hybrid**: Analysis on-prem, portal hosted publicly (only metadata exposed)

### Model Abstraction

DSPy framework allows swapping between AI providers:
- Public APIs (OpenAI, Anthropic) for development
- Local LLMs (Llama, Mistral) for production
- Embedding models can be replaced with domain-specific alternatives

## Why This Matters for Policy Work

### Transparency & Human Control

- **User-Defined Inputs**: Full control over monitored sources and policy topics
- **Traceable Scores**: Every ranking links to a specific semantic anchor and similarity score
- **No Hidden Decisions**: System ranks content, humans decide what to read
- **Safety Net**: Lower-ranked items remain accessible in archive for manual review

### Cost-Effective & Scalable

- **Minimal Infrastructure**: Runs on low-cost VM (~$10-20/month)
- **Open Source Stack**: No vendor lock-in (PostgreSQL, ChromaDB, Python, Observable)
- **Domain Agnostic**: Works for any policy area (health, finance, environment, etc.)
- **Replicable**: Teams can deploy isolated instances without shared platform overhead

### Evidence-Based Research

- **Searchable Archive**: Track how issues evolved over time
- **Source Diversity**: Monitor across academia, government, media
- **Retrospective Queries**: Search historical matches for policy briefs
- **Bias Transparency**: Source metadata enables algorithmic prioritization of authoritative evidence

---

## Explore the Portal

<div class="grid grid-cols-3" style="gap: 1rem; margin-top: 1rem;">
  <div class="card" style="text-align: center;">
    <h3>📊 Daily Review</h3>
    <p>Recent 7-day digest showing top-ranked articles across all semantic anchors</p>
    <a href="./index" style="text-decoration: none;">
      <div style="background: #0066cc; color: white; padding: 0.5rem; margin-top: 0.5rem; font-weight: bold;">
        VIEW DIGEST →
      </div>
    </a>
  </div>

  <div class="card" style="text-align: center;">
    <h3>🔍 Archive</h3>
    <p>Full search with advanced filters (date, score, source, anchor)</p>
    <a href="./archive" style="text-decoration: none;">
      <div style="background: #0066cc; color: white; padding: 0.5rem; margin-top: 0.5rem; font-weight: bold;">
        SEARCH ARCHIVE →
      </div>
    </a>
  </div>

  <div class="card" style="text-align: center;">
    <h3>🔍 Sources</h3>
    <p>Complete list of monitored websites and semantic anchors</p>
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
