# Phase 9 - Master Recommendations

Every recommendation from Phases 2-8, prioritised. Sorted by **highest impact, then lowest effort, then lowest risk**. Rendered as grouped lists for readability rather than one mega-table.

Columns where shown: **Imp** = Impact 1-10, **Eff** = Effort 1-10, **Rsk** = Risk 1-10, plus estimated **Perf** / **Accuracy** / **Cost** gains (qualitative).

All recommendations respect the hard rules: single inline file, ASCII-only `<script>`, no PWA build step, ESPN-only, locked fly-icon spec. Where a recommendation touches infra (proxy/backend), that is outside `index.html` and noted.

---

## Top 10 - do first

1. **Ship `DEBUG_FLY = false`** (`index.html:2013`). *Imp 9 / Eff 1 / Rsk 1.* Perf: removes the per-poll O(45 x upcoming) dashboard + per-card debug scores + mid-render `computeFlyMatch`. UX: removes debug text leaking onto every card. The lab still works via `?flylab=1`. **The single best effort-to-value edit in the codebase.**

2. **Prove FlyTime detection with an opt-in foreground heartbeat log** (Phase 3.8.1; `isFlyTime` `1934`, ledger `2078`). *Imp 10 / Eff 3 / Rsk 1.* Accuracy: unblocks validation of the entire predictor stack - the #1 product question. Log every live `isFlyTime` evaluation (even false) so one watched close finish yields evidence.

3. **Add a privacy-light, opt-in production beacon for "isFlyTime fired"** (Phase 8.5). *Imp 6 / Eff 4 / Rsk 3.* Accuracy/observability: answers "did a green fly ever appear for a real user" at scale, which local-only telemetry cannot.

4. **Decide FLY2's fate: document the "Likely" flashing fly or disable it** (`flyTimeIcon` `5717`, `FLY2` `2107`). *Imp 6 / Eff 2 / Rsk 3.* Removes an undocumented, unproven user-facing behaviour or makes it official. Pairs with #2.

5. **Single-pass predictor sweep + stop rendering from inside `ledgerPredict`** (Phase 2.8/5.5; `runFlyMatchSweep` `5551`, `ledgerPredict` `2076`). *Imp 5 / Eff 3 / Rsk 3.* Perf: halves the per-sweep upcoming walk; removes mid-sweep dashboard rebuilds.

6. **Throttle `saveSnapshot` to ~15-30s, decoupled from poll tier** (Phase 5.7; `3106`). *Imp 5 / Eff 2 / Rsk 2.* Perf/battery: removes a synchronous JSON serialise+write from the 1s/3s hot path.

7. **Fly Mode poll tier 1s -> 2-3s** (Phase 5.8; `FLYMODE_POLL` `1129`). *Imp 6 / Eff 2 / Rsk 3.* Cost/battery: large reduction in the marquee high-drain state; still reads as "instant".

8. **Cache the logo-contrast probe by image src** (Phase 5.3; `sampleLogoStats` `4297`, `attachTeamHaloProbe` `4377`). *Imp 6 / Eff 3 / Rsk 2.* Perf: removes dozens of `getImageData` canvas readbacks per poll.

9. **Fly Mode should use `teamMatch` like the Feed** (Phase 6.8; `buildFlyModeGrid` `4840`). *Imp 5 / Eff 2 / Rsk 2.* Correctness: fixes followed games missing from the big screen.

10. **Centralise the v1 formula in the Python package + add an offline threshold/rule sync check** (Phase 2.7/2.11; 11 duplicate sites). *Imp 5 / Eff 4 / Rsk 2.* Maintainability: one definition; `scripts/check_sync.py` asserts `FLY_V1_REGISTRY` == `config.py` and JS `isFlyTime` == `is_flytime_live` (the latter already has `validate_flytime_rules.py`). Offline only - no PWA risk.

---

## Performance & runtime

