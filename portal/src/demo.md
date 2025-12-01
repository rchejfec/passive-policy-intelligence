---
theme: dashboard
title: Demo Overview
toc: false
---

<link rel="stylesheet" href="theme.css">

# Automated Environmental Scanning for Passive Policy Intelligence

<div class="card" style="background: #f0f7ff; border-left: 4px solid #0066cc;">
  <strong>The Demo Portal</strong><br/>
  This is a live demonstration of an AI-powered system that helps public servants track policy-relevant research and announcements.
</div>

#GEM //Missing explanation of the grant/application program (the more pragmatic why)
---

## What is this?

An automated pipeline that acts as a **passive listener** for policy intelligence. It tracks a list of user-defined websites, ranks content against user-defined policy topics, and delivers curated digests via the users prefer choice (Microsoft Teams, email, Power BI, this web portal).

**The Problem:** Public servants may struggle to track critical research and announcements amidst overwhelming information flows. Missing important developments poses risks, while manual searching wastes valuable time.

**The Solution:** Modern vector embedding technology provides a cost-effective, transparent alternative to expensive market intelligence tools. 

For the past month, this demo has tracked more than 50 websites from government agencies, think tanks, research institutions, and media - matched against four sample semantic anchors covering hypothetical policy mandates or interests. (Learn more)[ sources page] <#GEM>

---

## What does it do?

### Core Functions

1. **Automated Ingestion** - Fetches articles daily from a user-defined list of RSS feeds and Google Alerts
2. **Semantic Ranking** - Calculates relevance scores against a user-defined list of "semantic anchors," or policy mandates and interests
3. **Smart Highlighting** - Applies tiered thresholds based on sources <gem>
4. **Multi-Channel Delivery** - Sends digests to Microsoft Teams, stores in searchable archive

### Key Innovations: 

#### Inexpensive, lightweight, and low-risk  
<#GEM>
Performs well with small, lightweight, open-source models. Only saves headlines, links and the ocassional short summary. This means no need for external API calls and no or low computing and storage costs. 

Other than in the creation of semantic anchors, where the use of LLMs is optional, this tool doesn't actually rely on chatbots or generates text. Reducing the risk of hallucination and allowing for easier handling of sensitive information. 

#### Hypothetical Document Embeddings (HyDE) for simplified semantic matching 

Instead of matching against phrases or lists of documents relevant to a user or team, we can instead use a hypothetical document, generated specifically to include language that is semantically similar to our target information. In this demo, users setting up a new instance can leverage DSPy to generate a sample anchor summary from a list of phrases, documents, or URLs.  

#### Ranking Over Filtering

Traditional keyword systems either show everything (noise) or filter aggressively (miss edge cases). This system **ranks** all content by relevance while keeping lower-scored items accessible. Users control thresholds and can always "look beyond" top matches.

---

## How does it do it?

### Technical Architecture

```
RSS Feeds → Ingestion → Vector Embeddings → Semantic Matching → Tiered Filtering → Delivery
    ↓           ↓              ↓                    ↓                  ↓              ↓
  ~110      PostgreSQL    ChromaDB +         Cosine Similarity    Highlight      Teams +
 Sources      Database    SentenceXfmrs     vs. Anchors (0-1)     Logic         Portal
```

### Semantic Anchors (The "Lens")

Users define policy topics of interest using:
- **HyDE Methodology** - Hypothetical policy briefs that exemplify the topic
- Based on:
  - **Representative Documents** - Real-world examples of relevant content (URLs or PDFs)
  - **Tags Combinations** - Keywords and category markers

The system converts these into vector embeddings and calculates semantic similarity with incoming articles.

### Tiered Highlighting Logic

Not all sources are equal. The system applies **source-aware thresholds** to avoid drowning signal in noise:

- **Tier 1 (Low volume, highly targetted)** - Sources that publish sporadically on topics very likely to be relevant in some way. 
  - In this demo: Think Tanks, Research, Industry
  - Fixed threshold: Score > 0.20

- **Tier 2 (Medium volume and targetting)** - Sources that publish frequently on topics that are often relevant.
  - In this demo: Government Press Releases 
  - Relative threshold: Score > Historical Mean

- **Tier 3 (High volume, not targetted)** - Sources that publish very frequently on a wide range of topics.
  - In this demo: News & Media
  - Strict threshold: Score > Mean + 1 Std Dev

**Why this matters:** Most relevant sources get surfaced with lower similarity scores, while high-volume sources require stronger semantic matches. This prevents a single day's news cycle from overwhelming careful research.

---

## Data Sovereignty & Architecture

### Local-First Design

- **Core Pipeline:** Runs entirely on user infrastructure (local computer or private cloud VM)
- **No External API Calls:** Vector embedding and ranking happen locally using open-source models
- **Data Stays Put:** Sensitive documents never leave the security perimeter
- **PostgreSQL Database:** Standard government-compatible infrastructure
- **Observable Framework Portal:** Static site, no backend servers required

### Optional AI Components

For semantic anchor definition, users can optionally use AI (via DSPy framework) to synthesize representative documents. The framework **abstracts the model layer**, allowing users to:
- Swap public APIs (OpenAI, Anthropic) for private/local models
- Run entirely offline with self-hosted LLMs
- Ensure even "thinking" processes respect data boundaries

---

## Why This Matters for Policy Work

### Transparency & Human Control

✓ **User-Defined Anchors** - Policy topics are explicit, not hidden in black boxes
✓ **Traceable Rankings** - Every score ties back to a specific semantic anchor
✓ **No Hallucinations** - AI ranks existing content, doesn't generate new claims
✓ **Safety Net** - Lower-ranked items remain accessible for manual review

### Cost-Effective & Accessible

✓ **Minimal Infrastructure** - Runs on standard low-cost VM (~$10-20/month)
✓ **Open Source Stack** - PostgreSQL, ChromaDB, Python, Observable Framework
✓ **Domain Agnostic** - Works for any policy area (health, finance, environment, etc.)
✓ **Replicable** - Teams deploy isolated instances, no shared platform overhead

### Evidence-Based Policy

✓ **Searchable Archive** - Track how issues evolved over time
✓ **Source Diversity** - Monitor 110+ organizations across academia, government, media
✓ **Retrospective Analysis** - Query historical matches for policy briefs
✓ **Bias Mitigation** - Source metadata enables algorithmic prioritization of authoritative evidence

---

## Explore the Portal

<div class="grid grid-cols-3" style="gap: 1rem; margin-top: 1rem;">
  <div class="card" style="text-align: center;">
    <h3>📊 The Morning Paper</h3>
    <p>Recent 7-day digest showing top-ranked articles across all semantic anchors</p>
    <a href="./index" style="text-decoration: none;">
      <div style="background: #0066cc; color: white; padding: 0.5rem; margin-top: 0.5rem; font-weight: bold;">
        VIEW DIGEST →
      </div>
    </a>
  </div>

  <div class="card" style="text-align: center;">
    <h3>🔍 The Archive</h3>
    <p>Full repository search with advanced filters (date, score, source, anchor)</p>
    <a href="./archive" style="text-decoration: none;">
      <div style="background: #0066cc; color: white; padding: 0.5rem; margin-top: 0.5rem; font-weight: bold;">
        SEARCH ARCHIVE →
      </div>
    </a>
  </div>

  <div class="card" style="text-align: center;">
    <h3>🔍 Source Transparency</h3>
    <p>Complete list of monitored organizations and semantic anchors</p>
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
  Automated Environmental Scanning System | Built with Observable Framework
</div>
