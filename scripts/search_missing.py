#!/usr/bin/env python3
"""Locate missing team logos via ESPN's global search API."""
from __future__ import annotations

import json
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "team-halo-config.json"
OUT = Path(__file__).resolve().parent / "search-results.txt"

UA = "Mozilla/5.0 (ScoreFly logo finder)"

# Hand-tuned search aliases for teams whose roster name differs from ESPN's.
ALIASES: dict[str, list[str]] = {
    "FC Köln": ["FC Cologne", "1. FC Koln", "Koln"],
    "Mazatlán": ["Mazatlan FC", "Mazatlan"],
    "Yokohama FC": ["Yokohama FC", "Yokohama F Marinos"],
    "Sunrisers Hyderabad": ["Sunrisers Hyderabad", "Hyderabad"],
    "Cape Cobras": ["Cape Cobras", "Western Province"],
    "FeralpiSalo": ["FeralpiSalo", "Feralpisalo"],
    "UCD": ["University College Dublin", "UCD AFC"],
    "Bayonne": ["Aviron Bayonnais", "Bayonne"],
}


def norm(s: str) -> str:
    s = unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]", "", s)


def search(query: str) -> list[dict]:
    q = urllib.parse.quote(query)
    url = f"https://site.web.api.espn.com/apis/common/v3/search?query={q}&limit=20&mode=prefix"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        data = json.loads(urllib.request.urlopen(req, timeout=20).read())
    except Exception as exc:  # noqa: BLE001
        return []
    items = []
    for it in data.get("items", []):
        if it.get("type") == "team" and it.get("sport") in ("soccer", "cricket", "rugby"):
            items.append(it)
    return items


def best_logo(item: dict) -> str:
    for logo in item.get("logos", []):
        rel = logo.get("rel", [])
        if "default" in rel and "dark" not in rel:
            return logo["href"]
    if item.get("logos"):
        return item["logos"][0].get("href", "")
    return ""


def main() -> None:
    data = json.loads(CONFIG.read_text(encoding="utf-8"))
    missing = [t for t in data["teams"] if not t.get("logoUrl")]

    lines: list[str] = [f"Searching {len(missing)} missing teams via ESPN", ""]
    found = 0
    for entry in missing:
        name = entry["names"][0]
        league = entry["league"]
        queries = [name] + ALIASES.get(name, [])
        hit = None
        for q in queries:
            for item in search(q):
                if norm(item.get("displayName", "")) == norm(q) or norm(name) in norm(
                    item.get("displayName", "")
                ) or norm(item.get("displayName", "")) in norm(name):
                    logo = best_logo(item)
                    if logo:
                        hit = (item, logo, q)
                        break
            if hit:
                break
            time.sleep(0.15)
        if hit:
            item, logo, q = hit
            found += 1
            lines.append(
                f"FOUND  {name}  [{league}]  -> {item['displayName']} "
                f"(id {item['id']}, {item.get('league','?')})"
            )
            lines.append(f"       {logo}")
        else:
            lines.append(f"MISS   {name}  [{league}]")
    lines.insert(1, f"Found {found} / {len(missing)}")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    print("\n".join(lines))
    print(f"\nReport: {OUT}")


if __name__ == "__main__":
    main()
