# Demo Setup Guide: G7 GovAI Grand Challenge

This guide walks through preparing the Passive Policy Intelligence system for demonstration to G7 GovAI Grand Challenge judges.

## Overview

The demo setup process creates **4 demonstration semantic anchors** based on HyDE (Hypothetical Document Embeddings) and re-analyzes recent articles against these policy-relevant topics. This approach showcases the system's capabilities while using content appropriate for the judging audience.

## Demo Topics

The four demo anchors cover distinct policy domains:

1. **Housing Affordability & Supply** - Municipal policy, zoning reform, social housing
2. **Sustainable Transportation Infrastructure** - Public transit, EV adoption, active mobility
3. **Agricultural Resilience & Food Security** - Climate adaptation, supply chains, rural development
4. **AI Governance & Public Sector Deployment** - Algorithmic transparency, workforce implications, democratic accountability

## Files

- **`demo_hyde_documents.json`** - HyDE documents for each anchor (400-500 words each)
- **`setup_demo_anchors.py`** - Creates anchors and indexes HyDE embeddings
- **`reanalyze_for_demo.py`** - Re-runs analysis on recent articles
- **`DEMO_SETUP_README.md`** - This file

## Step-by-Step Process

### Step 1: Review HyDE Documents

```bash
# View the HyDE documents
cat user_content/demo_hyde_documents.json
```

The HyDE documents are hypothetical policy briefs representing "ideal" content for each topic. These serve as semantic anchors for matching real articles.

### Step 2: Setup Demo Anchors (Dry Run)

```bash
# Preview what will be created
python scripts/setup_demo_anchors.py --dry-run

# Preview with PROG: anchor deactivation
python scripts/setup_demo_anchors.py --dry-run --deactivate-prog
```

**What this does:**
- Loads 4 HyDE documents from JSON
- Generates sentence-transformer embeddings for each
- Creates `DEMO:` semantic anchors in PostgreSQL
- Indexes HyDE embeddings to ChromaDB collection
- Optionally deactivates `PROG:` anchors (reversible)

### Step 3: Execute Demo Anchor Setup

```bash
# Create demo anchors and deactivate PROG anchors
python scripts/setup_demo_anchors.py --deactivate-prog
```

**Expected output:**
```
======================================================================
DEMO ANCHOR SETUP SCRIPT
======================================================================
✓ Connected to PostgreSQL database
✓ Loaded 4 demo anchor definitions
✓ Generated embeddings with shape: (4, 384)
✓ Created 4 demo anchors in PostgreSQL
✓ Indexed 4 HyDE documents to ChromaDB
✓ Deactivated 5 PROG: anchors
======================================================================
✅ DEMO SETUP COMPLETE
======================================================================
```

### Step 4: Re-analyze Recent Articles (Dry Run)

```bash
# Preview analysis on last 3 months
python scripts/reanalyze_for_demo.py --months 3 --dry-run

# Or specify a specific date
python scripts/reanalyze_for_demo.py --since 2025-10-01 --dry-run
```

**What this does:**
- Identifies articles published in the specified period
- Clears existing `DEMO:` anchor links (if any)
- Re-runs semantic analysis against DEMO anchors only
- Reports match counts and score statistics

### Step 5: Execute Re-analysis

```bash
# Re-analyze last 3 months
python scripts/reanalyze_for_demo.py --months 3
```

**Expected output:**
```
======================================================================
RE-ANALYZE ARTICLES FOR DEMO
======================================================================
✓ Found 4 active DEMO: anchors
✓ Articles to analyze: 2,847
✓ Date range: 2025-10-01 to 2025-12-30

🔍 Running semantic analysis...
   Processing batch 1/57...
   [Analysis progress...]
   ✓ Analysis complete

Results by anchor:
Anchor Name                                        Matches    Avg Score    Max Score
----------------------------------------------------------------------------------
DEMO: AI Governance & Public Sector Deployment         342       0.3245       0.7821
DEMO: Agricultural Resilience & Food Security          289       0.3102       0.7543
DEMO: Housing Affordability & Supply                   412       0.3387       0.8102
DEMO: Sustainable Transportation Infrastructure        376       0.3221       0.7932
----------------------------------------------------------------------------------
TOTAL                                                1,419
======================================================================
```

