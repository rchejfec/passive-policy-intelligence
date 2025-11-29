# AI Daily Digest Pipeline

This project is a cloud-based data pipeline that ingests external articles from public policy sources, analyzes them against a curated knowledge base, and delivers a curated digest to a Microsoft Teams channel.

## System Overview

The system is architected as a modular data pipeline hosted on an Azure VM, orchestrated by Cron, and integrated with Microsoft Teams for delivery.

* **Infrastructure:** Hosted on a Standard_B1s Azure VM running Ubuntu 22.04 LTS.
* **Orchestration:** A Cron scheduler triggers the pipeline twice daily (7:00 AM and 3:00 PM ET).
* **Ingestion:** Fetches and de-duplicates articles from RSS feeds.
* **Analysis:** Uses vector embeddings (ChromaDB + `sentence-transformers`) to calculate semantic relevance against user-defined "Semantic Anchors".
* **Enrichment:** Applies tiered logic to flag high-relevance content ("Highlights").
* **Delivery:** Generates an interactive "Morning Paper" digest (Adaptive Cards) and sends it to Microsoft Teams via Webhook.
* **Storage:** All data is persisted in a PostgreSQL database, which also feeds a Power BI dashboard.

## Key Features

* **Automated & Resilient:** Self-healing pipeline with automatic retries and alerting.
* **Semantic Intelligence:** Matches articles to specific policy interests using vector similarity.
* **Smart Filtering:** Prioritizes content based on source authority and historical relevance thresholds.
* **Interactive Digest:** Delivers a clean, collapsible daily briefing directly to Teams.
* **Admin Toolkit:** A CLI (`manage.py`) for managing subscribers, anchors, and system maintenance.

## Getting Started

For detailed instructions on how to operate, maintain, and troubleshoot the system, please refer to the **[Operations Guide](docs/OPERATIONS.md)**.

For an inventory of the active codebase, see **[ACTIVE_CODEBASE.md](ACTIVE_CODEBASE.md)**.

## Documentation

* **[Project Overview](docs/100_Project-Overview.md)**: High-level goals and context.
* **[Architecture](docs/200_Architecture.md)**: Detailed system design.
* **[Database Schema](docs/500_Database-Schema.md)**: PostgreSQL tables and relationships.
