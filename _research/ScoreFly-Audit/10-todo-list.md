# ScoreFly Audit — Comprehensive To-Do List

**Source:** `_research/ScoreFly-Audit/` (Phases 1–9, June 2026)  
**Purpose:** Actionable backlog from the complete system audit. Use this as the working checklist for speed, efficiency, FlyTime validation, and production readiness.  
**Hard rules (unchanged):** single `index.html`, ASCII-only `<script>`, no build step, ESPN-only, locked fly-icon spec.

---

## How to use this list

- Check boxes as work ships. Add the commit hash or `sw.js` cache version in the **Done** column when closing an item.
- **Benefit / Difficulty / Risk** use the audit’s 1–10 scores (higher = more). Benefit = Impact.
- **Do not tune FlyTime thresholds** until detection is proven (items in “Prove FlyTime” must come first).
- Every HTML/CSS/JS deploy: bump `CACHE` in `sw.js` and run the release checks in `SCOREFLY.md`.

**Related docs:** [00-README.md](00-README.md) · [09-master-recommendations.md](09-master-recommendations.md)

---

## Status at a glance

| Status | Count | Notes |
|--------|------:|-------|
| Done (v132) | 4 | Runtime quick wins shipped 2026-06-13 |
| Deferred by decision | 1 | `DEBUG_FLY` stays on until explicit release sign-off |
| Release blockers | 2 | Debug flag + unverified FlyTime detection |
| Remaining (PWA) | ~35 | See sections below |
| Infra / strategic | 4 | Only needed at scale |

---

## Done — shipped in v132 (`sw.js` → `scorefly-v132`, commit `50fab4f`)

| Done | Item | Benefit | Difficulty | Risk | Where |
|:----:|------|:-------:|:----------:|:----:|-------|
| [x] | Throttle `saveSnapshot` to ~20s (`SNAPSHOT_MIN_INTERVAL_MS`) | 5 | 2 | 2 | `index.html` ~3105 |
| [x] | Fly Mode poll 1s → 2s (`FLYMODE_POLL = 2000`) | 6 | 2 | 3 | `index.html` ~1129 |
| [x] | Cache logo contrast probe by image src (`_logoProbeCache`) | 6 | 3 | 2 | `index.html` ~4358 |
| [x] | Fly Mode uses `teamMatch` like the Feed | 5 | 2 | 2 | `index.html` ~4856 |
| [x] | Document v132 in `SCOREFLY.md` (partial) | 4 | 2 | 1 | `SCOREFLY.md` version history |

---

## Deferred — waiting on explicit decision

| Done | Item | Benefit | Difficulty | Risk | Notes |
|:----:|------|:-------:|:----------:|:----:|-------|
| [ ] | Ship `DEBUG_FLY = false` | 9 | 1 | 1 | **User decision:** keep testing UI on until they say to strip it. Lab still works via `?flylab=1` when off. `index.html:2014` |

---

## Release blockers (must resolve before calling the product “production ready”)

