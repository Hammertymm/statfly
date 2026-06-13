# Phase 6 - Data Flow & State Management

---

## 6.1 State ownership

| State | Declared | Owner / writer | Lifetime |
|-------|----------|----------------|----------|
| `ALL_LIVE` | `index.html:3747` | `loadLiveData` (replace), `refreshLiveFeeds` (filter+concat) | in-memory, per session |
| `ALL_UPCOMING` | `3942` | `loadLiveData` (replace), sorted by `eventMs` | in-memory |
| `ALL_RESULTS` | `3945` | `loadLiveData` (replace), `refreshLiveFeeds` (unshift new) | in-memory |
| `flyState` | `1825` | `updateFlyState`/`updateCricketFly`/`updateFlyTime2` | pruned each poll (`3077`) |
| `lastScores` | `1737` | `applyScoreFlashes` | pruned each poll (`3077`) |
| `flyFadePrev` | `1832` | `flyCrossfade` | **never pruned** (leak) |
| `flyTimeMatches` | `1996` | `markFlyTimeMatch` | localStorage, 35-day prune |
| `flyLedger` | `2039` | ledger fns | localStorage, 35-day prune |
| snapshot | `3103` | `saveSnapshot`/`hydrateSnapshot` | localStorage, 6h/15min TTL |
| form cache `v5` | `3337` | `loadTeamForm` | localStorage, 6h TTL |
| `favs` | `4686` | user actions | localStorage |
| `flytimeAlerted`, `notifiedMatchIds` | `3789`, n/a | notification fns | localStorage |

**Finding 6.1:** ownership is mostly clean and single-writer. The one in-memory state that is never pruned is `flyFadePrev` (Phase 4.6/5.9). **Impact 2 / Effort 1 / Risk 1.**

---

## 6.2 Duplication / redundancy

- `flyTimeMatches` (red-fly set) and `flyLedger[id].rf/a` (ledger) both record "reached FlyTime"; `syncFlyLedgerFromResults` reconciles them (`2443`). Two stores for one fact, kept in sync by a function - acceptable but a latent drift source.
- `AFL_TEAMS` (`1450`, display names) and `AFL_RESEARCH_NAMES` (`5401`, table-lookup names) are two separate AFL name maps; divergence silently drops a team from its v1 table (Phase 3.5).
- `homeScore`/`awayScore` (string) and `hInt`/`aInt` (parsed) both live on the match (`1641/1644`); intentional (display vs math) and fine.

**Impact 3 / Effort 2 / Risk 2.**

---

## 6.3 Fast-lane vs full-sweep merge correctness

**Current implementation** (`refreshLiveFeeds` `3229-3274`):
- Keeps live matches from *non-refreshed* feeds, swaps in fresh ones for refreshed feeds (`3254-3255`) - correct.
- Newly-finished games are `unshift`ed into `ALL_RESULTS` with an id-dedupe (`3258-3261`) - correct.
- `pruneResultsOfLive()` after (`3265`) - correct.

**Issues:**
1. **Upcoming is never updated in the fast lane** (by design, `3227` comment). So a game that kicks off between full sweeps stays in `ALL_UPCOMING` (and may also appear live) until the next full sweep (every `FULL_EVERY=15` fast cycles, ~1 min at 4s). The feed could briefly show the same fixture as both upcoming and live. `pruneResultsOfLive` does not cover the live-vs-upcoming overlap. **Impact 3 / Effort 3 / Risk 3.**
2. **Results window inconsistency:** fast lane keeps finished games for `RESULTS_MS = 7 days` (`3233`) while the full sweep keeps `WIN_MINE_BACK = 30 days` (`3141`). A just-finished My-Teams game added via the fast lane uses the 7-day rule; harmless because the display layer re-trims, but the two paths use different constants. **Impact 1 / Effort 1 / Risk 1.**

---

## 6.4 `pruneResultsOfLive`

`pruneResultsOfLive` (`1349`) removes any result whose id is currently live. Correct and called in both paths (`3195`, `3265`). It does **not** prevent a match being in both `ALL_LIVE` and `ALL_UPCOMING` (6.3.1). **Impact 2 / Effort 2 / Risk 2.**

---

## 6.5 Cache invalidation / TTLs

| Cache | TTL | Assessment |
|-------|-----|-----------|
| snapshot upcoming/results | 6h (`3104`) | reasonable |
| snapshot live | 15 min (`3105`) | good - live goes stale fast |
| form cache v5 | 6h (`3336`) | reasonable for schedules |
| flyTimeMatches / ledger | 35 days | matches results window |
| SW shell | versioned by `CACHE` bump | correct, but see drift (cache is v131) |

**Finding:** TTLs are well chosen. The form cache self-heals on schema bump (v4->v5). No invalidation bug found. **Impact 1.**

---

## 6.6 Race conditions

1. **Async form fetch mutates match objects mid-render.** `loadTeamForm` (`3470`) writes `m.homeForm/m.homeMargins` onto live `ALL_UPCOMING` objects asynchronously, then a sweep/render reads them. Because JS is single-threaded and the writes happen in promise callbacks between renders, this is not a data race in the threading sense, but a *rendered* card can show a yellow fly that appears/disappears a beat after the card paints when form lands. The code accepts this (repaints on form load). Low harm. **Impact 2 / Effort 3 / Risk 3.**
2. **`isPolling` guard** (`3287`) correctly prevents overlapping poll cycles. Good.
3. **`visibilitychange` immediate poll** clears the timer and calls `pollTick` only if `!isPolling` (`6240`) - correct.
4. **`espnFetch` race-and-abort** (`1296-1326`): the loser aborts are best-effort; a slow loser that resolves after `done` is ignored via the `done` flag. Correct.

**Finding:** no true race conditions; the guards are sound. The only observable artefact is late-arriving form changing a fly icon after paint.

---

## 6.7 Redundant storage / simplification

- Snapshot writes every poll (Phase 5.7) - throttle.
- `flyFadePrev` leak (6.1) - prune.
- Two AFL name maps (6.2) - unify or add a sync assert.
- Two "reached FlyTime" stores (6.2) - acceptable; document the sync responsibility.

---

## 6.8 My Teams matching inconsistency (real bug)

**Feed/Results** filter via `teamMatch` (`4612`) = exact OR substring both ways. **Fly Mode** filters via `favNames.includes(m.home.toLowerCase())` (`4840`) = exact only. So a followed team whose ESPN display name differs from the stored name (the exact case `teamMatch`'s substring logic exists to handle, and which `favMatchNames` augments with halo-config alias `names`, `4602-4606`) can appear in the Feed but be **missing from Fly Mode**.

**Suggested improvement:** Fly Mode should use the same `teamMatch(m, favNames)` as the Feed.

**Expected benefit:** consistent My Teams membership across the app; fixes a "my game is in the feed but not on the big screen" bug. **Impact 5 / Effort 2 / Risk 2.**

---

## Phase 6 summary

| # | Finding | Impact | Effort | Risk |
|---|---------|:--:|:--:|:--:|
| 6.8 | Fly Mode uses exact match, Feed uses substring - inconsistent membership | 5 | 2 | 2 |
| 6.3.1 | Kicked-off game can sit in live+upcoming until next full sweep | 3 | 3 | 3 |
| 6.2 | Two AFL name maps; two "reached" stores | 3 | 2 | 2 |
| 6.1/6.7 | `flyFadePrev` never pruned | 2 | 1 | 1 |
| 6.6.1 | Late form mutates card after paint (cosmetic) | 2 | 3 | 3 |
| 6.3.2 | Fast-lane vs full-sweep results window constant mismatch | 1 | 1 | 1 |
