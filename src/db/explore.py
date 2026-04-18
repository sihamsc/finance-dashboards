import pandas as pd
from src.db.connection import get_engine

engine = get_engine()

# find all schemas and tables in the DB
q = """
SELECT table_schema, table_name 
FROM information_schema.tables
WHERE table_type = 'BASE TABLE'
  AND table_schema NOT IN ('pg_catalog', 'information_schema')
ORDER BY table_schema, table_name
"""

df = pd.read_sql(q, engine)
print(df.to_string(index=False))

