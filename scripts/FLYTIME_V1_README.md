# FlyTime Engine v1 — Scripts

## Production JSON (bundled in app)

| Sport | File | Threshold | Status |
|-------|------|-----------|--------|
| AFL | `afl-flytime-v1.json` | 72 | Research-locked |
| NFL | `nfl-flytime-v1.json` | 93 | v1 bootstrap |

## Rebuild AFL tables

```bash
cd scripts
python export_tables_to_json.py
copy scorefly_research_tables.json ..\afl-flytime-v1.json
```

## Rebuild NFL tables

```bash
python build_nfl_flytime.py
python calibrate_nfl_threshold.py
```

`build_nfl_flytime.py` pulls NFL finals from ESPN (2019–2024 windows, 600 games in current API cap) and writes `nfl-flytime-v1.json`.

## Analyse thresholds

- `analyze_threshold.py` — AFL
- `calibrate_nfl_threshold.py` — NFL

## Score upcoming fixtures

- `score_upcoming.py` — AFL
- `score_nfl_upcoming.py` — NFL
