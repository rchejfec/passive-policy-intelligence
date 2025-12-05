# 501: Database Schema

This document provides a detailed technical reference for the Azure PostgreSQL database schema.

## Foundational Tables

These tables store the core, foundational data for the application.

### `sources`

Stores a master list of all organizations and websites being monitored.

| Column Name | Data Type | Constraints | Description |
|---|---|---|---|
| `id` | `SERIAL` | `PRIMARY KEY` | Unique identifier for the source. |
| `name` | `TEXT` | `NOT NULL` | The common name of the organization. |
| `site_url` | `TEXT` | | The main URL of the organization's website. |
| `feed_url` | `TEXT` | | The primary RSS feed URL. |
| `social_feed_url` | `TEXT` | | A secondary social media-related feed URL. |
| `ga_feed_url` | `TEXT` | | The Google Alerts-generated RSS feed URL. |
| `category` | `TEXT` | | The category of the source (e.g., 'Think Tank', 'News Media'). |
| `tags` | `TEXT` | | Comma-separated tags related to the source. |
| `notes` | `TEXT` | | General-purpose notes about the source. |
| `is_active` | `BOOLEAN` | `DEFAULT true` | Flag to indicate if the source should be actively fetched. |
| `last_fetched` | `TIMESTAMP` | | Timestamp of the last successful fetch attempt. |

### `articles`

Stores a permanent archive of every unique external article collected by the ingestion engine.

| Column Name | Data Type | Constraints | Description |
|---|---|---|---|
| `id` | `SERIAL` | `PRIMARY KEY` | Unique identifier for the article. |
| `source_id` | `INTEGER` | `FOREIGN KEY` | Links to the `sources` table. |
| `title` | `TEXT` | | The title of the article. |
| `link` | `TEXT` | `NOT NULL, UNIQUE` | The canonical URL for the article. |
| `summary` | `TEXT` | | The summary or description from the RSS feed. |
| `published_date` | `TIMESTAMP` | | The original publication date of the article. |
| `retrieved_from_url` | `TEXT` | | The specific feed URL this article was found in. |
| `status` | `TEXT` | `DEFAULT 'new'` | The processing status of the article. |
| `is_flagged` | `BOOLEAN` | `DEFAULT false` | A flag for manual review. |
| `created_at` | `TIMESTAMP` | `DEFAULT CURRENT_TIMESTAMP` | Timestamp when the article was first added to the database. |
| `indexed_at` | `TIMESTAMP` | | Timestamp when the article was indexed into ChromaDB. |
| `analyzed_at` | `TIMESTAMP` | | Timestamp when the article was processed by the analysis engine. |
| `enrichment_processed_at` | `TIMESTAMP` | | Timestamp when the article was processed by the enrichment engine. |
| `is_org_highlight` | `BOOLEAN` | `DEFAULT false` | Flag indicating if the article is an overall organizational highlight. |
| `newsletter_sent_at` | `TIMESTAMP` | | Timestamp when the article was last included in a newsletter. |

### `knowledge_base`

Stores a structured representation of the team's internal reference materials.

| Column Name | Data Type | Constraints | Description |
|---|---|---|---|
| `id` | `SERIAL` | `PRIMARY KEY` | Unique identifier for the knowledge base entry. |
| `source_location` | `TEXT` | `UNIQUE` (with `program_tag`) | The URL or local file path of the content. |
| `source_type` | `TEXT` | | The type of content (e.g., 'web', 'pdf', 'program_charter'). |
| `program_tag` | `TEXT` | `UNIQUE` (with `source_location`) | The slug-like identifier for the program it belongs to. |
| `program_name` | `TEXT` | | The human-readable name of the program. |
| `status` | `TEXT` | | The status of the content (e.g., 'active', 'draft'). |
| `initiative_type` | `TEXT` | | The type of initiative (e.g., 'program'). |
| `product_name` | `TEXT` | | A human-readable name for the specific content. |

### `tags`

Stores a master list of thematic tags and their pre-computed vector embeddings.

| Column Name | Data Type | Constraints | Description |
|---|---|---|---|
| `tag_name` | `TEXT` | `PRIMARY KEY` | The unique name of the tag. |
| `tag_category` | `TEXT` | | A category for grouping tags. |
| `embedding` | `BYTEA` | `NOT NULL` | The stored vector embedding for the tag name. |

## Core Engine Tables

These tables define and store the results of the semantic analysis engine.

### `semantic_anchors`

Defines the user-created "lenses" for analyzing content.

| Column Name | Data Type | Constraints | Description |
|---|---|---|---|
| `id` | `SERIAL` | `PRIMARY KEY` | Unique identifier for the anchor. |
| `name` | `TEXT` | `NOT NULL, UNIQUE` | The unique, human-readable name of the anchor. |
| `description` | `TEXT` | | A brief description of the anchor's purpose. |
| `anchor_author` | `TEXT` | | The person who created the anchor. |
| `is_active` | `BOOLEAN` | `NOT NULL, DEFAULT true` | Flag to indicate if the anchor should be used in analysis. |
| `created_at` | `TIMESTAMP` | `DEFAULT CURRENT_TIMESTAMP` | Timestamp when the anchor was created. |

### `anchor_components`

Defines the many-to-many relationship between anchors and their building blocks (tags, KB items, etc.).

| Column Name | Data Type | Constraints | Description |
|---|---|---|---|
| `id` | `SERIAL` | `PRIMARY KEY` | Unique identifier for the component link. |
| `anchor_id` | `INTEGER` | `NOT NULL, FOREIGN KEY` | Links to the `semantic_anchors` table. |
| `component_type`| `TEXT` | `NOT NULL` | The type of component (e.g., 'tag', 'kb_item', 'program'). |
| `component_id` | `TEXT` | `NOT NULL` | The identifier for the component (e.g., a `tag_name` or `source_location`). |

### `article_anchor_links`

Stores the output of the analysis engine, connecting articles to anchors.

| Column Name | Data Type | Constraints | Description |
|---|---|---|---|
| `id` | `SERIAL` | `PRIMARY KEY` | Unique identifier for the link. |
| `article_id` | `INTEGER` | `NOT NULL, FOREIGN KEY` | Links to the `articles` table. |
| `anchor_id` | `INTEGER` | `NOT NULL, FOREIGN KEY` | Links to the `semantic_anchors` table. |
| `similarity_score`| `REAL` | `NOT NULL` | The calculated semantic similarity score between the article and anchor. |
| `linked_at` | `TIMESTAMP` | `DEFAULT CURRENT_TIMESTAMP` | Timestamp when the link was created. |
| `is_anchor_highlight`| `BOOLEAN` | | Flag set by the enrichment engine based on Champion V4 logic. |
| `is_org_highlight` | `BOOLEAN` | | Flag set by the enrichment engine based on Champion V4 logic. |
