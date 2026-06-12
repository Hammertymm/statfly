#!/usr/bin/env python3
"""Nightly feature export for ML notebooks and research analysis.

Usage:
  python feature_builder.py
  python feature_builder.py --output ../../_research/FlyTime-Intelligence/features/
  python feature_builder.py --days 90
"""
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from flytime_engine.config import DEFAULT_DB_PATH
from flytime_engine.db import Database


FEATURE_COLUMNS = [
    "match_id", "espn_event_id", "league", "sport", "home_team", "away_team",
    "scheduled_at", "finished_at", "status",
    "final_margin", "home_score", "away_score",
    "had_yellow_fly", "had_live_flytime", "had_blue_fly", "had_red_fly",
    "yellow_score", "threshold", "formula_version",
    "predicted_fly", "actual_fly", "is_hit", "is_false_alarm", "is_miss",
    "snapshot_count", "max_margin", "min_margin", "avg_flyscore_live",
    "event_count", "green_fly_entries",
]


def build_features(db: Database, days: int | None = None) -> list[dict]:
    """Build feature rows from matches + snapshots + predictions."""
    date_filter = ""
    params: tuple = ()
    if days:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
        date_filter = "AND (m.finished_at >= ? OR m.scheduled_at >= ? OR m.status='live')"
        params = (cutoff, cutoff)

    rows = db.query_all(
        f"""SELECT m.id as match_id, m.espn_event_id, l.label as league, l.sport,
                   m.home_team, m.away_team, m.scheduled_at, m.finished_at, m.status,
                   m.final_margin, m.home_score, m.away_score,
                   m.had_yellow_fly, m.had_live_flytime, m.had_blue_fly, m.had_red_fly
            FROM matches m
            JOIN leagues l ON l.id = m.league_id
            WHERE 1=1 {date_filter}
            ORDER BY m.scheduled_at DESC""",
        params,
    )

    features = []
    for row in rows:
        mid = row["match_id"]
        pred = db.query_one(
            """SELECT flytime_score, threshold, formula_version,
                      predicted_fly, actual_fly, is_hit, is_false_alarm, is_miss
               FROM prediction_results WHERE match_id=? AND formula_version='v1'""",
            (mid,),
        )
        snap = db.query_one(
            """SELECT COUNT(*) as cnt,
                      MAX(margin) as max_margin, MIN(margin) as min_margin,
                      AVG(flytime_score) as avg_flyscore
               FROM live_snapshots WHERE match_id=?""",
            (mid,),
        )
        events = db.query_one(
            "SELECT COUNT(*) as cnt FROM match_events WHERE match_id=?", (mid,)
        )
        green_entries = db.query_one(
            """SELECT COUNT(*) as cnt FROM match_events
               WHERE match_id=? AND event_type='green_fly'""",
            (mid,),
        )

        features.append({
            **row,
            "yellow_score": (pred or {}).get("flytime_score"),
            "threshold": (pred or {}).get("threshold"),
            "formula_version": (pred or {}).get("formula_version", "v1"),
            "predicted_fly": (pred or {}).get("predicted_fly", 0),
            "actual_fly": (pred or {}).get("actual_fly", 0),
            "is_hit": (pred or {}).get("is_hit", 0),
            "is_false_alarm": (pred or {}).get("is_false_alarm", 0),
            "is_miss": (pred or {}).get("is_miss", 0),
            "snapshot_count": (snap or {}).get("cnt", 0),
            "max_margin": (snap or {}).get("max_margin"),
            "min_margin": (snap or {}).get("min_margin"),
            "avg_flyscore_live": round((snap or {}).get("avg_flyscore") or 0, 2),
            "event_count": (events or {}).get("cnt", 0),
            "green_fly_entries": (green_entries or {}).get("cnt", 0),
        })

    return features


def export_csv(features: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FEATURE_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(features)


def export_json(features: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(features, indent=2, default=str), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export FlyTime feature dataset")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--output", default=None, help="Output directory")
    parser.add_argument("--days", type=int, default=None, help="Limit to recent N days")
    args = parser.parse_args()

    db = Database(Path(args.db))
    features = build_features(db, days=args.days)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if args.output:
        out_dir = Path(args.output)
    else:
        out_dir = Path(__file__).resolve().parent.parent.parent / "_research" / "FlyTime-Intelligence" / "features"

    csv_path = out_dir / f"{today}.csv"
    json_path = out_dir / f"{today}.json"

    export_csv(features, csv_path)
    export_json(features, json_path)

    print(f"Exported {len(features)} match features:")
    print(f"  CSV:  {csv_path}")
    print(f"  JSON: {json_path}")


if __name__ == "__main__":
    main()
