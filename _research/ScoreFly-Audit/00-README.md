# ScoreFly Complete System Audit

**Type:** Analysis only. No code, config, or data was changed.
**Scope:** `scorefly/index.html` (single-file PWA, 5,775 lines), `scorefly/sw.js`, the offline `scorefly/flytime-engine/` Python package, `scorefly/scripts/`, the 45 `*-flytime-v1.json` prediction tables, and `scorefly/team-halo-config.json`.
**Out of scope:** `scorefly/oracle-cloud/` (on hold).
**Audited against:** the workspace copy of `scorefly/index.html` as it stands now.

> **Doc/code freshness caveat.** Per the file-freshness rule in `SCOREFLY.md`, the project copy can lag the deployed copy. This audit reads the workspace copy as the source of truth for *code* and flags every place the *doc* disagrees with it (see the drift table below). All line numbers refer to the workspace copy.

---

## How to read this audit

Each phase is one markdown file. Every finding follows the brief's required shape:

- **Purpose** - what the thing is for
- **Current implementation** - what the code actually does (with `file:line` citations)
- **Cost** - compute / network / memory / battery
- **Accuracy** - does it produce correct/useful output
- **Risk** - what breaks, and the cost of changing it
- **Suggested improvement**
- **Expected benefit**

Findings carry three 1-10 scores:

- **Impact** - how much the user/product gains if fixed (10 = transformational)
- **Effort** - how much work to fix (10 = large, multi-day)
- **Risk** - chance of regression given the locked single-file architecture (10 = high)

Every recommendation is challenged against the core philosophy **"Scores Anywhere. Simple."** and the hard rules in `SCOREFLY.md` (single file, ASCII-only `<script>`, no build step, ESPN-only, locked fly-icon spec). Recommendations that would violate a hard rule are not made; where a finding tempts one, the file says so explicitly.

---

## Files

| File | Phase |
|------|-------|
| `01-system-map.md` | Phase 1 - the 16 named systems, data-flow + poll-hot-path diagrams |
| `02-formula-audit.md` | Phase 2 - every formula/threshold critiqued; duplicate logic; coupling |
| `03-flytime-audit.md` | Phase 3 - qualification/locking, the calibration-vs-live-rules gap, redesign option |
| `04-flysense-audit.md` | Phase 4 - momentum/decay/states, gradients, hysteresis, per-poll compute |
| `05-performance-runtime.md` | Phase 5 - rendering, halo probe, reflow, timers, memory, battery |
| `06-data-flow-state.md` | Phase 6 - state ownership, merge correctness, races, cache/TTLs |
| `07-scalability.md` | Phase 7 - 10k / 100k / 1M users; proxy + CDN + notification ceilings |
| `08-production-readiness.md` | Phase 8 - reliability, observability, readiness scores /10 |
| `09-master-recommendations.md` | Final prioritised list + top-10 "do first" |
| `10-todo-list.md` | **Working checklist** — all audit actions with benefit/difficulty/risk, done/deferred/remaining |

---

## Headline findings (read these first)

1. **`DEBUG_FLY = true` is shipped (`index.html:2013`).** This is the single highest-leverage line in the codebase. It is documented as "set false before public release". Because it is true, every card renders an internal flyscore debug readout, the FlyTime Lab dashboard is force-enabled for all users, and `renderFlyDashboard()` runs an O(leagues x upcoming) loop on **every poll** (`index.html:2525-2531`, called from `renderHome`/`renderResults`). One-character/one-line fix, large perf + UX + polish win. **Top priority.**

2. **Three overlapping FlyTime predictor layers now coexist** - the v1 offline tables (`FLY_V1_REGISTRY`, `index.html:5353`), the legacy `computeFlyMatch` (`index.html:5563`), and an undocumented **FlyTime 2.0 "Likely" engine** (`FLY2`, `index.html:2107` onward) that drives a flashing-green "likely" fly. `SCOREFLY.md` does not mention FLY2 at all. This is the biggest *simplification* and *doc-drift* target.

3. **The FlyTime predictor has never been validated** because the live-detection path (`isFlyTime`, `index.html:1934`) has reportedly never fired (red-fly / "reached" count stuck at 0). Calibration optimises against a **final-margin proxy** (`flytime.py:retroactive_flytime_from_final`) while the app detects FlyTime from **live clock state** - two different ground truths. Detailed in Phase 3.

4. **The whole feed + Fly Mode rebuild via `innerHTML` every poll** (`renderHome` `index.html:4646/4651`, `buildFlyModeGrid` `index.html:4869`), with no keyed diff, plus a full-document `querySelectorAll('[data-fk]')` and forced reflow in `flyCrossfade` (`index.html:1833-1863`) and a 32x32 canvas pixel probe re-attached to every recreated logo `<img>` (`attachTeamHaloProbe`/`sampleLogoStats`, `index.html:4297/4377`). Detailed in Phase 5.

5. **The v1 formula is duplicated in 10+ places** across Python and JS (`index.html:5456`, `flytime.py:120`, `config.py:196`, and seven `scripts/*.py`). Thresholds are hand-synced between `config.py` and `FLY_V1_REGISTRY` with no automated check. Detailed in Phase 2.

---

## Doc vs code drift (flagged, not assumed)

| Item | `SCOREFLY.md` says | Code says | File:line |
|------|--------------------|-----------|-----------|
| SW cache version | `scorefly-v115` (header) / v129 (history) | `scorefly-v131` | `sw.js:3` |
| Fast poll cadence | `FAST_POLL = 12s` | `FAST_POLL = 4000` (4s) + 5 tiers (1/3/4/30/60s) | `index.html:1129-1135` |
| Python poll mirror | n/a | `POLL_FAST_SEC = 12`, `POLL_FLYTIME_SEC = 8` (disagree with JS) | `config.py:217-218` |
| `DEBUG_FLY` | "false in production" | `true` | `index.html:2013` |
| FlyTime 2.0 / FLY2 | not mentioned | live, drives "likely" flashing fly | `index.html:2107`, `5717` |
| Feed count | "47 feeds" | 48 entries in `ESPN_FEEDS` (NBL added) | `index.html:1144-1193` |
| NRL form | "parked" comment | `loadRugbyLeagueForm` still called every sweep | `index.html:3216`, `3334` |

These are documentation-maintenance items, not necessarily code bugs. They are listed once here and referenced from the relevant phase files.
