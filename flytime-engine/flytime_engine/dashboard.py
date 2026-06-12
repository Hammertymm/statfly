"""Simple HTTP analytics dashboard — no external dependencies."""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

from .analytics import Analytics
from .db import Database

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>FlyTime Data Engine</title>
<style>
  :root { --bg:#0d1117; --card:#161b22; --text:#e6edf3; --muted:#8b949e;
          --accent:#58a6ff; --green:#3fb950; --yellow:#d29922; --blue:#79c0ff; --red:#f85149; }
  * { box-sizing:border-box; margin:0; padding:0; }
  body { font-family:system-ui,sans-serif; background:var(--bg); color:var(--text);
         padding:1.5rem; line-height:1.5; }
  h1 { font-size:1.4rem; margin-bottom:.25rem; }
  .sub { color:var(--muted); font-size:.85rem; margin-bottom:1.5rem; }
  .grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(280px,1fr)); gap:1rem; }
  .card { background:var(--card); border:1px solid #30363d; border-radius:8px; padding:1rem; }
  .card h2 { font-size:.95rem; color:var(--accent); margin-bottom:.75rem; }
  .stat { display:flex; justify-content:space-between; padding:.3rem 0;
          border-bottom:1px solid #21262d; font-size:.85rem; }
  .stat:last-child { border:none; }
  .val { font-weight:600; }
  .y { color:var(--yellow); } .g { color:var(--green); }
  .b { color:var(--blue); } .r { color:var(--red); }
  table { width:100%; border-collapse:collapse; font-size:.8rem; }
  th,td { text-align:left; padding:.35rem .5rem; border-bottom:1px solid #21262d; }
  th { color:var(--muted); font-weight:500; }
  .refresh { margin-top:1rem; font-size:.8rem; color:var(--muted); }
  a { color:var(--accent); }
</style>
</head>
<body>
<h1>FlyTime Data Engine</h1>
<p class="sub">Continuous match data collection &amp; threshold learning</p>
<div id="app">Loading...</div>
<p class="refresh">Auto-refreshes every 60s · <a href="/api/report">JSON API</a></p>
<script>
async function load() {
  const r = await fetch('/api/report');
  const d = await r.json();
  const h = d.health || {};
  const mc = h.match_counts || {};
  const fc = h.fly_counts || {};
  const lo = d.league_overview || [];
  const bf = (d.blue_fly_analysis || {}).overall || {};
  const fr = (d.formula_analysis || {}).formula_rankings || [];

  let leagueRows = lo.slice(0, 20).map(l =>
    `<tr><td>${l.league||l.label}</td><td>${l.current_threshold??l.current_threshold??'-'}</td>
     <td>${l.recommended_threshold??'-'}</td><td class="y">${l.yellow_flies??0}</td>
     <td class="r">${l.red_flies??0}</td><td>${(l.conversion_pct??0).toFixed?.(1)??l.conversion_pct??0}%</td></tr>`
  ).join('');

  let formulaRows = fr.map(f =>
    `<tr><td>${f.formula_version}</td><td>${f.avg_conversion_pct}%</td>
     <td>${f.total_yellow}</td><td>${f.leagues_tested}</td></tr>`
  ).join('');

  document.getElementById('app').innerHTML = `
  <div class="grid">
    <div class="card"><h2>Service Health</h2>
      <div class="stat"><span>Status</span><span class="val">${h.status}</span></div>
      <div class="stat"><span>Last poll</span><span>${h.last_poll_at||'never'}</span></div>
      <div class="stat"><span>Matches</span><span>${mc.total||0}</span></div>
      <div class="stat"><span>Live</span><span class="g">${mc.live||0}</span></div>
    </div>
    <div class="card"><h2>Fly Counts</h2>
      <div class="stat"><span>Yellow</span><span class="y val">${fc.yellow||0}</span></div>
      <div class="stat"><span>Green</span><span class="g val">${fc.green||0}</span></div>
      <div class="stat"><span>Blue</span><span class="b val">${fc.blue||0}</span></div>
      <div class="stat"><span>Red</span><span class="r val">${fc.red||0}</span></div>
    </div>
    <div class="card"><h2>Blue Fly</h2>
      <div class="stat"><span>Total</span><span class="b val">${bf.total_blue_flies||0}</span></div>
      <div class="stat"><span>Became Red</span><span class="r val">${bf.became_red_fly||0}</span></div>
      <div class="stat"><span>Conversion</span><span>${bf.conversion_pct||0}%</span></div>
    </div>
  </div>
  <div class="card" style="margin-top:1rem"><h2>League Overview</h2>
    <table><tr><th>League</th><th>Thr</th><th>Rec</th><th>Y</th><th>R</th><th>Conv%</th></tr>
    ${leagueRows||'<tr><td colspan=6>No data — run backfill first</td></tr>'}</table>
  </div>
  <div class="card" style="margin-top:1rem"><h2>Formula Rankings</h2>
    <table><tr><th>Version</th><th>Avg Conv%</th><th>Yellow</th><th>Leagues</th></tr>
    ${formulaRows||'<tr><td colspan=4>Run analyze after backfill</td></tr>'}</table>
  </div>`;
}
load(); setInterval(load, 60000);
</script>
</body>
</html>"""


def create_handler(analytics: Analytics):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass  # quiet

        def do_GET(self):
            parsed = urlparse(self.path)
            if parsed.path in ("/", "/dashboard"):
                self._html(DASHBOARD_HTML)
            elif parsed.path == "/api/report":
                self._json(analytics.full_report())
            elif parsed.path == "/api/health":
                self._json(analytics.service_health())
            elif parsed.path == "/api/leagues":
                self._json(analytics.league_overview())
            elif parsed.path == "/api/blue-fly":
                self._json(analytics.blue_fly_analysis())
            elif parsed.path == "/api/formulas":
                self._json(analytics.formula_analysis())
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


def run_dashboard(db: Database, host: str = "127.0.0.1", port: int = 8787) -> None:
    analytics = Analytics(db)
    handler = create_handler(analytics)
    server = HTTPServer((host, port), handler)
    print(f"Dashboard: http://{host}:{port}/", flush=True)
    server.serve_forever()
