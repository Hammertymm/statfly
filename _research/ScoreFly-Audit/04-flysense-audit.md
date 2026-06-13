# Phase 4 - FlySense Audit

FlySense colours live score cells by momentum (8 states + continuous gradient). It is the most computationally intensive subsystem and runs for every live match every poll.

---

## 4.1 Momentum / decay / gain

**Purpose:** a 0-100 per-side momentum that rises on scoring bursts and decays smoothly.

**Current implementation:**
- Gain: `flyGainAndConfidence` (`2685`) - spreads a score burst over elapsed *game* time, clamps the burst to 1.6x `MOM_GAIN`, applies a confidence penalty after stale polls.
- Decay: `flyHalflife` (`2633`) - per-sport base half-life (`FLY_TUNING` `1747`), stretched up to 1.8x by run persistence, nudged by held tier.
- Applied in `updateFlyState` (`2795-2805`) with acceleration + ember boosts (`2783-2811`).

**Cost:** per live match per poll, this also builds and scans a trailing `hist` window (`2773-2790`): filter + push + a full loop computing recent/prior sums for acceleration and scoring share. `hist` holds up to `MOM_WINDOW_SEC=180`s of entries; at the 1s Fly Mode tier that is up to ~180 entries scanned per match per second.

**Accuracy:** the clock-validated spread (the v-anomaly fix) is genuinely good engineering - it correctly distinguishes a real burst from a batched refresh. The math is internally consistent.

**Critique:** the *richness* (acceleration + ember + peak + suppression share + persistence anchors) is a lot of machinery for a colour that the user reads in under a second. The acceleration term (`2786`) and suppression share (`2789-2791`) are second-order signals whose visible effect (a slightly faster/brighter ramp) is hard to perceive on a small cell. This is the prime FlySense *simplification* target: the visible output is a single colour; several of the scalar inputs do not change that colour enough to justify their per-poll cost.

**Suggested improvement:** keep momentum + dynamic decay + ember; consider dropping the acceleration/suppression/peak-collapse terms (or computing them only off the Fly Mode 1s tier) and measure whether the colour visibly changes. **Impact 4 / Effort 4 / Risk 4** (it is tuned; needs a careful before/after).

---

## 4.2 8-state transitions + `resolveSide` priority

**Current implementation** (`resolveSide` `2857`): priority comeback > heat tier (onfire/onrun/warming) > cold > neutral. Comeback and cold each have entry/exit hysteresis (`cbMomFloor` `2864`; cold `relative`/`absolute` with `wasCold` band `2896-2899`).

**Critique:**
- Priority order is sensible and matches the doc.
- Comeback condition (`2865-2868`) requires four simultaneous truths; correct but means comeback rarely shows except in textbook cases - acceptable for a rare-by-design state.
- Cold has two independent triggers (relative stall + absolute drought `2897-2899`); the absolute one needs `deficit > 0 && oppMom >= 25`, so a team that stops scoring while *level* never goes cold. Intentional but worth noting.

**Accuracy:** logically sound. No correctness bug found.

**Impact 2 / Effort 3 / Risk 4.** Leave the state machine; it is the stable core.

---

## 4.3 Continuous gradient ramps

**Current implementation:** `rampColour` (`1888`) with smoothstep interpolation over `FLY_RAMP_HEAT/COLD/CB` (`1903-1921`); `flyHeatColour/flyColdColour/flyCbColour` (`1922-1924`). Heat starts at momentum 12 (below that, no colour, `1922`).

**Critique:**
- Both hue and luminance rise with intensity (`1886-1887` comment) - good for colour-blind/glare robustness.
- The ramps are well chosen and cheap (a handful of lerps). No change.

**Impact 1 / Effort 1 / Risk 1.** This part is a clean win; keep as-is.

---

## 4.4 Hysteresis bands (`MOM_BANDS`)

**Current implementation** (`1868-1881`): onfire 70/64, onrun 45/40, warming 20/16, with a "held" check so a tier sticks until it drops below its exit. Correct hysteresis; labels will not chatter at a boundary, while the colour stays continuous. This is the right separation (label vs colour). No change. **Impact 1 / Effort 1 / Risk 1.**

---

## 4.5 `resolveSide` extreme triggers + `fs-xfire`/`fs-xcold`

**Current implementation:** extreme fire needs `mom >= 90 && conf >= 0.55` (`2888`); extreme cold needs `mom <= 10 && sev >= 0.75 && droughtFactor >= 0.4` (`2910`). CSS `fs-xfire`/`fs-xcold` (`index.html:193-203`).

