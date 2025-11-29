# Data Cleanup Scripts

These scripts safely remove test data from the database before production deployment.

## Overview

Two cleanup tasks:
1. **Remove test anchors** - Delete all anchors NOT starting with "PROG:" and their associated data
2. **Remove duplicates** - Delete duplicate article-anchor links (same title + same anchor)

## Safety Features

- ✅ **Dry-run by default** - Preview what will be deleted before execution
- ✅ **Confirmation required** - Must type 'DELETE' to confirm
- ✅ **Transaction support** - Changes rolled back on error
- ✅ **Preserves data** - Keeps PROG: anchors and highest-scored links
- ✅ **Foreign key safe** - Deletes in correct order

## Usage

### Step 1: Preview Test Anchor Cleanup

```bash
python scripts/cleanup_test_anchors.py
```

This shows:
- Which anchors will be deleted (NOT starting with "PROG:")
- How many article_anchor_links will be removed
- How many anchor_components will be removed
- How many subscriptions will be removed
- Which PROG: anchors will be preserved

### Step 2: Preview Duplicate Cleanup

```bash
python scripts/cleanup_duplicate_links.py
```

This shows:
- Duplicate article titles within each anchor
- Which specific link IDs will be deleted
- Which link will be kept (highest similarity score)

### Step 3: Execute Test Anchor Cleanup

```bash
python scripts/cleanup_test_anchors.py --execute
```

**Confirmation required:** Type `DELETE` when prompted.

This removes:
- All semantic_anchors NOT starting with "PROG:"
- Their anchor_components
- Their article_anchor_links
- Their subscriptions

**Preserves:**
- All PROG: anchors
- All articles (they're still valuable data)
- All article embeddings in ChromaDB

### Step 4: Execute Duplicate Cleanup

```bash
python scripts/cleanup_duplicate_links.py --execute
```

**Confirmation required:** Type `DELETE` when prompted.

This removes:
- Duplicate links where same article title appears multiple times for same anchor
- Keeps the link with the HIGHEST similarity score

## What Gets Deleted

### Test Anchor Cleanup
```
Before:
semantic_anchors:
  - PROG: Example Program (KEEP)
  - TAG: Test Tag (test2) (DELETE)
  - Complex: Test Anchor A (test2) (DELETE)

After:
semantic_anchors:
  - PROG: Example Program (KEEP)
```

### Duplicate Link Cleanup
```
Before:
Anchor: PROG: Example Program
  - Article: "Policy Update 2025" (Score: 0.85) → KEEP
  - Article: "Policy Update 2025" (Score: 0.72) → DELETE (duplicate, lower score)
  - Article: "Other Article" (Score: 0.90) → KEEP (unique)

After:
Anchor: PROG: Example Program
  - Article: "Policy Update 2025" (Score: 0.85) → KEPT
  - Article: "Other Article" (Score: 0.90) → KEPT
```

## Recommended Order

1. Run test anchor cleanup first (removes bulk of test data)
2. Run duplicate cleanup second (cleans remaining duplicates)

## Verification

After running both scripts:

### Check anchor count:
```sql
SELECT
    COUNT(*) FILTER (WHERE name LIKE 'PROG:%') as prog_anchors,
    COUNT(*) FILTER (WHERE name NOT LIKE 'PROG:%') as test_anchors,
    COUNT(*) as total_anchors
FROM semantic_anchors;
```

### Check for duplicates:
```sql
SELECT anchor_id, a.title, COUNT(*) as dup_count
FROM article_anchor_links aal
JOIN articles a ON aal.article_id = a.id
GROUP BY anchor_id, a.title
HAVING COUNT(*) > 1;
```

Should return 0 rows.

## Rollback

If you need to undo changes (only works if script is still running):
1. Press Ctrl+C before typing 'DELETE'
2. Or let script fail - it will auto-rollback

After commit, changes are permanent. Keep database backups!

## Notes

- **ChromaDB**: Article embeddings remain in ChromaDB (safe to keep, or clean manually)
- **Articles table**: No articles are deleted, only links to test anchors
- **Performance**: Scripts use indexed queries and should be fast
- **Idempotent**: Safe to run multiple times (will find no data to delete)

## Troubleshooting

### "No test anchors found"
- All anchors start with "PROG:" already - database is clean!

### "Failed to connect to database"
- Check that `.env` file exists with DATABASE_URL
- Verify database is accessible
- Check credentials

### "No duplicate links found"
- Database is already clean!
- Or all duplicates already removed

## Example Output

### Dry Run (Preview):
```
====================================================================================
TEST ANCHOR CLEANUP SCRIPT
====================================================================================

Mode: DRY RUN (preview only)

Found 15 test anchors to delete:
  [23] TAG: AI governance (test2)
  [24] TAG: Cybersecurity (test2)
  ...

Records that will be deleted:
  - 15 semantic_anchors
  - 45 anchor_components
  - 1,234 article_anchor_links
  - 8 subscriptions

✓ 5 PROG: anchors will be PRESERVED
```

### Execute (Real):
```
Type 'DELETE' to confirm deletion: DELETE

Deleting from PostgreSQL...
  - Deleting subscriptions... (8 deleted)
  - Deleting article_anchor_links... (1,234 deleted)
  - Deleting anchor_components... (45 deleted)
  - Deleting semantic_anchors... (15 deleted)

✓ PostgreSQL cleanup complete!
✓ Changes committed to database
```
