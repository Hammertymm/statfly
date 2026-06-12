# Fly Intelligence Platform — Cloud Deployment Guide

Run ScoreFly's FlyTime engine 24/7 in the cloud with no dependency on your laptop.

## What it does

The **Fly Intelligence Platform** extends the existing `flytime-engine` to:

- Poll ESPN every 8–60 seconds across all 47 leagues
- Score every match through the FlyScore v1 engine (plus v2/v3/experimental)
- Track yellow, green, blue, and red fly state transitions
- Store live snapshots, events, and prediction outcomes in SQLite
- Run nightly threshold analysis and feature exports
- Serve a web dashboard with Live, Analytics, and Research tabs

## Quick start (Docker)

```bash
cd scorefly

# Build and run (dashboard at http://localhost:8787)
docker compose up -d

# Initialize + backfill historical data (one-time, takes a while)
docker compose exec fly-intelligence python main.py init
docker compose exec fly-intelligence python main.py backfill --league NRL
docker compose exec fly-intelligence python main.py analyze
```

The platform starts collecting live data immediately. Historical backfill improves yellow calibration but is not required for live monitoring.

## Cloud providers

### Oracle Cloud Always Free (recommended — $0/month)

Full step-by-step guide: **[oracle-cloud/README.md](../oracle-cloud/README.md)**

Summary:

1. Create Ampere A1 VM (Ubuntu ARM, 1 OCPU, 6 GB RAM)
2. Open TCP port **8787** in Oracle Security List
3. SSH in and run `bash oracle-cloud/setup-vm.sh`
4. Upload local DB: `oracle-cloud/upload-db.ps1 -VmIp YOUR_IP`

### Railway (paid convenience)

1. Push this repo to GitHub
2. Create a new Railway project → Deploy from GitHub
3. Set root directory to `scorefly` (or repo root if Dockerfile is at root)
4. Add a **Volume** mounted at `/data`
5. Set environment variables:
   - `FLYTIME_DB_PATH=/data/flytime_engine.db`
   - `PORT=8787`
6. Railway auto-detects the Dockerfile and exposes the service

### Fly.io

```bash
fly launch --dockerfile Dockerfile
fly volumes create flytime_data --size 1
# Mount volume at /data in fly.toml
fly deploy
```

### Any VPS (DigitalOcean, Hetzner, etc.)

```bash
git clone <repo>
cd scorefly
docker compose up -d
```

Add a reverse proxy (Caddy/nginx) for HTTPS if exposing publicly.

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `FLYTIME_DB_PATH` | `flytime-engine/data/flytime_engine.db` | SQLite database path |
| `HOST` | `0.0.0.0` | Dashboard bind address |
| `PORT` | `8787` | Dashboard port |
| `FEATURE_EXPORT_DIR` | `flytime-engine/exports` | Nightly CSV export directory |

## API endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /` | HTML dashboard |
| `GET /api/health` | Service health + match/fly counts |
| `GET /api/live` | Currently tracked live/upcoming matches |
| `GET /api/flytime` | Matches currently in FlyTime |
| `GET /api/events` | Recent fly triggers and transitions |
| `GET /api/intelligence` | Full accuracy + insights report |
| `GET /api/recommendations` | Per-league threshold recommendations |
| `GET /api/research` | Filterable historical data |
| `GET /api/export` | CSV download |
| `GET /api/match/{id}` | Full match detail with snapshots |

## Nightly jobs (automatic)

At 03:00 UTC each day the platform runs:

1. Threshold evaluation across all leagues
2. Formula A/B ranking
3. Feature CSV export to `/data/exports/`

## Local development (without Docker)

```bash
cd scorefly/flytime-engine
python main.py init
python run_platform.py
# → http://localhost:8787
```

Or run collector and dashboard separately:

```bash
python main.py serve      # terminal 1
python main.py dashboard  # terminal 2
```

## Data persistence

SQLite lives on a persistent volume (`/data` in Docker). Back up regularly:

```bash
docker compose exec fly-intelligence cp /data/flytime_engine.db /data/backup-$(date +%Y%m%d).db
```

When you exceed ~100k snapshots, consider migrating to Postgres (schema is portable).

## PWA integration

Fetch threshold recommendations from the cloud platform:

```
GET https://your-platform.example.com/api/recommendations
```

Apply to `FLY_V1_REGISTRY` in `index.html` manually or via a sync script.

## Cost estimate

| Item | Cost |
|------|------|
| ESPN API | $0 |
| Railway/Fly.io (512MB) | ~$5–7/month |
| Volume storage (1GB) | ~$0.25/month |
| **Total** | **~$5–8/month** |

## Validation checklist

Before trusting analytics:

1. Confirm `/api/health` shows `status: running` and recent `last_poll_at`
2. During a live match, verify `/api/live` shows updating scores
3. When a close finish occurs, confirm green fly events in `/api/events`
4. After the match, verify red fly flag on finished match in `/api/research`

Green fly detection has not been validated on real live data until the cloud collector runs through at least one close finish.
