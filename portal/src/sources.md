---
theme: dashboard
title: Source Transparency
toc: false
---

<link rel="stylesheet" href="theme.css">

# Source Transparency

<div class="card" style="background: #d1ecf1; border-left: 4px solid #0c5460;">
  <strong>🔍 Transparency Commitment:</strong> This page provides complete disclosure of both the data sources being monitored and the semantic anchors (policy topics) used for ranking. No hidden sources, no opaque ranking criteria. Users control both the "world" of data the system analyzes and the "lens" used to evaluate relevance.
</div>

```js
import {DuckDBClient} from "npm:@observablehq/duckdb";

const db = await DuckDBClient.of({
  sources: FileAttachment("data/sources.parquet"),
  anchors: FileAttachment("data/anchors.parquet")
});
```

```js
const sourcesArrow = await db.query("SELECT * FROM sources ORDER BY source_name");
const sources = Array.from(sourcesArrow);

const anchorsArrow = await db.query("SELECT * FROM anchors ORDER BY anchor_name");
const anchors = Array.from(anchorsArrow);
```

## Semantic Anchors (Policy Focus Areas)

<div class="card">
  <p>These are the user-defined policy topics that guide the system's ranking. Each anchor represents a specific area of policy interest, defined using the HyDE (Hypothetical Document Embeddings) methodology.</p>
</div>

```js
Inputs.table(anchors, {
  columns: [
    "anchor_name",
    "anchor_description"
  ],
  header: {
    anchor_name: "Semantic Anchor",
    anchor_description: "Description"
  },
  rows: anchors.length
})
```

---

## Monitored Sources

```js
// Calculate category distribution
const categoryGroups = d3.rollup(sources, v => v.length, d => d.source_category);
const categorySummary = Array.from(categoryGroups).sort((a, b) => b[1] - a[1]);
```

```js
const summaryHtml = htl.html`<div class="card" style="background: #f8f9fa;">
  <h3 style="margin-top: 0;">Source Distribution</h3>
  <p><strong>${sources.length} organizations</strong> monitored across ${categorySummary.length} categories:</p>
  <ul>
    ${categorySummary.map(([cat, count]) => htl.html`<li><strong>${cat}:</strong> ${count} sources</li>`)}
  </ul>
</div>`;
```

${summaryHtml}

```js
Inputs.table(sources, {
  columns: [
    "source_name",
    "source_category",
    "url"
  ],
  header: {
    source_name: "Organization",
    source_category: "Category",
    url: "Website"
  },
  format: {
    url: d => htl.html`<a href="${d}" target="_blank">Link</a>`
  },
  rows: sources.length
})
```
