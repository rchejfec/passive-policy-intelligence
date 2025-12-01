import sys
import codecs
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

from src.management.db_utils import get_db_connection
import pandas as pd

conn = get_db_connection()
df = pd.read_sql_query("SELECT id, name, description FROM semantic_anchors WHERE name LIKE 'DEMO%' ORDER BY name", conn)
print(df.to_string(index=False))
conn.close()
