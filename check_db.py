import sqlite3
import os

db_path = "src/loto.db"
if not os.path.exists(db_path):
    print(f"File {db_path} not found.")
else:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    tables = ["sessions", "stats", "last_results"]
    for table in tables:
        try:
            cur.execute(f"SELECT count(*) FROM {table}")
            count = cur.fetchone()[0]
            print(f"Table '{table}': {count} rows")
        except sqlite3.OperationalError as e:
            print(f"Table '{table}' error: {e}")
            
    conn.close()
