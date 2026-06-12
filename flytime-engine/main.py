#!/usr/bin/env python3
"""FlyTime Data Engine CLI.

Usage:
  python main.py init                          # Create database schema
  python main.py backfill [--league NFL] [--force]
  python main.py collect                       # Single poll cycle
  python main.py analyze                       # Run threshold + formula analysis
  python main.py report [--export path.json]
  python main.py blue-fly                      # Blue fly analysis
  python main.py backtest [--league NFL] [--formula v1]
  python main.py serve                         # Start always-on collection service
  python main.py dashboard [--port 8787]       # Analytics dashboard
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from flytime_engine.analytics import Analytics
from flytime_engine.blue_fly import BlueFlyAnalyzer
from flytime_engine.collector import CollectionService, MatchCollector
from flytime_engine.config import DEFAULT_DB_PATH, LEAGUES, get_league
from flytime_engine.db import Database
from flytime_engine.flytime import FlyTimeEngine
from flytime_engine.formula_testing import FormulaTester
from flytime_engine.threshold_engine import ThresholdEngine


def find_league(name: str):
    name_upper = name.upper()
    for lg in LEAGUES:
        if lg.label.upper() == name_upper or (lg.tag and lg.tag.upper() == name_upper):
            return lg
        if lg.league_code.upper() == name_upper:
            return lg
    return None


def cmd_init(db: Database) -> None:
    db.init_schema()
    print(f"Database initialized: {db.path}")


def cmd_backfill(db: Database, league_name: str | None, force: bool) -> None:
    engine = FlyTimeEngine()
    engine.load_all(LEAGUES)
    collector = MatchCollector(db, engine)

    if league_name:
        lg = find_league(league_name)
        if not lg:
            print(f"Unknown league: {league_name}")
            sys.exit(1)
        n = collector.backfill_league(lg, force=force)
        print(f"{lg.label}: imported {n} historical matches")
    else:
        print("Backfilling all leagues...")
        results = collector.backfill_all(force=force)
        total = sum(v for v in results.values() if v > 0)
        print(f"\nDone. {total} matches imported across {len(results)} leagues.")


def cmd_collect(db: Database) -> None:
    engine = FlyTimeEngine()
    engine.load_all(LEAGUES)
    collector = MatchCollector(db, engine)
    results = collector.poll_all()
    live = sum(1 for v in results.values() if v > 0)
    print(f"Poll complete. {live} leagues fetched.")


def cmd_analyze(db: Database) -> None:
    engine = FlyTimeEngine()
    engine.load_all(LEAGUES)
    threshold = ThresholdEngine(db, engine)
    formula = FormulaTester(db, engine)

    print("Running threshold evaluation...")
    results = threshold.evaluate_all()
    print(f"Evaluated {len(results)} leagues.")

    print("\nRunning formula backtests...")
    rankings = formula.rank_formulas()
    for r in rankings:
        print(f"  {r['formula_version']:12s}  avg_conv={r['avg_conversion_pct']}%  "
              f"yellow={r['total_yellow']}")

    Analytics(db).print_summary()


def cmd_report(db: Database, export: str | None) -> None:
    analytics = Analytics(db)
    analytics.print_summary()
    if export:
        path = Path(export)
        analytics.export_report(path)
        print(f"\nReport exported to {path}")


def cmd_blue_fly(db: Database) -> None:
    report = BlueFlyAnalyzer(db).full_report()
    import json
    print(json.dumps(report, indent=2, default=str))


def cmd_backtest(db: Database, league_name: str | None, formula: str) -> None:
    engine = FlyTimeEngine()
    engine.load_all(LEAGUES)
    tester = FormulaTester(db, engine)

    if league_name:
        lg = find_league(league_name)
        if not lg:
            print(f"Unknown league: {league_name}")
            sys.exit(1)
        results = tester.compare_formulas(lg)
    else:
        results = tester.compare_all_leagues(formula)

    import json
    print(json.dumps(results, indent=2, default=str))


def cmd_serve(db: Database) -> None:
    service = CollectionService(db)
    try:
        service.start()
    except KeyboardInterrupt:
        service.stop()


def cmd_dashboard(db: Database, port: int) -> None:
    from flytime_engine.dashboard import run_dashboard
    run_dashboard(db, port=port)


def main():
    parser = argparse.ArgumentParser(description="FlyTime Data Engine")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="Database path")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="Initialize database")

    p_backfill = sub.add_parser("backfill", help="Historical backfill")
    p_backfill.add_argument("--league", help="Single league (e.g. NFL, NRL)")
    p_backfill.add_argument("--force", action="store_true", help="Re-run completed ranges")

    sub.add_parser("collect", help="Single live poll cycle")
    sub.add_parser("analyze", help="Run threshold + formula analysis")
    sub.add_parser("serve", help="Start always-on collection service")

    p_report = sub.add_parser("report", help="Print analytics summary")
    p_report.add_argument("--export", help="Export JSON report to file")

    sub.add_parser("blue-fly", help="Blue fly analysis report")

    p_bt = sub.add_parser("backtest", help="Formula backtesting")
    p_bt.add_argument("--league", help="Single league")
    p_bt.add_argument("--formula", default="v1")

    p_dash = sub.add_parser("dashboard", help="Analytics dashboard")
    p_dash.add_argument("--port", type=int, default=8787)

    args = parser.parse_args()
    db = Database(Path(args.db))

    if args.command == "init":
        cmd_init(db)
    elif args.command == "backfill":
        cmd_backfill(db, getattr(args, "league", None), getattr(args, "force", False))
    elif args.command == "collect":
        cmd_collect(db)
    elif args.command == "analyze":
        cmd_analyze(db)
    elif args.command == "report":
        cmd_report(db, getattr(args, "export", None))
    elif args.command == "blue-fly":
        cmd_blue_fly(db)
    elif args.command == "backtest":
        cmd_backtest(db, getattr(args, "league", None), args.formula)
    elif args.command == "serve":
        cmd_serve(db)
    elif args.command == "dashboard":
        cmd_dashboard(db, args.port)


if __name__ == "__main__":
    main()
