# FlyTime Data Engine — Fly Intelligence Platform

Standalone background service for **24/7 cloud match monitoring**, threshold learning, Blue Fly analysis, and formula testing across all ScoreFly leagues.

## Fly Intelligence Platform (cloud)

Run collector + dashboard + nightly analysis in one process:

```bash
cd scorefly/flytime-engine
python main.py init
python run_platform.py
# → http://localhost:8787
```

Or with Docker (see [CLOUD-DEPLOY.md](./CLOUD-DEPLOY.md)):

```bash
cd scorefly
docker compose up -d
```

## Quick Start (local)

This engine is the **single source of truth** for FlyTime intelligence. The main ScoreFly PWA can eventually consume threshold recommendations from this service via its JSON API.

## Quick Start

```bash
cd scorefly/flytime-engine

# 1. Initialize database
python main.py init

# 2. Backfill historical data (all 47 leagues — takes a while)
python main.py backfill

# Or one league:
python main.py backfill --league NRL

# 3. Run analysis on backfilled data
python main.py analyze

# 4. Start always-on live collection
python main.py serve

# 5. Open analytics dashboard (separate terminal)
python main.py dashboard
# → http://127.0.0.1:8787/
```

## Architecture

```
ESPN API
    ↓
collector.py (backfill + live polling)
    ↓
SQLite database (flytime_engine/data/flytime_engine.db)
    ├── matches, match_events, live_snapshots
    ├── fly_events, blue_fly_events
    ├── threshold_history, league_metrics
    └── prediction_results, historical_backtests
    ↓
threshold_engine.py  →  recommended thresholds
blue_fly.py          →  yellow→green→red analysis
formula_testing.py   →  v1/v2/v3/experimental comparison
    ↓
dashboard.py / main.py report
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `init` | Create database schema and seed leagues/formulas |
| `backfill` | Import historical ESPN match data (incremental, no duplicates) |
| `collect` | Single live poll cycle |
| `serve` | Always-on collection service (12s/8s/60s adaptive polling) |
| `platform` | Fly Intelligence Platform — collector + dashboard + nightly jobs |
| `analyze` | Run threshold + formula evaluation |
| `report` | Print analytics summary (`--export report.json`) |
| `blue-fly` | Blue Fly behaviour analysis |
| `backtest` | Formula replay testing (`--league NFL --formula v1`) |
| `dashboard` | HTTP analytics dashboard on port 8787 |

## Database Tables

- **matches** — all fixtures with fly outcome flags
- **match_events** — timeline (status, score, yellow/green/blue/red events)
- **live_snapshots** — poll-time state for live matches
- **fly_events** — fly lifecycle records
- **blue_fly_events** — yellow→green analysis with outcomes
- **threshold_history** — threshold performance over time
- **formula_versions** — v1 (production), v2, v3, experimental
- **league_metrics** — rolling aggregates per league
- **prediction_results** — per-match predictions across formulas
- **historical_backtests** — replay test results

## FlyTime Logic

Mirrors `scorefly/index.html`:

- **Yellow fly**: FlyTime v1 score ≥ league threshold (45 leagues with JSON tables)
- **Green fly**: `isFlyTime()` live detection (sport-specific period/clock/margin rules)
- **Blue fly**: Yellow predicted AND green achieved
- **Red fly**: Match entered green fly and finished

### Formula versions

| Version | Weights |
|---------|---------|
| v1 (production) | close 35%, form 25%, margin 25%, matchup 15% |
| v2 | close 45%, form 20%, margin 20%, matchup 15% |
| v3 | close 25%, form 35%, margin 25%, matchup 15% |
| experimental | close 25%, form 20%, margin 20%, matchup 35% |

### Threshold types tested

- **Fixed**: NRL=85, AFL=75, etc.
- **Percentile**: top 10%, 15%, 20%, 25%, 30%
- **Dynamic**: auto-adjusted from conversion rate

## API Endpoints (dashboard)

| Endpoint | Data |
|----------|------|
| `GET /` | Fly Intelligence Platform HTML dashboard |
| `GET /api/report` | Full analytics JSON |
| `GET /api/health` | Service health |
| `GET /api/live` | Live/upcoming matches with FlyScore |
| `GET /api/flytime` | Matches currently in FlyTime |
| `GET /api/events` | Recent fly triggers |
| `GET /api/intelligence` | Accuracy, false positives/negatives, insights |
| `GET /api/recommendations` | Per-league threshold recommendations |
| `GET /api/research` | Filterable historical data |
| `GET /api/export` | CSV download |
| `GET /api/leagues` | League overview |
| `GET /api/blue-fly` | Blue fly analysis |
| `GET /api/formulas` | Formula rankings |

## Running as a Background Service

### Windows (Task Scheduler)

Create a task that runs at startup:
```
python C:\Projects\ScoreFly\scorefly\flytime-engine\run_service.py
```

### Linux (systemd)

```ini
[Unit]
Description=FlyTime Data Engine
After=network.target

[Service]
Type=simple
WorkingDirectory=/path/to/scorefly/flytime-engine
ExecStart=/usr/bin/python3 run_service.py
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
```

## Integration with ScoreFly PWA

Fetch `GET /api/recommendations` from your cloud platform for per-league thresholds. Today, thresholds are still in `index.html` `FLY_V1_REGISTRY` — apply engine recommendations manually or via a sync script.

See [CLOUD-DEPLOY.md](./CLOUD-DEPLOY.md) for full deployment guide.

## Notes

- Historical backfill uses **final-margin proxy** for red flies (same as offline `calibrate_flytime.py`). Live collection uses true `isFlyTime()` rules.
- Cricket feeds (BBL, IPL, ICC) have no v1 JSON tables — live-only FlyTime.
- Database defaults to `flytime-engine/data/flytime_engine.db` (gitignored).
- No external Python dependencies — stdlib only.
