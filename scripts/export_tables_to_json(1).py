import sqlite3
import json

conn = sqlite3.connect("data/scorefly.db")
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

tables = [
    "matchup_ratings",
    "matchup_close_rates",
    "form_strengths",
    "team_margin_ratings"
]

output = {}

for table in tables:
    cursor.execute(f"SELECT * FROM {table}")
    output[table] = [dict(row) for row in cursor.fetchall()]

with open("scorefly_research_tables.json", "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2)

print("Created: scorefly_research_tables.json")