**Critique:** correctly additive (one effect per cell), gated by confidence so a stale-refresh spike does not pulse. Good.

**`prefers-reduced-motion` gap:** the media query (`index.html:204-206`) disables only `fs-xfire`, `flymode-score.fs-xfire`, and `flymode-score.fs-flytime`. It does **not** cover:
- `flyLikelyFlash` (the FLY2 "likely" flashing fly, `246`),
- `flyPulse` on the onboarding badge (`394`) and Fly Mode flytime score on feed (`.sc.fs-flytime` has no pulse, ok),
- `scoreFlash` (`169`),
- `pulse` (the live dots / live badge, `73`, `102`, `58`).

So a reduced-motion user still sees the flashing "likely" fly and pulsing dots. **Impact 3 / Effort 2 / Risk 1** - extend the media query.

---

## 4.6 `fs-xfire`/`fs-xcold` + `flyCrossfade` reflow cost

`flyCrossfade` (`1833`) implements the cross-fade by snapping each changed cell to its previous colour, forcing one document reflow (`void document.body.offsetWidth`, `1854`), then swapping to the new colour so the 2.5s CSS transition runs. This is clever and uses a single batched reflow (good), but:
- It runs a **document-wide `querySelectorAll('[data-fk]')`** every render (`1834`), matching every score cell on every tab, not just visible/changed ones.
- `flyFadePrev` (`1832`) is keyed by `matchId|side|cell` and **never pruned** - it grows for every match ever rendered in the session. Over a long session across many feeds this is a slow memory leak (small per entry, but unbounded). Contrast with `flyState`/`lastScores`, which *are* pruned (`3077-3079`).

**Suggested improvement:** scope the query to the active page container, and prune `flyFadePrev` alongside `flyState`. **Impact 3 / Effort 3 / Risk 3.** (More in Phase 5/6.)

---

## 4.7 Confidence gating

Covered in 4.1/4.5: confidence correctly suppresses extreme effects after stale/batched refreshes (`2888`, `cricketStaleConf` `2943`). This is a genuine quality feature and should be kept. **Impact n/a (keep).**

---

## 4.8 Cricket: cold/comeback disabled

`updateCricketFly` (`2930`) writes `hState=hTier`/`aState=aTier` directly (`3011`) - i.e. only heat tiers, never cold/comeback. Correct per design (innings scores make deficit logic meaningless). The run-rate engine is well-commented. See Phase 2.10 for the wall-clock-over caveat. **Impact 2 / Effort 3 / Risk 3.**

---

## 4.9 Per-poll compute summary (the real FlySense cost)

For each live match, every poll, FlySense runs:
- `updateFlyState`: deltas, `flyGameElapsedSec`, `flyGainAndConfidence`, `hist` filter+push+scan (up to 180 entries), two decays, two ember/peak updates, two `resolveSide` (each doing tier + comeback + cold maths), object rebuild (`2731-2851`).
- `updateFlyTime2`: window + base/mom/ctx/rate + EMA + stage (`2209-2242`).

At the **1s Fly Mode tier with up to 8 live matches**, that is ~8x(updateFlyState + updateFlyTime2 + hist scan) every second, plus a full grid `innerHTML` rebuild and `flyCrossfade`. This is the worst-case CPU/battery path and is examined in Phase 5.

**Signal vs noise:** the *visible* output is one colour per cell that the user glances at. Much of the scalar richness (4.1) does not change that glance. The recommendation is not to gut FlySense - the core (momentum + decay + 8 states + gradient + hysteresis) is excellent and on-brand - but to **trim the second-order terms and/or compute the expensive `hist`-window analytics at the slower live tier rather than the 1s Fly Mode tier**, where nobody is reading acceleration nuance across a room.

**Impact 5 / Effort 4 / Risk 4.**

---

## Phase 4 summary

| # | Finding | Impact | Effort | Risk |
|---|---------|:--:|:--:|:--:|
| 4.9/4.1 | Trim 2nd-order momentum terms / throttle hist analytics off the 1s tier | 5 | 4 | 4 |
| 4.6 | `flyCrossfade` document-wide query + unbounded `flyFadePrev` | 3 | 3 | 3 |
| 4.5 | `prefers-reduced-motion` misses likely-flash, pulse, scoreFlash | 3 | 2 | 1 |
| 4.2/4.3/4.4 | State machine, ramps, hysteresis - keep as-is | 1 | - | 1 |
| 4.8 | Cricket run-rate engine - keep, minor over-fallback | 2 | 3 | 3 |
