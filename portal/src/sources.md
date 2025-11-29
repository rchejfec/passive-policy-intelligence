---
theme: dashboard
title: Source Manifest
toc: false
---

<link rel="stylesheet" href="theme.css">

# Source Manifest

<div class="card">
  Transparency report: All monitored organizations.
</div>

```js
import {DuckDBClient} from "npm:@observablehq/duckdb";

const db = await DuckDBClient.of({
  sources: FileAttachment("data/sources.parquet")
});
```

```js
const sourcesArrow = await db.query("SELECT * FROM sources ORDER BY source_name");
const sources = Array.from(sourcesArrow);
```

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
  }
})
```
