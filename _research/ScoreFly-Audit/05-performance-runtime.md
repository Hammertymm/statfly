# Phase 5 - Performance & Runtime

Estimated gains are relative to the per-poll cost on a mid-range phone with a busy board. They are reasoned estimates, not measured (no profiling was run, per the analysis-only scope).

---

## 5.1 `DEBUG_FLY = true` shipped - the dashboard runs every poll

**Purpose (intended):** lab-only tuning dashboard + per-card debug scores.

**Current implementation:** `DEBUG_FLY = true` (`index.html:2013`); `flyLabEnabled()` returns true unconditionally when `DEBUG_FLY` (`2024-2025`); `renderFlyDashboard()` is called from `renderHome` (`4655`) and `renderResults` (`4681`), both every poll. The dashboard:
- iterates `FLY_V1_REGISTRY` (45 keys) and, **inside that loop, iterates all of `ALL_UPCOMING`** (`2525-2531`) -> O(45 x |UPCOMING|);
- calls `flyDashboardPerLeague` (`2284`) which again loops the registry + UPCOMING;
- builds a multi-kilobyte HTML string and sets `innerHTML` on the ledger panel;
- runs `syncFlyLedgerFromResults` (`2443`).
- Additionally, every card calls `flyScoreDebugHTML` (`5664`) which can re-invoke `computeFlyMatch` mid-render (`5639/5653`).

**Cost:** with a 30-day window across 48 feeds, `ALL_UPCOMING` can be hundreds of matches; 45 x 300 = ~13,500 iterations per poll *just for the engine snapshot*, plus a second registry x upcoming pass, plus string building, on top of the actual feed render. At the 1s/3s tiers this is the dominant main-thread cost.

**Risk:** none to fix - it is a documented pre-release flag.

**Suggested improvement:** set `DEBUG_FLY = false`. The lab still works via `?flylab=1` for the developer (`2026-2031`).

**Expected benefit:** removes the entire dashboard cost and all per-card debug-score work from production polls; eliminates the per-card `computeFlyMatch` re-entry. **Est. perf gain: the single biggest per-poll CPU reduction available.** **Impact 9 / Effort 1 / Risk 1.**

---

## 5.2 Wholesale `innerHTML` rebuild every poll (no keyed diff)

**Current implementation:** `renderHome` rebuilds `live-cards` and `upcoming-cards` via `.map(buildLiveCard).join('')` -> `innerHTML` (`4646`, `4651`); `renderResults` rebuilds all result groups (`4680`); `buildFlyModeGrid` rebuilds the entire grid (`4869-4896`). Runs every poll (1-60s depending on tier).

**Cost:** destroys and recreates every card DOM node even when nothing changed, forcing full parse + layout + paint, discarding all `<img>` decode work, and re-running every logo's onload probe (5.3). For a feed of dozens of cards this is the largest rendering cost.

**Accuracy:** functionally correct but wasteful; also causes the score-flash + crossfade gymnastics (because the nodes are new each time, there is nothing to transition from - hence `flyCrossfade`, `1827-1831` comment).

**Suggested improvement:** keyed reconciliation - reuse card nodes by `data-match-id` and update only changed text/class/style. This is achievable in vanilla JS without a framework (no build step needed): maintain a `Map<id, node>`, diff, patch. It also removes the need for the `flyCrossfade` reflow hack because real nodes persist and CSS transitions work natively.

**Expected benefit:** large reduction in layout/paint and image re-decode on every poll; smoother Fly Mode at 1s. **Impact 8 / Effort 7 / Risk 6** (largest refactor here; must preserve the locked card markup exactly).

---

## 5.3 Per-poll 32x32 canvas logo-contrast probe

**Current implementation:** every logo `<img>` is rendered with `onload="attachTeamHaloProbe(this)"` (`4429`). On load, `probeTeamLogoContrast` -> `sampleLogoStats` (`4297`) draws the image to a 32x32 canvas and calls `getImageData` (1024 px scan) to compute brightness/sat/mass (`4305-4321`).

**Cost:** because cards are rebuilt every poll (5.2), every logo `<img>` is a *new* element, so it loads/decodes and **re-runs the probe every poll** for every visible logo. `getImageData` forces a readback and is not free; doing it dozens of times per poll is pure waste - the result is deterministic per logo URL and never changes.

**Suggested improvement (independent of 5.2):** cache the probe result by logo src (a module-level `Map<src, attrs>`); on subsequent loads of the same src, apply the cached attributes without touching a canvas. Better still, most logos are already pre-classified in `team-halo-config.json` (the probe is a fallback for un-classified logos, `4358-4360`), so a cache would make the canvas path rare. Combined with 5.2 (node reuse), the probe would run once per logo per session.

**Expected benefit:** eliminates dozens of `getImageData` calls per poll. **Impact 6 / Effort 3 / Risk 2.**

---

## 5.4 `flyCrossfade` document-wide query + forced reflow

**Current implementation** (`1833-1863`): `document.querySelectorAll('[data-fk]')` every render (matches every score cell on every page, including hidden tabs), then a single forced reflow (`void document.body.offsetWidth`, `1854`) to commit colour jumps.

**Cost:** the forced reflow is correctly batched (one per render - good). The waste is the unscoped query and operating on cells in inactive tabs. Also `flyFadePrev` grows unbounded (4.6 / 6.x).

**Suggested improvement:** scope the query to the active page (or to the just-rendered container, passed in). Prune `flyFadePrev`. If 5.2 lands, the crossfade hack can largely go away.

**Expected benefit:** smaller query + no leak. **Impact 3 / Effort 3 / Risk 3.**

---