| Done | Item | Benefit | Difficulty | Risk | Phase | Action |
|:----:|------|:-------:|:----------:|:----:|-------|--------|
| [ ] | Remove debug from production (`DEBUG_FLY = false`) | 9 | 1 | 1 | 5.1 / 8.1 | One-line change + doc update + cache bump |
| [ ] | Prove FlyTime live detection works | 10 | 3–4 | 1–2 | 3.2 / 8.6 | Watch a close finish with app open; green fly live → red on Results. Add heartbeat log (#2 below) if still zero |

---

## Phase A — Next session (cheap, high value, low risk)

*Estimated: half a day. Do before any threshold tuning.*

| Done | # | Item | Benefit | Difficulty | Risk | File / function | Verify on phone |
|:----:|--:|------|:-------:|:----------:|:----:|-----------------|-----------------|
| [ ] | A1 | Finish `SCOREFLY.md` drift reconciliation | 4 | 2 | 1 | `SCOREFLY.md` | Doc only |
| [ ] | A2 | Add foreground FlyTime detection heartbeat log | 10 | 3 | 1 | `isFlyTime` ~1934, ledger ~2078 | Open app on close game; log shows true/false each poll |
| [ ] | A3 | Decide FLY2 fate: **document** or **disable** “Likely” flashing fly | 6 | 2 | 3 | `FLY2` ~2107, `flyTimeIcon` ~5717 | Confirm flashing green behaviour matches decision |
| [ ] | A4 | Prune `flyFadePrev` when matches leave live | 2 | 1 | 1 | `flyFadePrev` ~1832, `applyScoreFlashes` | Long session; memory stable |
| [ ] | A5 | Align fast-lane vs full-sweep results window constant | 1 | 1 | 1 | `RESULTS_MS` vs `WIN_MINE_BACK` ~3141/3233 | Edge case only |
| [ ] | A6 | Cache `favMatchNames()` per favourites change | 3 | 2 | 2 | render paths ~4623+ | My Teams filter unchanged |

### Doc drift checklist (A1)

Update `SCOREFLY.md` so it matches code:

- [ ] Header cache version (`scorefly-v132` — update when cache bumps again)
- [ ] Poll tiers: document actual JS tiers (1s Fly Mode was 2s; FAST 4s; FLYTIME 3s; SOON 30s; SLOW 60s) — not the old “12s live” text
- [ ] Document **FlyTime 2.0 / FLY2** “Likely” engine (or note it was disabled)
- [ ] Feed count: 48 entries in `ESPN_FEEDS` (not “47”)
- [ ] NRL form: `loadRugbyLeagueForm` still runs — remove “parked” if inaccurate
- [ ] `DEBUG_FLY = true` during testing (already partially documented in v132 entry)
- [ ] Python `config.py` poll constants vs JS (note they are offline-only mirrors, may drift)

---

## Phase B — Prove FlyTime (unblock the core promise)

*Do A2 → B1 → B2 before spending time on calibration or threshold tweaks.*

| Done | # | Item | Benefit | Difficulty | Risk | Phase | Notes |
|:----:|--:|------|:-------:|:----------:|:----:|-------|-------|
| [ ] | B1 | Opt-in production beacon: “isFlyTime fired” | 6 | 4 | 3 | 8.5 | Privacy-light; answers field truth at scale |
| [ ] | B2 | Global error beacon (`window.onerror` / `unhandledrejection`) | 3 | 2 | 2 | 8.2 | Catches silent JS failures on user devices |
| [ ] | B3 | Manual validation session: one watched close finish | 10 | 2 | 1 | 3.2 | Green fly while live; red on Results; ledger “reached” > 0 |
| [ ] | B4 | Review ledger stats after validation (`flyLedgerStats`) | 5 | 1 | 1 | 3 | Only meaningful after B3 |

**Gate:** Do **not** proceed to Phase C prediction/calibration work until B3 passes or heartbeat log explains why not.

---

## Phase C — Performance & runtime (structural PWA work)

| Done | # | Item | Benefit | Difficulty | Risk | Phase | Est. gain |
|:----:|--:|------|:-------:|:----------:|:----:|-------|-----------|
| [ ] | C1 | Keyed card diff instead of wholesale `innerHTML` rebuild | 8 | 7 | 6 | 5.2 | Largest remaining perf win; reuse nodes by match id |
| [ ] | C2 | Single-pass predictor sweep; no render from `ledgerPredict` | 5 | 3 | 3 | 2.8 / 5.5 | Halves upcoming walk; stops mid-sweep dashboard |
| [ ] | C3 | Scope `flyCrossfade` query to active container (not full document) | 3 | 3 | 3 | 5.4 | Smaller DOM query each poll |
| [ ] | C4 | Trim 2nd-order FlySense terms / throttle history off 1s tier | 5 | 4 | 4 | 4.9 | Fly Mode battery; needs before/after check |
| [ ] | C5 | Extend `prefers-reduced-motion` to FLY2 flash + pulse animations | 3 | 2 | 1 | 4.5 | Accessibility |
| [ ] | C6 | Prevent live + upcoming duplicate between sweeps | 3 | 3 | 3 | 6.3.1 | Game at kickoff may appear in both lists briefly |

### C1 subtasks (keyed diff — schedule as its own mini-project)

- [ ] Map current card builders: `buildLiveCard`, `buildResultCard`, `buildUpcomingCard`, Fly Mode tiles
- [ ] Maintain `Map<matchId, HTMLElement>` per list container
- [ ] Patch text/classes/styles only when data changes
- [ ] Preserve locked card markup and fly-icon positions exactly
- [ ] Retest FlySense colour crossfade (may simplify or remove `flyCrossfade` hack)
- [ ] Live test: Feed, Results, Fly Mode during active games

---

## Phase D — Prediction systems (after FlyTime detection is proven)

| Done | # | Item | Benefit | Difficulty | Risk | Phase | Notes |
|:----:|--:|------|:-------:|:----------:|:----:|-------|-------|
| [ ] | D1 | Centralise v1 formula in Python package + export to JSON for JS | 5 | 4 | 2 | 2.7 / #10 | Single source; 11 duplicate sites today |
| [ ] | D2 | Offline sync check: `FLY_V1_REGISTRY` ↔ `config.py` ↔ `isFlyTime` ↔ `is_flytime_live` | 4 | 3 | 1 | 2.11 | Extend `validate_flytime_rules.py`; add `scripts/check_sync.py` |
| [ ] | D3 | Re-label calibration to live rule (not final-margin proxy) | 7 | 6 | 4 | 3.3 | `retroactive_flytime_from_final` vs clock-based detection |
| [ ] | D4 | Collapse v1 + legacy + FLY2 into one staged `flyTime(m)` | 6 | 6 | 5 | 3.8.2 | Returns `{ stage, score }`; one caller surface |
| [ ] | D5 | Unify AFL name maps + sync check | 4 | 3 | 3 | 3.5 / 6.2 | Prevents silent v1 table misses |
| [ ] | D6 | Cricket: define yellow-fly behaviour (no `CLOSE_MARGIN` in v1) | 4 | 3 | 4 | 2.4 | Legacy-only or add cricket margins |
| [ ] | D7 | Fix v1 balance terms (similarity vs closeness) | 4 | 5 | 6 | 2.1 | **Only after D3** — table rebuild |
| [ ] | D8 | Review `close_margin * 3` denominator | 2 | 2 | 3 | 2.3 | Document or drop `tight` term |
| [ ] | D9 | Rescale `form_strength` 40-floor | 3 | 6 | 6 | 2.2 | Calibration-coupled; low priority |
| [ ] | D10 | Tune `isFlyTime` thresholds per league | 3 | 2 | 5 | 2.6 | **Blind until B3 passes** |
| [ ] | D11 | Tune `FLYMATCH_THRESHOLD` / nodata / comp gap | 3 | 2 | 5 | 2.5 | **Blind until B3 passes** |

---

## Phase E — FlySense polish (optional quality pass)

| Done | # | Item | Benefit | Difficulty | Risk | Phase |
|:----:|--:|------|:-------:|:----------:|:----:|-------|
| [ ] | E1 | Evaluate dropping acceleration/suppression/peak-collapse terms | 4 | 4 | 4 | 4.1 |
| [ ] | E2 | Cricket wall-clock momentum fallback review | 2 | 3 | 3 | 2.10 |
| [ ] | E3 | Confirm 8-state labels vs continuous colour separation still clear to users | 2 | 2 | 2 | 4.2 |

*FlySense core (hysteresis, gradients, cricket run-rate engine) was rated solid — no mandatory changes.*

---

## Phase F — Scalability & infra (strategic / native track)

*Not needed at current scale. First bottleneck: free CORS proxies (~1k–10k concurrent actives).*

| Done | # | Item | Benefit | Difficulty | Risk | Phase | Trigger |
|:----:|--:|------|:-------:|:----------:|:----:|-------|---------|
| [ ] | F1 | Self-hosted CORS proxy or edge function | 8 | 6 | 5 | 7.2 | Proxy rate limits / reliability |
| [ ] | F2 | Fan-in feed cache (1 ESPN fetch → N clients) | 9 | 8 | 6 | 7.3 | >10k actives |
| [ ] | F3 | Push server (VAPID) for background alerts | 7 | 8 | 5 | 7.5 | Alerts must work when app closed |
| [ ] | F4 | Trim precached `team-halo-config.json` payload | 4 | 4 | 2 | 7.4 | Install size / first load |

---

## Headline findings → todo mapping

| # | Headline (from 00-README) | Primary todos |
|---|---------------------------|---------------|
| 1 | `DEBUG_FLY = true` shipped | Deferred item + Release blocker |
| 2 | Three overlapping FlyTime layers + undocumented FLY2 | A3, D4 |
| 3 | FlyTime never validated; calibration vs live rules mismatch | A2, B1–B4, D3 |
| 4 | Full `innerHTML` rebuild every poll + logo probe + `flyCrossfade` | v132 logo cache done; C1, C3, C4 |
| 5 | v1 formula duplicated 10+ places | D1, D2 |

---

## Recommended sequence (summary)

```text
DONE (v132)
  snapshot throttle, Fly Mode 2s poll, logo probe cache, teamMatch fix

NOW (Phase A)
  doc drift → heartbeat log → FLY2 decision → tiny cleanups (fadePrev, fav cache)

NEXT (Phase B)
  prove detection → optional beacons → manual validation session

THEN (Phase C)
  keyed card diff (big) → single-pass sweep → flyCrossfade scope

AFTER VALIDATION (Phase D)
  formula centralisation → calibration re-label → layer collapse → threshold tuning

LATER (Phase F)
  proxy → fan-in cache → push → halo payload trim

EXPLICIT RELEASE STEP (when user says so)
  DEBUG_FLY = false + final doc pass + cache bump
```

---

## Explicitly out of scope (audit said no)

Do **not** add these without a fresh product decision:

- Rivalries, score worms, expand-collapse cards, stat ticker, Must Watch, Gold Glow
- Merging FlySense score colours with fly-icon system (correctly separate)
- New card UI for FlyTime (locked fly-icon-only spec)
- PWA build step, framework, or splitting `index.html`
- Reintroducing `oracle-cloud/` work (on hold)

---

## Release checklist (every deploy)

Copy from `SCOREFLY.md` — run before pushing:

- [ ] No forbidden Unicode inside `<script>` (U+2014, U+2013, box drawing, U+2212, U+00B1)
- [ ] Page order: `page-home` → `page-results` → `page-settings`
- [ ] `results-cards` inside `page-results`
- [ ] JS syntax sanity check
- [ ] Bump `CACHE` in `sw.js`
- [ ] Update `SCOREFLY.md` version history if behaviour changed
- [ ] Describe phone verification steps for anything behavioural

---

## Change log (this file)

| Date | Change |
|------|--------|
| 2026-06-13 | Created from audit Phases 2–9; marked v132 completed items and DEBUG deferral |
