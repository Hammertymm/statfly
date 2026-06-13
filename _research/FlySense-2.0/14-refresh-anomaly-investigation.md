# 14 — Score Update Validation & False Positive Investigation

**Issue:** After a prolonged period without score updates (API gap, backgrounded tab, failed poll cycle), the next refresh can deliver a **batched score jump**. FlySense 1.0/2.0 treated the entire delta as a single poll burst, which could spike momentum to on fire / extreme red (`fs-xfire`) even when the scoring was spread over minutes of real game time.

**Status:** Vulnerability confirmed in pre-fix code. **Mitigations shipped** in `index.html` (clock-gap validation + gain spreading + confidence).

---

## 1. Root cause (pre-fix behaviour)

Per poll, momentum gain was:

```
gain = min(scoreDelta / bigPlay, 1.6) * MOM_GAIN
```

- **No normalization by elapsed time** — 18 points after a 3-minute silence looked identical to 18 points in one 4-second poll.
- **Decay used wall-clock `dt`** (clamped to 120s) but **gain ignored `dt` and game clock**.
- **`flyState` did not store game clock** — no way to cross-reference score vs clock progression.
- **Trailing-window acceleration** used raw `hDelta`/`aDelta`, so batched jumps also polluted velocity/acceleration.

This is **not** a FlyTime (coloured fly icon) calculation bug — red flies come from `matchHadFlyTime` / live clutch detection. Batched scores can still move a game *into* a close margin on one refresh (separate FlyTime edge case). This document focuses on **FlySense momentum** (score colour / intensity).

---

## 2. Key questions — answers

| Question | Answer |
|---|---|
| Can large score increases be cross-referenced against elapsed game time? | **Yes**, for most team sports. ESPN provides `period`, `displayClock` → `clockSec` / `clockRaw` on every live match object. Stored in `flyState` as `period`, `clockSec`, `clockRaw` each poll. |
| Can FlySense distinguish genuine bursts vs delayed refreshes? | **Yes, probabilistically.** Compare `pollDt` (wall) vs `gameElapsed` (clock). If scores jump but clock barely moves during a long `pollDt` → batched/stuck clock → low confidence. If clock advanced with the gap → spread gain over game time. |
| Should clock and score be analysed together? | **Yes.** Gain is now spread over `spreadDt` derived from both clocks, not applied as one instantaneous burst. |
| Can refresh anomaly detection flag batched updates? | **Yes.** `pollDt >= 90s` triggers scrutiny; clock/score mismatch lowers `confidence` to 0.35–0.6. |
| Should momentum normalize when gaps are large? | **Yes.** `burst = (delta/bigPlay) / (spreadDt/60)` capped at 1.6, instead of raw `delta/bigPlay`. |
| Can confidence scoring reduce certainty after long gaps? | **Yes.** `hConf`/`aConf` stored per side; `fs-xfire` blocked when `confidence < 0.55`. |

---

## 3. What data exists (no play-by-play)

| Signal | Available? | Used for |
|---|---|---|
| Score integers (`hInt`/`aInt`) | Yes | Delta |
| Game period | Yes | Period transitions |
| Game clock (`clockSec`, soccer minute) | Yes (not baseball/cricket primary) | `flyGameElapsedSec` |
| Poll wall time (`prev.ts`) | Yes | Decay + stale detection |
| Play-by-play / event stream | **No** in client | Momentum reconstruction not viable without new fetch |
| Cricket overs / wickets | Yes (linescores) | Run-rate engine + stale overs check |

**Momentum reconstruction (solution 3)** from play-by-play is **not** available in the current ESPN scoreboard-only path. The FlyTime engine backfill could supply historical timelines later ([11-historical-validation-framework.md](./11-historical-validation-framework.md)) but that is a separate build.

---

## 4. Implemented mitigations (shipped)

### 4.1 Clock gap validation — `flyGameElapsedSec(m, prev)`

Computes seconds of **game time** between polls:

