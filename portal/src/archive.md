---
theme: dashboard
title: Archive
toc: false
---

<link rel="stylesheet" href="theme.css">

# Archive

<div class="card" style="background: #d1ecf1; border-left: 4px solid #0c5460;">
  <strong>🔍 Archive Search:</strong> Searchable repository of all analyzed content since June 2024. This demonstrates the system's "evidence base" capability - allowing retrospective analysis of how policy issues evolved over time. Use advanced filters to explore historical matches across sources, time periods, and semantic anchors.
</div>

```js
import {DuckDBClient} from "npm:@observablehq/duckdb";

const db = await DuckDBClient.of({
  archive: FileAttachment("data/archive.parquet").parquet()
});
```

```js
// Fetch all data
const allDataArrow = await db.query(`SELECT * FROM archive ORDER BY normalized_score DESC`);
const allArchiveData = Array.from(allDataArrow);
```

```js
// 2. Get filter options from data
const anchors = [null, ...new Set(allArchiveData.map(d => d.anchor_name))].sort((a, b) => {
  if (a === null) return -1;
  if (b === null) return 1;
  return a.localeCompare(b);
});
const categories = [null, ...new Set(allArchiveData.map(d => d.source_category))].sort((a, b) => {
  if (a === null) return -1;
  if (b === null) return 1;
  return a.localeCompare(b);
});
```

```js
// 3. Filter inputs
const anchorFilter = Inputs.select(anchors, {label: "Semantic Anchor", format: x => x || "All"});
const selectedAnchor = Generators.input(anchorFilter);

const categoryFilter = Inputs.select(categories, {label: "Source Type", format: x => x || "All"});
const selectedCategory = Generators.input(categoryFilter);

// Date range filter
const dateRangeFilter = Inputs.date({label: "From Date", value: null});
const dateFrom = Generators.input(dateRangeFilter);

// Score range filter
const scoreRangeFilter = Inputs.range([0, 1], {label: "Min Similarity Score (0-1)", step: 0.05, value: 0});
const minScore = Generators.input(scoreRangeFilter);

// Text search
const searchFilter = Inputs.text({label: "Search", placeholder: "Search titles..."});
const searchTerm = Generators.input(searchFilter);

// Sort options - use simple values, not objects
const sortFilter = Inputs.select(
  ["score_desc", "score_asc", "date_desc", "date_asc"],
  {
    value: "score_desc",
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
    <div>${anchorFilter}</div>
    <div>${categoryFilter}</div>
    <div>${dateRangeFilter}</div>
    <div>${scoreRangeFilter}</div>
    <div>${sortFilter}</div>
    <div>${searchFilter}</div>
  </div>
</div>

```js
// 4. Apply filters using JavaScript
let filtered = allArchiveData;

if (selectedCategory) {
  filtered = filtered.filter(d => d.source_category === selectedCategory);
}

if (selectedAnchor) {
  filtered = filtered.filter(d => d.anchor_name === selectedAnchor);
}

if (dateFrom) {
  const filterDate = new Date(dateFrom);
  filtered = filtered.filter(d => new Date(d.created_at) >= filterDate);
}

if (minScore > 0) {
  filtered = filtered.filter(d => d.normalized_score >= minScore);
}

if (searchTerm) {
  const lowerSearch = searchTerm.toLowerCase();
  filtered = filtered.filter(d => d.title.toLowerCase().includes(lowerSearch));
}

// Sort the results
switch(selectedSort) {
  case "date_desc":
    filtered.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
    break;
  case "date_asc":
    filtered.sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
    break;
  case "score_desc":
    filtered.sort((a, b) => b.normalized_score - a.normalized_score);
    break;
  case "score_asc":
    filtered.sort((a, b) => a.normalized_score - b.normalized_score);
    break;
}

const results = filtered;
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
    "normalized_score"
  ],
  header: {
    created_at: "Date",
    title: "Headline",
    source_name: "Source",
    anchor_name: "Semantic Anchor",
    normalized_score: "Score"
  },
  format: {
    created_at: d => new Date(d).toLocaleDateString(),

    title: (t, i, data) => {
      const row = data[i];
      const orgStar = row.is_org_highlight ? "⭐ " : "";
      return htl.html`<a href="${row.link}" target="_blank" style="font-weight:${row.is_org_highlight ? 'bold' : 'normal'};">${orgStar}${t}</a>`;
    },

    normalized_score: d => d.toFixed(2)
  },
  rows: 50,
  width: {
    title: "50%",
    source_name: "15%",
    anchor_name: "20%",
    normalized_score: "8%",
    created_at: "7%"
  }
})
```