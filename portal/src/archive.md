---
theme: dashboard
title: The Archive
toc: false
---

<link rel="stylesheet" href="theme.css">

# The Archive

<div class="card">
  Full repository search.
</div>

```js
import {DuckDBClient} from "npm:@observablehq/duckdb";

// 1. Load the lightweight archive file
const db = await DuckDBClient.of({
  archive: FileAttachment("data/archive.parquet"),
  sources: FileAttachment("data/sources.parquet"),
  anchors: FileAttachment("data/anchors.parquet")
});
```

```js
// 2. Get filter options from data
const categoriesData = await db.query("SELECT DISTINCT source_category FROM archive ORDER BY source_category");
const categories = [null, ...Array.from(categoriesData).map(d => d.source_category)];

const sourcesData = await db.query("SELECT DISTINCT source_name FROM archive ORDER BY source_name");
const sources = [null, ...Array.from(sourcesData).map(d => d.source_name)];

const anchorsData = await db.query("SELECT DISTINCT anchor_name FROM archive ORDER BY anchor_name");
const anchors = [null, ...Array.from(anchorsData).map(d => d.anchor_name)];
```

```js
// 3. Filter inputs
const categoryFilter = Inputs.select(categories, {label: "Source Type", format: x => x || "All"});
const selectedCategory = Generators.input(categoryFilter);

const sourceFilter = Inputs.select(sources, {label: "Source", format: x => x || "All"});
const selectedSource = Generators.input(sourceFilter);

const anchorFilter = Inputs.select(anchors, {label: "Focus Area", format: x => x || "All"});
const selectedAnchor = Generators.input(anchorFilter);

// Date range filter
const dateRangeFilter = Inputs.date({label: "From Date", value: null});
const dateFrom = Generators.input(dateRangeFilter);

// Score range filter
const scoreRangeFilter = Inputs.range([0, 1], {label: "Min Relevance Score", step: 0.05, value: 0});
const minScore = Generators.input(scoreRangeFilter);

// Text search
const searchFilter = Inputs.text({label: "Search", placeholder: "Search titles..."});
const searchTerm = Generators.input(searchFilter);

// Sort options - use simple values, not objects
const sortFilter = Inputs.select(
  ["date_desc", "date_asc", "score_desc", "score_asc"],
  {
    value: "date_desc",
    label: "Sort By",
    format: (sortType) => {
      if (sortType === "date_desc") return "Newest First";
      if (sortType === "date_asc") return "Oldest First";
      if (sortType === "score_desc") return "Highest Score";
      if (sortType === "score_asc") return "Lowest Score";
      return sortType;
    }
  }
);
const selectedSort = Generators.input(sortFilter);
```

<div class="card" style="background: #f8f9fa;">
  <h3 style="margin-top: 0;">Filters</h3>

  <div class="grid grid-cols-3" style="gap: 1rem; margin-bottom: 1rem;">
    <div>${categoryFilter}</div>
    <div>${sourceFilter}</div>
    <div>${anchorFilter}</div>
  </div>

  <div class="grid grid-cols-3" style="gap: 1rem; margin-bottom: 1rem;">
    <div>${dateRangeFilter}</div>
    <div>${scoreRangeFilter}</div>
    <div>${sortFilter}</div>
  </div>

  <div>${searchFilter}</div>
</div>

```js
// 4. Build dynamic query with filters
const whereConditions = [];

if (selectedCategory) whereConditions.push(`source_category = '${selectedCategory}'`);
if (selectedSource) whereConditions.push(`source_name = '${selectedSource}'`);
if (selectedAnchor) whereConditions.push(`anchor_name = '${selectedAnchor}'`);
if (dateFrom) whereConditions.push(`created_at >= '${dateFrom.toISOString()}'`);
if (minScore > 0) whereConditions.push(`similarity_score >= ${minScore}`);
if (searchTerm) whereConditions.push(`LOWER(title) LIKE '%${searchTerm.toLowerCase()}%'`);

const whereClause = whereConditions.length > 0
  ? `WHERE ${whereConditions.join(' AND ')}`
  : '';

// Build ORDER BY clause
let orderByClause;
switch(selectedSort) {
  case "date_desc": orderByClause = "created_at DESC"; break;
  case "date_asc": orderByClause = "created_at ASC"; break;
  case "score_desc": orderByClause = "similarity_score DESC"; break;
  case "score_asc": orderByClause = "similarity_score ASC"; break;
}

// Execute query
const archiveArrow = await db.query(`
  SELECT
    article_id,
    created_at,
    title,
    source_name,
    source_category,
    anchor_name,
    similarity_score,
    link,
    is_org_highlight,
    is_anchor_highlight
  FROM archive
  ${whereClause}
  ORDER BY ${orderByClause}
`);

const results = Array.from(archiveArrow);
```

```js
// Display count
const resultCount = results.length;
const uniqueArticles = new Set(results.map(d => d.article_id)).size;
```

<div class="card">
  <strong>${resultCount} matches</strong> (${uniqueArticles} unique articles)
</div>

```js
// 5. Render the Results Table
Inputs.table(results, {
  columns: [
    "created_at",
    "title",
    "source_name",
    "anchor_name",
    "similarity_score"
  ],
  header: {
    created_at: "Date",
    title: "Headline",
    source_name: "Source",
    anchor_name: "Focus Area",
    similarity_score: "Score"
  },
  format: {
    created_at: d => new Date(d).toLocaleDateString(),

    title: (t, i, data) => {
      const row = data[i];
      const orgStar = row.is_org_highlight ? "⭐ " : "";
      const anchorIcon = row.is_anchor_highlight ? "📌 " : "";
      return htl.html`<a href="${row.link}" target="_blank" style="font-weight:${row.is_org_highlight ? 'bold' : 'normal'};">${orgStar}${anchorIcon}${t}</a>`;
    },

    similarity_score: d => d.toFixed(2)
  },
  rows: 50,
  layout: "auto"
})
```