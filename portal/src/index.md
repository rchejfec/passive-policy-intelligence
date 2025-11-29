---
theme: dashboard
title: The Morning Paper
toc: false
---

<link rel="stylesheet" href="theme.css">

# The Morning Paper

<div class="card">
  Recent digest from the last week.
</div>

```js
import {DuckDBClient} from "npm:@observablehq/duckdb";

const db = await DuckDBClient.of({
  articles: FileAttachment("data/morning_paper.parquet")
});
```

```js
// Fetch all data first (morning_paper.parquet already has last 7 days)
const allDataArrow = await db.query(`SELECT * FROM articles ORDER BY created_at DESC`);
const allData = Array.from(allDataArrow);
```

```js
// Get unique values for filters
const anchors = [...new Set(allData.map(d => d.anchor_name))].sort();
const categories = [...new Set(allData.map(d => d.source_category))].sort();
```

```js
// Filter inputs
const anchorInput = Inputs.select([null, ...anchors], {label: "Focus Area", format: x => x || "All Topics"});
const selectedAnchor = Generators.input(anchorInput);

const categoryInput = Inputs.select([null, ...categories], {label: "Source Type", format: x => x || "All Sources"});
const selectedCategory = Generators.input(categoryInput);

const sortInput = Inputs.select(
  ["score", "date"],
  {value: "score", label: "Sort by", format: x => x === "score" ? "Relevance" : "Most Recent"}
);
const selectedSort = Generators.input(sortInput);
```

<div class="card">
  <div class="grid grid-cols-3" style="gap: 1rem;">
    <div>${anchorInput}</div>
    <div>${categoryInput}</div>
    <div>${sortInput}</div>
  </div>
</div>

```js
// Apply filters
let filtered = allData;

if (selectedAnchor) {
  filtered = filtered.filter(d => d.anchor_name === selectedAnchor);
}

if (selectedCategory) {
  filtered = filtered.filter(d => d.source_category === selectedCategory);
}

// Apply sort
if (selectedSort === "score") {
  filtered.sort((a, b) => b.similarity_score - a.similarity_score);
} else {
  filtered.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
}

const morningPaper = filtered;
```

```js
// Stats
const uniqueArticles = new Set(morningPaper.map(d => d.article_id)).size;
const highlights = morningPaper.filter(d => d.is_org_highlight).length;
const avgScore = morningPaper.length > 0
  ? (morningPaper.reduce((sum, d) => sum + d.similarity_score, 0) / morningPaper.length).toFixed(2)
  : "0.00";
```

<div class="card" style="background: #f8f9fa; margin-bottom: 1rem;">
  <div class="grid grid-cols-4" style="gap: 1rem; text-align: center;">
    <div>
      <div style="font-size: 2rem; font-weight: bold;">${uniqueArticles}</div>
      <div style="color: #666;">Articles</div>
    </div>
    <div>
      <div style="font-size: 2rem; font-weight: bold;">${morningPaper.length}</div>
      <div style="color: #666;">Matches</div>
    </div>
    <div>
      <div style="font-size: 2rem; font-weight: bold;">${highlights}</div>
      <div style="color: #666;">Highlights</div>
    </div>
    <div>
      <div style="font-size: 2rem; font-weight: bold;">${avgScore}</div>
      <div style="color: #666;">Avg. Relevance</div>
    </div>
  </div>
</div>

```js
Inputs.table(morningPaper, {
  columns: ["title", "source_name", "anchor_name", "similarity_score", "created_at"],
  header: {
    title: "Headline",
    source_name: "Source",
    anchor_name: "Focus Area",
    similarity_score: "Score",
    created_at: "Date"
  },
  format: {
    title: (t, i) => {
      const row = morningPaper[i];
      const star = row.is_org_highlight ? "⭐ " : "";
      const pin = row.is_anchor_highlight ? "📌 " : "";
      return htl.html`<a href="${row.link}" target="_blank">${star}${pin}${t}</a>`;
    },
    created_at: d => new Date(d).toLocaleDateString(),
    similarity_score: d => d.toFixed(2)
  },
  rows: 25
})
```
