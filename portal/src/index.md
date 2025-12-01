---
theme: dashboard
title: Daily Review
toc: false
---

<link rel="stylesheet" href="theme.css">

# Daily Review

<div class="card" style="background: #fff3cd; border-left: 4px solid #856404;">
  <strong>📊 Daily Review:</strong> This view shows articles from the last 7 days, ranked by semantic similarity to your chosen policy focus areas (Semantic Anchors). The system analyzes incoming content daily and highlights the most relevant matches based on tiered thresholds that account for source authority.
</div>

```js
import {DuckDBClient} from "npm:@observablehq/duckdb";

const db = await DuckDBClient.of({
  articles: FileAttachment("data/morning_paper.parquet").parquet()
});
```

```js
// Fetch all data first (morning_paper.parquet already has last 7 days)
const allDataArrow = await db.query(`SELECT * FROM articles ORDER BY created_at DESC`);
const allData = Array.from(allDataArrow);
```

```js
// Get unique values for filters
const anchors = [null, ...new Set(allData.map(d => d.anchor_name))].sort((a, b) => {
  if (a === null) return -1;
  if (b === null) return 1;
  return a.localeCompare(b);
});
const categories = [null, ...new Set(allData.map(d => d.source_category))].sort((a, b) => {
  if (a === null) return -1;
  if (b === null) return 1;
  return a.localeCompare(b);
});
```

```js
// Filter inputs
const anchorInput = Inputs.select(anchors, {label: "Semantic Anchor", format: x => x || "All Anchors"});
const selectedAnchor = Generators.input(anchorInput);

const categoryInput = Inputs.select(categories, {label: "Source Type", format: x => x || "All Sources"});
const selectedCategory = Generators.input(categoryInput);
```

<div class="card">
  <div class="grid grid-cols-2" style="gap: 1rem;">
    <div>${anchorInput}</div>
    <div>${categoryInput}</div>
  </div>
</div>

```js
// Apply filters and sort by relevance (normalized_score)
let filtered = allData;

if (selectedAnchor) {
  filtered = filtered.filter(d => d.anchor_name === selectedAnchor);
}

if (selectedCategory) {
  filtered = filtered.filter(d => d.source_category === selectedCategory);
}

// Always sort by normalized score (relevance)
filtered.sort((a, b) => b.normalized_score - a.normalized_score);

const morningPaper = filtered;
```

```js
// Stats
const uniqueArticles = new Set(morningPaper.map(d => d.article_id)).size;
const avgScore = morningPaper.length > 0
  ? (morningPaper.reduce((sum, d) => sum + d.normalized_score, 0) / morningPaper.length).toFixed(2)
  : "0.00";
```

<div class="card" style="background: #f8f9fa; margin-bottom: 1rem;">
  <div class="grid grid-cols-3" style="gap: 1rem; text-align: center;">
    <div>
      <div style="font-size: 2rem; font-weight: bold;">${uniqueArticles}</div>
      <div style="color: #666;">Articles</div>
    </div>
    <div>
      <div style="font-size: 2rem; font-weight: bold;">${morningPaper.length}</div>
      <div style="color: #666;">Article-Anchor Pairs</div>
    </div>
    <div>
      <div style="font-size: 2rem; font-weight: bold;">${avgScore}</div>
      <div style="color: #666;">Avg. Relevance Score</div>
    </div>
  </div>
</div>

```js
Inputs.table(morningPaper, {
  columns: ["title", "source_name", "anchor_name", "normalized_score", "created_at"],
  header: {
    title: "Headline",
    source_name: "Source",
    anchor_name: "Semantic Anchor",
    normalized_score: "Score",
    created_at: "Date"
  },
  format: {
    title: (t, i) => {
      const row = morningPaper[i];
      const star = row.is_org_highlight ? "⭐ " : "";
      return htl.html`<a href="${row.link}" target="_blank">${star}${t}</a>`;
    },
    created_at: d => new Date(d).toLocaleDateString(),
    normalized_score: d => d.toFixed(2)
  },
  rows: 25,
  width: {
    title: "50%",
    source_name: "15%",
    anchor_name: "20%",
    normalized_score: "8%",
    created_at: "7%"
  }
})
```
