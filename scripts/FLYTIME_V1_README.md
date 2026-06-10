# FlyTime Engine v1 — Scripts

## Production JSON (bundled in app)

| Sport | File | Threshold | Status |
|-------|------|-----------|--------|
| AFL | `afl-flytime-v1.json` | 72 | Research-locked |
| NFL | `nfl-flytime-v1.json` | 93 | v1 bootstrap |
| NBA | `nba-flytime-v1.json` | 88 | v1 bootstrap |
| WNBA | `wnba-flytime-v1.json` | 70 | v1 bootstrap |
| NCAAM | `ncaam-flytime-v1.json` | 97 | v1 bootstrap |
| MLB | `mlb-flytime-v1.json` | 85 | v1 bootstrap |
| NHL | `nhl-flytime-v1.json` | 78 | v1 bootstrap |
| NCAAF | `ncaaf-flytime-v1.json` | 96 | v1 bootstrap |
| NRL | `nrl-flytime-v1.json` | 85 | v1 bootstrap |
| Soccer (22 leagues) | `soccer-{league}-flytime-v1.json` | 78–98 per league | v1 bootstrap |
| Tennis / Cricket | — | — | Green fly only |

## Rebuild AFL tables

```bash
cd scripts
python export_tables_to_json.py
copy scorefly_research_tables.json ..\afl-flytime-v1.json
```

## Rebuild bootstrap tables (team sports)

```bash
python build_flytime_v1.py --all
python build_soccer_flytime.py --all
python calibrate_flytime.py
```

Legacy NFL-only script: `build_nfl_flytime.py`

`build_nfl_flytime.py` pulls NFL finals from ESPN (2019–2024 windows, 600 games in current API cap) and writes `nfl-flytime-v1.json`.

## Analyse thresholds

- `analyze_threshold.py` — AFL
- `calibrate_nfl_threshold.py` — NFL

## Score upcoming fixtures

- `score_upcoming.py` — AFL
- `score_nfl_upcoming.py` — NFL
