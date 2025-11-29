# 100: Project Overview

## 1. Core Problem & Guiding Principles

This project aims to develop a personalized system to combat the significant information overload faced by public policy professionals. The goal is to create a pipeline that transforms raw data from diverse sources into filtered, actionable intelligence.

The development is guided by the following core values:

* **Personal Use & Flexibility:** Prioritizing working and useful solutions for a single user.
* **Achievable & Manageable:** The project is broken down into distinct, manageable modules.
* **Cost-Efficiency:** The design minimizes operational costs.
* **Resilience & Robustness:** The system is designed to be fault-tolerant and require minimal maintenance.

## 2. System Overview: A Production Pipeline

The system is a modular pipeline that transforms raw information into an enriched, searchable knowledge base. It consists of three primary stages that are executed in sequence.

### Stage 1: Data Ingestion

This module is responsible for collecting raw data from various online sources. It uses a hybrid strategy that combines native RSS feeds with Google Alerts to ensure comprehensive coverage. All collected articles are stored and de-duplicated in a central **Azure Database for PostgreSQL**.

### Stage 2: Vector Indexing

This is the project's intelligence layer, enabling the system to understand the meaning of text. It processes content by generating "embeddings" (numerical vector representations) using a `sentence-transformers` model and storing them in a local ChromaDB vector database. All corresponding metadata is stored in Azure PostgreSQL.

### Stage 3: Analysis & Enrichment

This stage is fully implemented and in production. It finds newly indexed articles and analyzes them against user-defined "semantic anchors." It applies relevance filtering and then enriches the data by writing intelligence—such as `is_anchor_highlight` flags—directly back to the database.

## 3. Delivery Layers

The system provides multiple ways to consume the generated intelligence, catering to different workflows:

### The "Morning Paper" (Teams Digest)
The primary push mechanism is an automated daily digest sent to a Microsoft Teams channel via Adaptive Cards. This provides a quick, high-level briefing of the most critical news and research, filtered by relevance and priority.

### Think Tank Intelligence Portal (Web)
A separate, read-only web portal provides a rich, interactive interface for browsing the intelligence.
*   **Morning Paper Dashboard:** A digital version of the daily digest with anchor and category filtering.
*   **Archive:** A comprehensive search interface for the entire article history (12,000+ items), featuring advanced filtering and sorting.
*   **Architecture:** Built on the **Observable Framework**, it runs entirely client-side using **DuckDB-WASM** to query highly optimized Parquet files exported by the pipeline.

### Microsoft Power BI
For deeper exploration and historical analysis, **Microsoft Power BI** connects directly to the Azure PostgreSQL database. This allows for interactive filtering, trend analysis, and drill-down capabilities.

## 4. Future Scope

Once the core data pipeline is mature and validated, development will explore ways to build on this foundation.

*   **Advanced AI Analysis:** Using a multi-agent LLM pipeline to perform advanced summarization and categorization.
*   **Enhanced Observability:** Creating a dedicated data model to log and store pipeline run metrics, allowing for performance and data quality monitoring in Power BI dashboards.
