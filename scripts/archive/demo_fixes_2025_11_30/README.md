# Demo Fix Scripts - November 30, 2025

## Context
These scripts were created to fix issues encountered during G7 GovAI demo preparation. They are one-time fixes and diagnostic tools that are no longer needed in production.

## Issues Fixed

### 1. DEMO Anchor Enrichment Bug
**Problem**: DEMO anchor links were created after articles were already enriched. The enrichment engine is article-based (checks `enrichment_processed_at`), so it skipped these articles even though they had new unenriched anchor links.

**Fix**: `fix_demo_enrichment.py` - Reset `enrichment_processed_at` for DEMO articles and re-ran enrichment.

**Result**: 769 articles re-enriched, 2,591 DEMO links processed, 894 highlights flagged.

### 2. News & Media Category Name Mismatch
**Problem**: Code used `'News Media'` but database category was updated to `'News & Media'`. This caused Tier 3 enrichment rules to fail (no matches found).

**Fix**: `fix_news_media_enrichment.py` - Re-enriched all News & Media articles after updating code constants.

**Result**: 6,534 articles re-enriched, 18,531 links processed, 2,322 highlights flagged.

### 3. Diagnostic Scripts
**Scripts**:
- `check_demo_highlighting.py` - Validates highlighting compliance against enrichment rules
- `check_demo_status.py` - Checks DEMO anchor status and link counts

**Purpose**: Used to diagnose and verify the fixes. Kept in archive for reference.

## Production Code Changes Made

These changes were integrated into production code:

1. **`src/analysis/enrich_articles.py`**
   - Changed `TIER3_CATEGORY = 'News & Media'`

2. **`src/analysis/analyze_articles.py`**
   - Changed `CATEGORIES_TO_FILTER = ['News & Media', 'Misc. Research']`
   - Added support for `'chroma_doc'` component type (for HyDE anchors)

3. **`src/delivery/config.py`**
   - Updated delivery config: `"categories": ["News & Media", ...]`

## Known Issues (Not Fixed)

### Enrichment is Article-Based, Not Link-Based
**Issue**: The enrichment engine (`src/analysis/enrich_articles.py`) processes articles where `enrichment_processed_at IS NULL`. If new semantic anchors are added to already-enriched articles, their article-anchor links won't be processed.

**Impact**: Edge case - only affects scenarios where:
1. Articles are analyzed and enriched
2. New semantic anchors are added later
3. Articles are re-analyzed (creating new links)
4. Enrichment runs but skips those articles

**Workaround**: Manually reset `enrichment_processed_at` for affected articles or use the fix scripts in this archive.

**Proper Fix (Future)**: Modify `load_data_to_process()` in `enrich_articles.py` to select links where `is_anchor_highlight IS NULL` instead of articles where `enrichment_processed_at IS NULL`. This makes enrichment link-based instead of article-based.

## Files in This Archive

- `fix_demo_enrichment.py` - One-time fix for DEMO enrichment bug
- `fix_news_media_enrichment.py` - One-time fix for News & Media category
- `check_demo_highlighting.py` - Diagnostic tool for highlighting compliance
- `check_demo_status.py` - Diagnostic tool for DEMO anchor status
- `README.md` - This file

## Related Production Scripts

These scripts remain in the main `scripts/` directory:

- `setup_demo_anchors.py` - Creates HyDE-based semantic anchors
- `reanalyze_for_demo.py` - Re-analyzes articles for specific time periods
- `demo_cleanup.py` - Production utilities (normalized view, category updates)
- `explore_highlights.py` - Analyzes highlighting patterns (utility)

## Session Notes

For complete session details and context, see: `session_notes_2025_11_30.md` in project root.
