import sqlite3
from pathlib import Path

conn = sqlite3.connect(Path(__file__).parent / "data" / "scorefly.db")
c = conn.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
print("tables:", [r[0] for r in c.fetchall()])
for t in ["matches", "historical_matches"]:
    try:
        c.execute(f"SELECT COUNT(*) FROM {t}")
        print(t, c.fetchone()[0])
    except Exception as e:
        print(t, e)
conn.close()
