-- FlyTime Data Engine schema
-- SQLite-compatible; portable to Postgres with minor type tweaks

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- ── Core reference ──────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS formula_versions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    version_key     TEXT NOT NULL UNIQUE,          -- v1, v2, v3, experimental
    name            TEXT NOT NULL,
    weights_json    TEXT NOT NULL,                 -- {"close_rate":0.35,...}
    is_production   INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS leagues (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    sport           TEXT NOT NULL,
    league_code     TEXT NOT NULL,
    label           TEXT NOT NULL,
    tag             TEXT,
    flytime_file    TEXT,                          -- *-flytime-v1.json filename
    close_margin    INTEGER NOT NULL DEFAULT 8,
    chunk_size      INTEGER NOT NULL DEFAULT 16,
    threshold       REAL,                          -- current production threshold
    threshold_type  TEXT NOT NULL DEFAULT 'fixed', -- fixed | percentile | dynamic
    UNIQUE (sport, league_code)
);

-- ── Matches ─────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS matches (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    espn_event_id   TEXT NOT NULL UNIQUE,
    league_id       INTEGER NOT NULL REFERENCES leagues(id),
    home_team       TEXT NOT NULL,
    away_team       TEXT NOT NULL,
    home_team_id    TEXT,
    away_team_id    TEXT,
    venue           TEXT,
    scheduled_at    TEXT,
    status          TEXT NOT NULL DEFAULT 'upcoming', -- upcoming|live|finished|cancelled
    home_score      INTEGER,
    away_score      INTEGER,
    final_margin    INTEGER,
    season          TEXT,
    round_label     TEXT,
    -- Fly outcome flags (ground truth)
    had_live_flytime    INTEGER NOT NULL DEFAULT 0,
    had_yellow_fly      INTEGER NOT NULL DEFAULT 0,
    had_blue_fly        INTEGER NOT NULL DEFAULT 0,
    had_red_fly         INTEGER NOT NULL DEFAULT 0,
    -- Metadata
    first_seen_at   TEXT,
    last_polled_at  TEXT,
    finished_at     TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_matches_league ON matches(league_id);
CREATE INDEX IF NOT EXISTS idx_matches_status ON matches(status);
CREATE INDEX IF NOT EXISTS idx_matches_scheduled ON matches(scheduled_at);

-- ── Live snapshots (poll-time state) ────────────────────────────────────────

CREATE TABLE IF NOT EXISTS live_snapshots (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id        INTEGER NOT NULL REFERENCES matches(id),
    captured_at     TEXT NOT NULL,
    status          TEXT NOT NULL,
    period          INTEGER,
    clock_raw       TEXT,
    clock_sec       INTEGER,
    home_score      INTEGER,
    away_score      INTEGER,
    margin          INTEGER,
    is_flytime      INTEGER NOT NULL DEFAULT 0,
    flytime_score   REAL,
    threshold       REAL,
    formula_version TEXT,
    is_yellow       INTEGER NOT NULL DEFAULT 0,
    is_blue         INTEGER NOT NULL DEFAULT 0,
    is_red          INTEGER NOT NULL DEFAULT 0,
    is_flymode      INTEGER NOT NULL DEFAULT 0,
    extra_json      TEXT
);

CREATE INDEX IF NOT EXISTS idx_snapshots_match ON live_snapshots(match_id);
CREATE INDEX IF NOT EXISTS idx_snapshots_time ON live_snapshots(captured_at);

-- ── Match events (timeline) ─────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS match_events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id        INTEGER NOT NULL REFERENCES matches(id),
    event_at        TEXT NOT NULL,
    event_type      TEXT NOT NULL,
    -- Types: status_change, score_change, yellow_fly, blue_fly, green_fly,
    --        flymode_enter, red_fly, threshold_change, match_start, match_end
    match_state     TEXT,
    home_score      INTEGER,
    away_score      INTEGER,
    period          INTEGER,
    clock_raw       TEXT,
    flytime_score   REAL,
    threshold       REAL,
    formula_version TEXT,
    detail_json     TEXT
);

CREATE INDEX IF NOT EXISTS idx_events_match ON match_events(match_id);
CREATE INDEX IF NOT EXISTS idx_events_type ON match_events(event_type);

-- ── Fly events (aggregated fly lifecycle) ───────────────────────────────────

CREATE TABLE IF NOT EXISTS fly_events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id        INTEGER NOT NULL REFERENCES matches(id),
    fly_type        TEXT NOT NULL,                 -- yellow|green|blue|red
    activated_at    TEXT,
    deactivated_at  TEXT,
    flytime_score   REAL,
    threshold       REAL,
    formula_version TEXT,
    period          INTEGER,
    clock_raw       TEXT,
    margin          INTEGER,
    time_remaining_sec INTEGER,
    converted_to_red INTEGER,                      -- yellow/blue → red
    detail_json     TEXT
);

CREATE INDEX IF NOT EXISTS idx_fly_events_match ON fly_events(match_id);
CREATE INDEX IF NOT EXISTS idx_fly_events_type ON fly_events(fly_type);