- **Countdown sports** (NBA, NFL, NHL, rugby): remaining clock decreases; handles period advances via `FLY_PERIOD_CLOCK_SEC`.
- **AFL**: clock counts up (elapsed = `c1 - c0` within period).
- **Soccer**: match minute from `clockRaw` × 60.
- **Baseball**: inning delta × ~180s estimate when clock meaningless.
- **Cricket**: overs delta in `updateCricketFly` (not `flyGameElapsedSec`).

### 4.2 Refresh anomaly detection — `flyGainAndConfidence`

When `pollDt >= 90s` and scoring occurred:

| Condition | `confidence` | `spreadDt` |
|---|---|---|
| `gameElapsed / pollDt < 0.25` (score jumped, clock stuck) | 0.35 | `pollDt` (wall) |
| ratio 0.25–0.55 | 0.6 | blended |
| ratio ≥ 0.55 (clock moved with outage) | 1.0 | `gameElapsed` |
| No usable clock | 0.55 | `pollDt` |

Gain:

```
spreadDt = max(spreadDt, 20s)
gain = min((delta/bigPlay) / (spreadDt/60), 1.6) * MOM_GAIN * confidence
```

Trailing-window history uses **spread-normalised pseudo-deltas** so acceleration is not poisoned by one batched jump.

### 4.3 Confidence decay

`flyState` stores `hConf`, `aConf` per poll. Low confidence:

- Reduces momentum **gain** (multiplier on burst).
- Blocks **Extreme On Fire** (`fs-xfire`) unless `confidence >= 0.55`.
- Does **not** hide legitimate sustained runs once normal polling resumes (confidence returns to 1.0).

### 4.4 Cricket stale path

If `pollDt >= 90s` and runs increased but overs advanced &lt; 0.15 → `confidence 0.35`. Overs advanced ≥ 0.5 → full confidence (run rate already time-normalised).

---

## 5. Example scenarios (post-fix)

| Scenario | pollDt | gameElapsed | delta | Pre-fix gain factor | Post-fix |
|---|---|---|---|---|---|
| Genuine NBA 8-0 in 30s | 4s | 30s | 8 | min(8/6,1.6)=1.33 | min(8/6/(30/60),1.6)×1 ≈ 0.67 |
| Stale refresh, real 12pt over 3min | 180s | 180s | 12 | min(12/6,1.6)=1.6 | min(12/6/(180/60),1.6)×1 = 0.67 |
| Batched jump, clock stuck | 180s | 10s | 12 | 1.6 (false on fire) | min(12/6/(180/60),1.6)×0.35 ≈ 0.23 |
| Fast poll, no score | 4s | 4s | 0 | 0 | 0 |

---

## 6. Residual risks / future work

1. **ESPN clock granularity** — soccer minute is coarse; short bursts inside one minute still batch visually.
2. **Baseball** — no game clock; inning estimates only; stale polls rely on wall-time spreading + confidence penalty.
3. **Cricket `hInt`** — `parseInt("156/4")` = 156; wicket-only updates without runs changing `hInt` are invisible; overs/wickets paths handle most cases.
4. **FlyTime margin jumps** — a batched close score can still trigger green fly on that poll; FlyTime uses instantaneous margin + clock, not momentum history. Consider similar confidence gate if observed live.
5. **Play-by-play reconstruction** — best long-term fix for perfect momentum replay; requires new data path (engine backfill or secondary API).

---

## 7. Validation

- Structural: `scripts/check_js_balance.py`
- Stale burst math: extend `scripts/sim_flysense2.py` with `flyGainAndConfidence` scenarios
- Live: watch FlyTime Lab / debug momentum after returning from background mid-game

---

## 8. Recommendation summary

| Solution | Verdict |
|---|---|
| 1. Clock gap validation | **Shipped** — `flyGameElapsedSec` |
| 2. Refresh anomaly detection | **Shipped** — stale `pollDt` + clock/score ratio |
| 3. Momentum reconstruction (PBP) | **Deferred** — no client PBP today |
| 4. Confidence decay | **Shipped** — `hConf`/`aConf`, gain scaling, xfire gate |
| 5. Fly protection logic | **Shipped** for extreme fire; FlyTime icon separate |

FlySense now measures **time-normalized scoring rate** with explicit uncertainty after abnormal gaps, while preserving fast response to genuine short-window bursts during normal polling.
