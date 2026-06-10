"""Print FLY_V1_REGISTRY entries and sw.js paths from soccer-thresholds.json"""
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
data = json.loads((ROOT / "soccer-thresholds.json").read_text(encoding="utf-8"))

print("// --- paste into FLY_V1_REGISTRY ---")
for row in data:
    key = f"soccer|{row['league_key']}"
    print(f"  '{key}': {{ file: '{row['file']}', threshold: {row['threshold']}, tag: '{row['tag']}' }},")

print("\n// --- paste into sw.js SHELL ---")
for row in data:
    print(f"  './{row['file']}',")
