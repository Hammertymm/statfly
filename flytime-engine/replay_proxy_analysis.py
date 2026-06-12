#!/usr/bin/env python3
"""Compare final-margin proxy vs terminal-state isFlyTime() on backfilled matches.

Historical ESPN scoreboards only provide final period/clock — not in-game trajectories.
This script quantifies three labels per finished match:

  proxy_red     — abs(home-away) <= close_margin (current research ground truth)
  terminal_green — is_flytime_live() using final period/clock/scores from ESPN
  yellow        — FlyTime v1 score >= league threshold

Usage:
  cd scorefly/flytime-engine
  python replay_proxy_analysis.py
  python replay_proxy_analysis.py --league NRL --export report.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from flytime_engine.config import LEAGUES, get_league
from flytime_engine.db import Database
from flytime_engine.flytime import FlyTimeEngine, is_flytime_live, retroactive_flytime_from_final
from flytime_engine.espn import ParsedMatch


def find_league(name: str):
    name_upper = name.upper()
    for lg in LEAGUES:
        if lg.label.upper() == name_upper or (lg.tag and lg.tag.upper() == name_upper):
            return lg
        if lg.league_code.upper() == name_upper:
            return lg
    return None


def row_to_match(row, sport: str, league_code: str) -> ParsedMatch:
    return ParsedMatch(
        espn_event_id=row["espn_event_id"],
        sport=sport,
        league_code=league_code,
        home_team=row["home_team"],
        away_team=row["away_team"],
        home_team_id=row["home_team_id"] or "",
        away_team_id=row["away_team_id"] or "",
        status="finished",
        scheduled_at=row["scheduled_at"] or "",
        home_score=row["home_score"] or 0,
        away_score=row["away_score"] or 0,
        period=row["period"] or 0,
        clock_raw=row["clock_raw"] or "",
        clock_sec=row["clock_sec"] or 0,
    )


def analyze_league(db: Database, engine: FlyTimeEngine, league_tag: str | None) -> list[dict]:
    results = []
    leagues = LEAGUES if not league_tag else [find_league(league_tag)]
    leagues = [lg for lg in leagues if lg]

    for lg in leagues:
        if not lg.flytime_file:
            continue

        rows = db.query_all(
            """SELECT m.espn_event_id, m.home_team, m.away_team, m.home_score, m.away_score,
                      m.home_team_id, m.away_team_id, m.scheduled_at,
                      ls.period, ls.clock_raw, ls.clock_sec
               FROM matches m
               JOIN leagues l ON l.id = m.league_id
               LEFT JOIN live_snapshots ls ON ls.match_id = m.id
               WHERE l.sport=? AND l.league_code=? AND m.status='finished'
                 AND m.home_score IS NOT NULL AND m.away_score IS NOT NULL""",
            (lg.sport, lg.league_code),
        )

        if not rows:
            # Fall back without snapshots — terminal state unavailable
            rows = db.query_all(
                """SELECT m.espn_event_id, m.home_team, m.away_team, m.home_score, m.away_score,
                          m.home_team_id, m.away_team_id, m.scheduled_at,
                          NULL as period, NULL as clock_raw, NULL as clock_sec
                   FROM matches m
                   JOIN leagues l ON l.id = m.league_id
                   WHERE l.sport=? AND l.league_code=? AND m.status='finished'
                     AND m.home_score IS NOT NULL AND m.away_score IS NOT NULL""",
                (lg.sport, lg.league_code),
            )

        total = len(rows)
        proxy = terminal = yellow = both = proxy_only = terminal_only = yellow_hit_proxy = 0

        for row in rows:
            hs, as_ = row["home_score"], row["away_score"]
            proxy_red = retroactive_flytime_from_final(hs, as_, lg.close_margin)

            pm = row_to_match(row, lg.sport, lg.league_code)
            term_green = is_flytime_live(pm)

            ft = engine.score_for_league(pm, lg)
            is_yellow = ft.is_yellow if ft.score is not None else False

            if proxy_red:
                proxy += 1
            if term_green:
                terminal += 1
            if is_yellow:
                yellow += 1
            if proxy_red and term_green:
                both += 1
            if proxy_red and not term_green:
                proxy_only += 1
            if term_green and not proxy_red:
                terminal_only += 1
            if is_yellow and proxy_red:
                yellow_hit_proxy += 1

        proxy_rate = round(100 * proxy / total, 2) if total else 0
        terminal_rate = round(100 * terminal / total, 2) if total else 0
        yellow_rate = round(100 * yellow / total, 2) if total else 0
        mismatch = round(100 * (proxy - both) / max(proxy, 1), 2) if proxy else 0

        results.append({
            "league": lg.label,
            "tag": lg.tag,
            "sport": lg.sport,
            "close_margin": lg.close_margin,
            "threshold": lg.threshold,
            "games_total": total,
            "proxy_red_count": proxy,
            "proxy_red_rate_pct": proxy_rate,
            "terminal_green_count": terminal,
            "terminal_green_rate_pct": terminal_rate,
            "yellow_count": yellow,
            "yellow_rate_pct": yellow_rate,
            "proxy_and_terminal": both,
            "proxy_only_not_terminal": proxy_only,
            "terminal_only_not_proxy": terminal_only,
            "proxy_mismatch_pct": mismatch,
            "yellow_to_proxy_conversion_pct": round(100 * yellow_hit_proxy / max(yellow, 1), 2),
            "note": (
                "terminal_green uses final ESPN period/clock; often 0:00 at FT so "
                "isFlyTime clock rules (c>0) rarely fire. True replay needs live_snapshots."
            ),
        })

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Proxy vs terminal FlyTime label analysis")
    parser.add_argument("--league", help="League tag or name (default: pilot five)")
    parser.add_argument("--export", help="JSON export path")
    parser.add_argument("--pilot", action="store_true", help="NRL AFL EPL NFL NBA only")
    args = parser.parse_args()

    db = Database()
    engine = FlyTimeEngine()
    engine.load_all(LEAGUES)

    if args.pilot:
        tags = ["NRL", "AFL", "EPL", "NFL", "NBA"]
        all_results = []
        for tag in tags:
            all_results.extend(analyze_league(db, engine, tag))
    elif args.league:
        all_results = analyze_league(db, engine, args.league)
    else:
        all_results = analyze_league(db, engine, None)

    print("\n=== FlyTime Proxy vs Terminal Analysis ===\n")
    for r in all_results:
        print(f"{r['tag']:5} {r['league']:22} games={r['games_total']:4}  "
              f"proxy_red={r['proxy_red_rate_pct']:5.1f}%  "
              f"terminal={r['terminal_green_rate_pct']:5.1f}%  "
              f"yellow={r['yellow_rate_pct']:5.1f}%  "
              f"mismatch={r['proxy_mismatch_pct']:5.1f}%")

    out = {"leagues": all_results, "methodology": {
        "proxy_red": "abs(home-away) <= close_margin",
        "terminal_green": "is_flytime_live() at final ESPN state",
        "limitation": "No in-game trajectory without live_snapshots or play-by-play",
    }}

    export_path = args.export or str(
        Path(__file__).resolve().parent.parent.parent
        / "_research" / "FlyTime-Intelligence" / "replay-proxy-analysis.json"
    )
    Path(export_path).parent.mkdir(parents=True, exist_ok=True)
    Path(export_path).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nExported to {export_path}")


if __name__ == "__main__":
    main()
