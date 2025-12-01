"""
Check article-anchor linkages to understand the matching issues
"""
import sys
import codecs
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

from src.management.db_utils import get_db_connection
import pandas as pd

conn = get_db_connection()

# Check what fields exist in article_anchor_links
print("=== Checking article_anchor_links table structure ===")
schema_query = """
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'article_anchor_links'
ORDER BY ordinal_position
"""
schema_df = pd.read_sql_query(schema_query, conn)
print(schema_df.to_string(index=False))
print()

# Check recent article linkages with DEMO anchors
print("=== Recent Article-Anchor Linkages (DEMO) ===")
query = """
SELECT
    a.id,
    a.title,
    sa.name as anchor_name,
    aal.similarity_score,
    a.is_org_highlight
FROM articles a
JOIN article_anchor_links aal ON a.id = aal.article_id
JOIN semantic_anchors sa ON aal.anchor_id = sa.id
WHERE sa.name LIKE 'DEMO%'
AND a.created_at > NOW() - INTERVAL '60 HOURS'
ORDER BY a.created_at DESC, aal.similarity_score DESC
LIMIT 20
"""
df = pd.read_sql_query(query, conn)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.max_colwidth', 80)
print(df.to_string(index=False))

conn.close()
