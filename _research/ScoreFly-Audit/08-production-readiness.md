# Phase 8 - Production Readiness

---

## 8.1 Reliability

**Strengths:**
- Single self-rescheduling poll loop, no overlapping intervals, `isPolling` guard (`3287`), error-swallowed so the loop never dies (`3299`).
- Proxy racing + last-good memory + persistence (`1281`, `1276`).
- Connection banner + freshness line surface outages honestly (`1674`, `1696`).
- Snapshot hydrate gives an instant, honest-about-staleness first paint (`3116`).
- `pruneResultsOfLive` + `espnStatus` (v82) fixed the dual-listing and NRL-instant-finish bugs.

**Weaknesses:**
- `DEBUG_FLY = true` shipped (`2013`) - debug readouts on every card, lab forced on, heavy per-poll dashboard (Phase 5.1). **This is a release blocker by the project's own definition.**
- Live-vs-upcoming overlap window between full sweeps (Phase 6.3.1).
- Fly Mode 1s tier + wakeLock is a battery risk (Phase 5.8).

---

## 8.2 Error handling

- Network: every fetch path has timeout + try/catch + null-return; `coveredSports.size===0` triggers retry (`3171`). Good.
- Storage: all `localStorage` access is try/caught. Good.
- Rendering: `renderResults` wraps in try/catch (`4659`); `renderHome` does not, but its inputs are controlled.
- Canvas probe: try/catch, no-ops on CORS failure (`4333`). Good.
- **Gap:** no global `window.onerror`/`unhandledrejection` handler, so a render exception is silent to the developer in production (DEBUG logging is off unless `scorefly_debug=1`). For a no-test-suite codebase, a lightweight error beacon would help.

---

## 8.3 Offline behaviour

- SW cache-first for shell, network-only for data/fonts (`sw.js:107-141`) - correct strategy.
- Snapshot hydrate paints last-known scores offline (`3116`).
- **Gap:** if all proxies fail at launch with no snapshot (first run offline), the user sees an empty feed + connection banner - acceptable, ESPN-only doctrine forbids mock data.
- Cache version bumping is manual and currently drifted (doc says v115/v129, code v131) - a process risk, not a code bug.

---

## 8.4 Data-failure recovery

- Partial feed coverage: whatever returns is shown; missing feeds just have no cards. Reasonable.
- Stale data: freshness line + amber "reconnecting" (`1704`). Honest.
- Form/margins not loading: surfaced in the lab's margin-coverage line (`2519`), but only visible to lab users.

---

## 8.5 Monitoring / logging / observability

- Debug logging is opt-in via `localStorage.scorefly_debug=1` (`1121`) - off in production, so **there is essentially no production observability**: no error reporting, no analytics, no way to know if FlyTime detection ever fired in the field (the core open question).
- The FlyTime Lab ledger is the only telemetry, and it is local-only and per-device.
- **This is the biggest readiness gap after `DEBUG_FLY`:** the team cannot answer "did a green fly ever appear for a real user?" without a beacon. A privacy-light, opt-in, fire-once event (e.g. "isFlyTime fired" count) would unblock the Phase 3 validation problem at scale.

---

## 8.6 The unverified-FlyTime-detection blocker

Restated from Phase 3.2 because it is a release-readiness item: the product's headline feature has never been confirmed to fire live. Until a single watched close finish produces a green-then-red fly (or a beacon proves it in the field), the core promise is unverified. **This is the top production-readiness blocker alongside `DEBUG_FLY`.**

---

## 8.7 Code quality / maintainability

- One 5,775-line file with ~5,140 lines of inline JS. Enforced by the single-file hard rule, so this is a *constraint*, not a defect - but it makes the file hard to navigate and impossible to unit-test in isolation. Mitigations: the code is well-commented and sectioned, and offline Python tooling carries the testable logic.
- Duplicated v1 formula across 11 files (Phase 2.7).
- Three predictor layers with doc drift (Phase 3.1).
- Two AFL name maps (Phase 6.2).
- ASCII-only-in-`<script>` rule respected (the code uses `\u` escapes and HTML entities, e.g. `&#129712;` for the fly fallback `5715`).

---

## 8.8 Readiness scores (/10)

| Dimension | Score | Rationale |
|-----------|:-----:|-----------|
| **Architecture** | 7 | Clean single-file design within tight constraints; poll loop, proxy strategy, SW, snapshot all well-built. Loses points for three accreted predictor layers and per-poll full rebuilds. |
| **Performance** | 5 | Strong ideas (tiered polling, batched reflow, deep-window selectivity) undercut by `DEBUG_FLY=true` dashboard every poll, wholesale innerHTML rebuilds, per-poll canvas probe, 1s Fly Mode tier, per-poll snapshot writes. Most are cheap to fix. |
| **Scalability** | 3 | Static hosting scales; the data path (free proxies + O(users x feeds) direct polling) caps in the low thousands of actives. No path beyond that without a backend. |
| **Prediction Systems** | 3 | Sophisticated machinery, but the core detector has never been confirmed live, calibration targets the wrong label, and the stack is unvalidated/unmeasurable. High potential, unproven. |
| **Code Quality** | 6 | Well-commented, consistent style, ASCII-safe, good guards. Held back by duplication, doc/code drift, debug flag shipped, one giant file. |
| **Maintainability** | 5 | Single-file constraint + duplicated formulas + manual threshold sync + doc drift make changes error-prone; offline Python tooling and the decisions log help. |
| **User Experience** | 7 | Genuinely strong: instant snapshot paint, honest freshness, FlySense colour language, Fly Mode, clean onboarding. Debug scores currently leak onto every card (regression once `DEBUG_FLY=false`). |
| **Production Readiness** | 4 | Two hard blockers: `DEBUG_FLY=true` shipped and FlyTime detection unverified. Plus no production observability. All addressable. |

**Overall:** a polished, thoughtfully-built product whose *engineering fundamentals are good* but which is **not currently in a shippable-for-scale state** for two concrete, mostly-cheap reasons (debug flag + unverified core feature) and one structural one (no backend path beyond a few thousand actives).

---

## Phase 8 summary

| # | Finding | Impact | Effort | Risk |
|---|---------|:--:|:--:|:--:|
| 8.1/5.1 | `DEBUG_FLY=true` shipped - release blocker | 9 | 1 | 1 |
| 8.6/3.2 | FlyTime detection never verified live - core-feature blocker | 10 | 4 | 2 |
| 8.5 | No production observability / error beacon | 6 | 4 | 3 |
| 8.2 | No global error handler | 3 | 2 | 2 |
| 8.3 | Manual cache-version bump drifted | 2 | 1 | 1 |
