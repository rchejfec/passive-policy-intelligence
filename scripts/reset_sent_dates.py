"""
Reset newsletter_sent_at dates for articles linked to DEMO anchors
This allows them to be resent in the next digest.
"""
import sys
import codecs
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

from src.management.db_utils import get_db_connection

conn = get_db_connection()
cur = conn.cursor()

# Reset newsletter_sent_at for articles linked to DEMO anchors
sql = """
UPDATE articles
SET newsletter_sent_at = NULL
WHERE id IN (
    SELECT DISTINCT a.id
    FROM articles a
    JOIN article_anchor_links aal ON a.id = aal.article_id
    JOIN semantic_anchors sa ON aal.anchor_id = sa.id
    WHERE sa.name LIKE 'DEMO%'
    AND a.created_at > NOW() - INTERVAL '60 HOURS'
)
"""

cur.execute(sql)
rows_updated = cur.rowcount
conn.commit()

print(f"✅ Reset newsletter_sent_at for {rows_updated} articles linked to DEMO anchors")
print("These articles will now be included in the next digest.")

cur.close()
conn.close()
