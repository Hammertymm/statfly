"""Fly Intelligence Platform HTTP dashboard and API."""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .analytics import Analytics
from .db import Database
from .intelligence import FlyIntelligence

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


def create_handler(analytics: Analytics, intelligence: FlyIntelligence):
    dashboard_html = (STATIC_DIR / "dashboard.html").read_text(encoding="utf-8")

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass

        def do_GET(self):
            parsed = urlparse(self.path)
            qs = parse_qs(parsed.query)

            routes = {
                "/": lambda: self._html(dashboard_html),
                "/dashboard": lambda: self._html(dashboard_html),
                "/api/report": lambda: self._json(analytics.full_report()),
                "/api/health": lambda: self._json(analytics.service_health()),
                "/api/leagues": lambda: self._json(analytics.league_overview()),
                "/api/blue-fly": lambda: self._json(analytics.blue_fly_analysis()),
                "/api/formulas": lambda: self._json(analytics.formula_analysis()),
                "/api/recommendations": lambda: self._json(analytics.recommendations()),
                "/api/intelligence": lambda: self._json(intelligence.full_intelligence_report()),
                "/api/live": lambda: self._json(analytics.live_matches()),
                "/api/flytime": lambda: self._json(analytics.flytime_matches()),
                "/api/events": lambda: self._json(
                    analytics.recent_events(int(qs.get("limit", ["40"])[0]))
                ),
                "/api/conversion": lambda: self._json(analytics.conversion_rates()),
                "/api/trends": lambda: self._json(
                    analytics.historical_trends(int(qs.get("days", ["30"])[0]))
                ),
                "/api/sports": lambda: self._json(analytics.sport_breakdown()),
                "/api/formulas/compare": lambda: self._json(
                    analytics.compare_formulas(qs.get("league", [None])[0])
                ),
            }

            if parsed.path == "/api/research":
                self._json(analytics.research_query(
                    league=qs.get("league", [None])[0] or None,
                    sport=qs.get("sport", [None])[0] or None,
                    status=qs.get("status", [None])[0] or None,
                    had_yellow=_bool_qs(qs, "had_yellow"),
                    had_green=_bool_qs(qs, "had_green"),
                    formula_version=qs.get("formula", ["v1"])[0],
                    limit=int(qs.get("limit", ["200"])[0]),
                ))
                return

            if parsed.path == "/api/export":
                rows = analytics.research_query(
                    league=qs.get("league", [None])[0] or None,
                    sport=qs.get("sport", [None])[0] or None,
                    status=qs.get("status", [None])[0] or None,
                    had_yellow=_bool_qs(qs, "had_yellow"),
                    had_green=_bool_qs(qs, "had_green"),
                    formula_version=qs.get("formula", ["v1"])[0],
                    limit=int(qs.get("limit", ["5000"])[0]),
                )
                csv_data = analytics.export_csv(rows)
                self.send_response(200)
                self.send_header("Content-Type", "text/csv; charset=utf-8")
                self.send_header("Content-Disposition", 'attachment; filename="flytime-export.csv"')
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(csv_data.encode())
                return

            if parsed.path.startswith("/api/match/"):
                try:
                    match_id = int(parsed.path.split("/")[-1])
                    detail = analytics.match_detail(match_id)
                    if detail:
                        self._json(detail)
                    else:
                        self.send_error(404)
                except ValueError:
                    self.send_error(400)
                return

            handler = routes.get(parsed.path)
            if handler:
                handler()
            else:
                self.send_error(404)

        def _html(self, content: str):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(content.encode())

        def _json(self, data):
            body = json.dumps(data, indent=2, default=str)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body.encode())

    return Handler


def _bool_qs(qs: dict, key: str) -> bool | None:
    val = qs.get(key, [None])[0]
    if val is None or val == "":
        return None
    return val in ("1", "true", "True", "yes")


def run_dashboard(db: Database, host: str = "127.0.0.1", port: int = 8787) -> None:
    analytics = Analytics(db)
    intelligence = FlyIntelligence(db, analytics.engine)
    handler = create_handler(analytics, intelligence)
    server = HTTPServer((host, port), handler)
    print(f"Fly Intelligence Platform: http://{host}:{port}/", flush=True)
    server.serve_forever()