## 5.5 Twice-per-poll upcoming sweep

Covered in Phase 2.8: `runFlyMatchSweep` walks `ALL_UPCOMING` twice per sweep, and `ledgerPredict` can trigger a dashboard render mid-sweep. **Est. gain: halves predictor sweep cost; removes mid-sweep renders.** **Impact 5 / Effort 3 / Risk 3.**

---

## 5.6 Timers / listeners inventory

| Timer/listener | Where | Note |
|----------------|-------|------|
| `pollTimer` (single self-rescheduling) | `3327` | clean; guarded by `isPolling` |
| `setInterval(renderFreshness, 30s)` | `6238` | cheap; gated by `!document.hidden` |
| `visibilitychange` -> immediate poll | `6239` | good |
| pull-to-refresh touch listeners x3 pages | `3703-3720` | per-page; fine |
| global touchstart/touchend | `3650/3661` | fine |
| brightness fade `setTimeout` | `4972` | fine |
| score-flash `setTimeout` x changed cell | `3093` | bounded by changed cells |
| SW message + load listeners | `6249/6252` | fine |

**Finding:** no leaked intervals or duplicate loops. The timer design is sound. **Impact 1.**

---

## 5.7 localStorage / snapshot usage

**Current implementation:** `saveSnapshot` (`3106`) serialises `ALL_LIVE` + 250 upcoming + 300 results to `localStorage` **every successful poll** (`3206`, `3272`). `JSON.stringify` of up to ~550 match objects every 1-4s while live.

**Cost:** `localStorage` is synchronous and main-thread; stringifying hundreds of objects every second (Fly Mode/FlyTime tier) blocks the main thread briefly each poll. The snapshot only needs to be fresh enough for the *next launch*, not updated every second.

**Suggested improvement:** throttle `saveSnapshot` to at most every ~15-30s (a `lastSnapshotMs` guard), independent of poll tier. Live scores 15s stale at launch are corrected by the first poll anyway (the `SNAPSHOT_LIVE_MS=15min` design already tolerates staleness, `3105`).

**Expected benefit:** removes a synchronous serialise+write from the hot 1s/3s path. **Impact 5 / Effort 2 / Risk 2.**

Other storage: form cache `v5` (6h TTL, `3337`), ledger, flyTimeMatches, favs - all reasonable, all pruned except the in-memory `flyFadePrev`.

---

## 5.8 Battery / network

**Current implementation:**
- Full sweep = 48 feeds via `Promise.allSettled` (`3146`); fast lane = live feeds only.
- `espnFetch` (`1281`) tries last-good proxy first (4.5s), else races 4 others (8s); cache-busts with `_=Date.now()` (`1287`) so nothing is cached.
- Fly Mode holds a 1s poll tier + `wakeLock` (`4938`) + fullscreen.

**Cost / critique:**
- The **1s Fly Mode tier** (`FLYMODE_POLL=1000`, `3321`) means up to one full live-feed fetch *per second* per live feed, plus full grid rebuild + crossfade + snapshot write, with the screen forced on (wakeLock). This is the heaviest battery/network state by far. ESPN scoreboard rarely updates sub-second; 1s polling mostly returns identical data.
- `anyStartingSoon` (`3309`) keeps a 30s tier when a game is <=30 min away even if nothing is live - reasonable.
- Cache-busting defeats the SW's network-only passthrough caching intentionally (correct for live data) but also defeats any 304 reuse.

**Suggested improvement:** raise the Fly Mode tier from 1s to ~2-3s (still "instant" to the eye, halves the work and radio wakeups), and/or only fast-poll feeds whose matches are actually progressing. Decouple snapshot writes from poll cadence (5.7).

**Expected benefit:** materially lower battery drain in the marquee Fly Mode use case. **Impact 6 / Effort 2 / Risk 3** (verify the board still feels live).

---

## 5.9 `flyFadePrev` unbounded growth

Covered in 4.6/6.x: `flyFadePrev` (`1832`) is never pruned. **Impact 2 / Effort 1 / Risk 1** - prune alongside `flyState`.

---

## 5.10 `prefers-reduced-motion` incomplete

Covered in 4.5. **Impact 3 / Effort 2 / Risk 1.**

---

## Phase 5 summary (with rough gain estimates)

| # | Finding | Est. gain | Impact | Effort | Risk |
|---|---------|-----------|:--:|:--:|:--:|
| 5.1 | Ship `DEBUG_FLY=false` | Removes O(45xUPCOMING) + per-card debug every poll | 9 | 1 | 1 |
| 5.2 | Keyed card diff instead of innerHTML rebuild | Large layout/paint + img-decode cut | 8 | 7 | 6 |
| 5.8 | Fly Mode 1s -> 2-3s tier | Big battery/network cut in Fly Mode | 6 | 2 | 3 |
| 5.3 | Cache logo probe by src | Removes dozens of getImageData/poll | 6 | 3 | 2 |
| 5.5 | Single-pass sweep | Halves predictor sweep | 5 | 3 | 3 |
| 5.7 | Throttle snapshot writes | Removes sync write from hot path | 5 | 2 | 2 |
| 5.4 | Scope flyCrossfade query | Smaller query, no leak | 3 | 3 | 3 |
| 5.10 | Extend reduced-motion | Accessibility | 3 | 2 | 1 |
| 5.9 | Prune flyFadePrev | Memory | 2 | 1 | 1 |

**Note on sequencing:** 5.1 alone removes most of the avoidable per-poll cost for one trivial edit. 5.2 is the big structural win but the riskiest (must preserve locked card markup). 5.8/5.7/5.3 are cheap, independent, high-value.