## Verification

After setup, verify the demo configuration:

```sql
-- Check active anchors
SELECT id, name, is_active
FROM semantic_anchors
ORDER BY name;

-- Count matches per demo anchor
SELECT
    sa.name,
    COUNT(*) as matches,
    AVG(aal.similarity_score) as avg_score
FROM semantic_anchors sa
LEFT JOIN article_anchor_links aal ON sa.id = aal.anchor_id
WHERE sa.name LIKE 'DEMO:%'
GROUP BY sa.id, sa.name
ORDER BY sa.name;

-- Top articles for each demo anchor
SELECT
    sa.name as anchor,
    a.title,
    a.source_name,
    a.published_date,
    aal.similarity_score
FROM article_anchor_links aal
JOIN semantic_anchors sa ON aal.anchor_id = sa.id
JOIN articles a ON aal.article_id = a.id
WHERE sa.name LIKE 'DEMO:%'
ORDER BY sa.name, aal.similarity_score DESC
LIMIT 20;
```

## Reverting After Demo

To restore the system to production state:

```sql
-- Reactivate PROG: anchors
UPDATE semantic_anchors
SET is_active = true, updated_at = NOW()
WHERE name LIKE 'PROG:%';

-- Deactivate demo anchors (or delete them)
UPDATE semantic_anchors
SET is_active = false, updated_at = NOW()
WHERE name LIKE 'DEMO:%';

-- Or delete demo anchors entirely
DELETE FROM article_anchor_links
WHERE anchor_id IN (SELECT id FROM semantic_anchors WHERE name LIKE 'DEMO:%');

DELETE FROM semantic_anchors
WHERE name LIKE 'DEMO:%';
```

Then re-run analysis for PROG anchors:

```bash
python src/analysis/analyze_articles.py
```

## Demo Delivery Layer

The demo anchors will automatically appear in:

1. **Teams Digest** - Daily intelligence summary cards
2. **Observable Portal** - Morning Paper dashboard and archive
3. **Parquet Export** - Data for portal visualization

To regenerate portal data:

```bash
python scripts/export_to_parquet.py
cd portal && npm run build
```

## Troubleshooting

### No articles matched to demo anchors

**Cause:** Similarity thresholds may be filtering out matches
**Solution:** Check the `MINIMUM_SIMILARITY_SCORE` in `src/analysis/analyze_articles.py`

### ChromaDB indexing fails

**Cause:** Collection may not exist or embeddings are wrong dimension
**Solution:** Delete and recreate ChromaDB collection:

```python
import chromadb
client = chromadb.PersistentClient(path='data/chroma_db')
client.delete_collection('irpp_research')
# Then re-run setup_demo_anchors.py
```

### PROG: anchors still active

**Cause:** `--deactivate-prog` flag wasn't used
**Solution:** Manually deactivate:

```sql
UPDATE semantic_anchors SET is_active = false WHERE name LIKE 'PROG:%';
```

## Notes

- **Demo data is isolated**: PROG anchor data remains in the database, just inactive
- **Reversible**: All demo changes can be undone with SQL commands
- **HyDE approach**: This demonstrates the future methodology (pure HyDE anchors without tag/KB components)
- **MaxSim deferred**: Current scoring logic used for stability; MaxSim implementation planned post-demo

## Timeline

- **Setup**: 15-20 minutes (embedding generation, indexing)
- **Re-analysis**: 10-30 minutes (depends on article count)
- **Verification**: 5 minutes
- **Total**: ~45 minutes for full demo preparation