-- ── Blue Fly analysis ───────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS blue_fly_events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id        INTEGER NOT NULL REFERENCES matches(id),
    league_id       INTEGER NOT NULL REFERENCES leagues(id),
    activated_at    TEXT NOT NULL,
    yellow_score    REAL NOT NULL,
    yellow_threshold REAL NOT NULL,
    green_at        TEXT,
    match_state_at_activation TEXT,
    period          INTEGER,
    clock_raw       TEXT,
    time_remaining_sec INTEGER,
    score_differential INTEGER,
    home_score      INTEGER,
    away_score      INTEGER,
    became_red_fly  INTEGER NOT NULL DEFAULT 0,
    final_margin    INTEGER,
    final_winner    TEXT,                          -- home|away|draw
    formula_version TEXT NOT NULL DEFAULT 'v1'
);

CREATE INDEX IF NOT EXISTS idx_blue_fly_league ON blue_fly_events(league_id);

-- ── Threshold history & learning ────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS threshold_history (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    league_id       INTEGER NOT NULL REFERENCES leagues(id),
    recorded_at     TEXT NOT NULL DEFAULT (datetime('now')),
    threshold_type  TEXT NOT NULL,                 -- fixed|percentile|dynamic
    threshold_value REAL NOT NULL,
    percentile      REAL,                          -- e.g. 0.20 for top 20%
    formula_version TEXT NOT NULL DEFAULT 'v1',
    yellow_count    INTEGER,
    red_count       INTEGER,
    conversion_pct  REAL,
    fly_volume      REAL,
    avg_flytime_score REAL,
    avg_winning_score REAL,
    recommended     INTEGER NOT NULL DEFAULT 0,
    notes           TEXT
);

CREATE INDEX IF NOT EXISTS idx_threshold_league ON threshold_history(league_id);

-- ── League metrics (rolling aggregates) ───────────────────────────────────────

CREATE TABLE IF NOT EXISTS league_metrics (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    league_id       INTEGER NOT NULL REFERENCES leagues(id),
    period_start    TEXT NOT NULL,
    period_end      TEXT NOT NULL,
    formula_version TEXT NOT NULL DEFAULT 'v1',
    threshold       REAL,
    games_total     INTEGER NOT NULL DEFAULT 0,
    yellow_flies    INTEGER NOT NULL DEFAULT 0,
    green_flies     INTEGER NOT NULL DEFAULT 0,
    blue_flies      INTEGER NOT NULL DEFAULT 0,
    red_flies       INTEGER NOT NULL DEFAULT 0,
    conversion_pct  REAL,
    false_positives INTEGER NOT NULL DEFAULT 0,
    false_negatives INTEGER NOT NULL DEFAULT 0,
    avg_flytime_score REAL,
    avg_winning_score REAL,
    recommended_threshold REAL,
    computed_at     TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (league_id, period_start, period_end, formula_version)
);

-- ── Predictions & backtests ───────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS prediction_results (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id        INTEGER NOT NULL REFERENCES matches(id),
    formula_version TEXT NOT NULL,
    threshold       REAL NOT NULL,
    flytime_score   REAL,
    predicted_fly   INTEGER NOT NULL DEFAULT 0,
    actual_fly      INTEGER NOT NULL DEFAULT 0,
    is_hit          INTEGER NOT NULL DEFAULT 0,
    is_false_alarm  INTEGER NOT NULL DEFAULT 0,
    is_miss         INTEGER NOT NULL DEFAULT 0,
    scored_at       TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (match_id, formula_version)
);

CREATE INDEX IF NOT EXISTS idx_predictions_match ON prediction_results(match_id);
CREATE INDEX IF NOT EXISTS idx_predictions_formula ON prediction_results(formula_version);

CREATE TABLE IF NOT EXISTS historical_backtests (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    league_id       INTEGER NOT NULL REFERENCES leagues(id),
    formula_version TEXT NOT NULL,
    threshold       REAL NOT NULL,
    threshold_type  TEXT NOT NULL DEFAULT 'fixed',
    season_label    TEXT,
    games_tested    INTEGER NOT NULL,
    yellow_count    INTEGER NOT NULL,
    red_count       INTEGER NOT NULL,
    conversion_pct  REAL,
    false_positives INTEGER NOT NULL DEFAULT 0,
    false_negatives INTEGER NOT NULL DEFAULT 0,
    avg_score       REAL,
    run_at          TEXT NOT NULL DEFAULT (datetime('now')),
    config_json     TEXT
);

CREATE INDEX IF NOT EXISTS idx_backtests_league ON historical_backtests(league_id);

-- ── Service state (restart recovery) ────────────────────────────────────────

CREATE TABLE IF NOT EXISTS service_state (
    key             TEXT PRIMARY KEY,
    value           TEXT NOT NULL,
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ── Backfill progress ─────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS backfill_progress (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    league_id       INTEGER NOT NULL REFERENCES leagues(id),
    date_range_start TEXT NOT NULL,
    date_range_end  TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending', -- pending|running|done|failed
    games_imported  INTEGER NOT NULL DEFAULT 0,
    started_at      TEXT,
    finished_at     TEXT,
    error_message   TEXT,
    UNIQUE (league_id, date_range_start, date_range_end)
);