| Rec | Imp | Eff | Rsk | Perf | Cost |
|-----|:--:|:--:|:--:|------|------|
| Ship `DEBUG_FLY=false` (#1) | 9 | 1 | 1 | Huge per-poll CPU cut | - |
| Keyed card diff instead of innerHTML rebuild (5.2) | 8 | 7 | 6 | Large layout/paint + img-decode cut; also removes the `flyCrossfade` reflow hack | - |
| Fly Mode 1s->2-3s (#7) | 6 | 2 | 3 | Med CPU | Large battery/network |
| Cache logo probe by src (#8) | 6 | 3 | 2 | Med (no canvas readbacks) | - |
| Single-pass sweep (#5) | 5 | 3 | 3 | Med | - |
| Throttle snapshot (#6) | 5 | 2 | 2 | Removes sync write | Battery |
| Trim 2nd-order FlySense terms / throttle hist off 1s tier (4.9) | 5 | 4 | 4 | Med on Fly Mode | Battery |
| Scope `flyCrossfade` query + prune `flyFadePrev` (5.4/5.9) | 3 | 3 | 3 | Small | Memory |
| Extend `prefers-reduced-motion` (4.5) | 3 | 2 | 1 | - | Accessibility |

## Prediction systems (FlyTime / FlyMatch)

| Rec | Imp | Eff | Rsk | Accuracy |
|-----|:--:|:--:|:--:|----------|
| Prove detection (heartbeat log) (#2) | 10 | 3 | 1 | Unblocks all validation |
| Production beacon (#3) | 6 | 4 | 3 | Field truth on detection |
| Document/disable FLY2 (#4) | 6 | 2 | 3 | Removes unproven UX |
| Re-label calibration to the live rule, not final margin (3.3) | 7 | 6 | 4 | Trains predictor on the right target |
| Collapse 3 layers into one staged `flyTime(m)` (3.8.2) | 6 | 6 | 5 | Simpler, removes doc gap |
| Cricket has no `CLOSE_MARGIN`; legacy model is cricket-only (2.4) | 4 | 3 | 4 | Defines cricket yellow behaviour |
| Unify AFL name maps / add sync (3.5/6.2) | 4 | 3 | 3 | Prevents silent table misses |
| v1 balance terms reward similarity not closeness (2.1) | 4 | 5 | 6 | Better closeness signal (calibration-coupled) |

## Data flow, state & correctness

| Rec | Imp | Eff | Rsk |
|-----|:--:|:--:|:--:|
| Fly Mode `teamMatch` consistency (#9) | 5 | 2 | 2 |
| Prevent live+upcoming overlap between sweeps (6.3.1) | 3 | 3 | 3 |
| Cache `favMatchNames()` per favs-change (2.9) | 3 | 2 | 2 |
| Prune `flyFadePrev` (6.1) | 2 | 1 | 1 |
| Align fast-lane/full-sweep results window constant (6.3.2) | 1 | 1 | 1 |

## Maintainability & docs

| Rec | Imp | Eff | Rsk |
|-----|:--:|:--:|:--:|
| Centralise v1 formula + sync check (#10) | 5 | 4 | 2 |
| Reconcile `SCOREFLY.md` with code (cache v131, poll tiers, FLY2, feed count, NRL form) (README drift table) | 4 | 2 | 1 |
| Add global `window.onerror`/`unhandledrejection` beacon (8.2) | 3 | 2 | 2 |

## Scalability (infra track - beyond `index.html`)

| Rec | Imp | Eff | Rsk |
|-----|:--:|:--:|:--:|
| Self-hosted CORS proxy / edge function before ~1k-10k actives (7.2) | 8 | 6 | 5 |
| Fan-in feed cache (1 fetch -> N clients) for >10k (7.3) | 9 | 8 | 6 |
| Push server (VAPID) for closed-app alerts (7.5) | 7 | 8 | 5 |
| Trim `team-halo-config.json` precached payload (7.4) | 4 | 4 | 2 |

---

## Sequencing guidance

- **This week (cheap, high value, low risk):** #1, #6, #7, #8, #9, plus the README doc reconciliation. These are mostly one-to-a-few-line edits that cut per-poll cost and fix a real bug, with negligible regression risk. Re-bump `sw.js` `CACHE` on deploy.
- **Next (unblock the core promise):** #2 then #3, then #4. Until detection is proven, do **not** spend effort tuning thresholds (it is blind, per Phase 3).
- **Then (structural, schedule carefully):** keyed card diff (5.2), single-pass sweep (#5), formula centralisation (#10), calibration re-label (3.3).
- **Strategic (native/back-end track):** the scalability items - the app is fine for current scale; these define when a backend stops being optional (low thousands of concurrent actives).

## What this audit explicitly did NOT recommend

- No reintroduction of removed features (rivalries, score worms, banners, pills) - none would help.
- No merging of the three independent fly systems (score-colour / borders / fly icon) - the separation is correct and locked.
- No new card UI for FlyTime - the locked fly-icon-only spec is respected; all FlyTime recommendations are internal.
- No PWA build step, framework, or file split - all perf recommendations are achievable in vanilla inline JS.
