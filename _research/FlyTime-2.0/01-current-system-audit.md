# Phase 1 — Current System Audit

A complete forensic reverse-engineering of the FlyTime system as it exists today. Everything here is traced to source in [scorefly/index.html](../../scorefly/index.html), [scorefly/flytime-engine/](../../scorefly/flytime-engine/), and the 45 `*-flytime-v1.json` tables.

---

## 1. There are two FlyTime engines, not one

FlyTime is two separate systems that share a name and a UI motif but never share a calculation:

| | **Yellow engine** (prediction) | **Green engine** (live detection) |
|---|---|---|
| Question | "Could this *upcoming* match be close?" | "Is this match close *right now*?" |
| Where | `computeFlyMatch` + `FLY_V1_REGISTRY` | `isFlyTime(m)` (index.html:1949) |
| Inputs | Historical tables (close rate, form, margin, matchup) | Live margin, period, clock |
| Output | `isFlyMatch` (bool) + `flyMatchRating` (0–100) | `isFlyTime` (bool) |
| Nature | Weighted score vs per-league threshold | Hard multi-condition gate |
| Timing | Before kickoff | During play |
| Ground truth used to tune | Final close margin (proxy) | None (rule is hand-set) |

The critical gap: **nothing predicts the live state**. The yellow engine stops at tip-off; the green engine only activates once the close finish is already visible. There is no system that says "this live match, currently not close, is *trending* toward a close finish." That missing middle is the whole point of FlyTime 2.0.

---

## 2. Green engine — live trigger logic (the reactive gate)

### 2.1 The full rule set

```js
// index.html:1949
function isFlyTime(m) {
  const margin = Math.abs((m.hInt || 0) - (m.aInt || 0));
  const p = m.period || 0;
  const c = m.clockSec || 0;          // seconds REMAINING in the period
  switch (m.sportKey) {
    case 'basketball':  return p >= 4 && c > 0 && c <= 300 && margin <= 8;
    case 'football':    return p >= 4 && c > 0 && c <= 300 && margin <= 8;
    case 'hockey':      return p >= 3 && c > 0 && c <= 300 && margin <= 1;
    case 'baseball':    return p >= 8 && margin <= 2;
    case 'australian-football':
      if (margin > 12) return false;
      if (p > 4) return true;                       // OT: close margin only
      return p === 4 && c >= AFL_FLY_Q4_ELAPSED_SEC; // c here = elapsed (20*60)
    case 'rugby-league':
      if (margin > 12) return false;
      if (p > 2) return true;                       // OT
      return p >= 1 && p <= 2 && c >= NRL_FLY_HALF_ELAPSED_SEC; // 35*60 elapsed
    case 'rugby':       return p >= 2 && c > 0 && c <= 600 && margin <= 12;
    case 'soccer': {
      const minute = parseInt(m.clockRaw, 10) || 0;
      return minute >= 80 && margin <= 1;
    }
    case 'cricket':     return isCricketFlyTime(m);
    default: return false;
  }
}
```

### 2.2 Decoded per-sport gate

| Sport | Time gate | Margin gate | Earliest possible green |
|-------|-----------|-------------|--------------------------|
| Basketball | Q4 (or OT), ≤ 5:00 remaining | ≤ 8 pts | 5:00 left in Q4 |
| Football (NFL/CFL/NCAAF) | Q4, ≤ 5:00 remaining | ≤ 8 pts | 5:00 left in Q4 |
| Hockey | Period ≥ 3, ≤ 5:00 remaining | ≤ 1 goal | 5:00 left in P3 |
| Baseball | Inning ≥ 8 | ≤ 2 runs | top of the 8th |
| AFL | Q4 with ≥ 20:00 *elapsed*, or any OT | ≤ 12 pts | ~partway through Q4 |
| Rugby League | ≥ 35:00 elapsed in a half, or any OT | ≤ 12 pts | ~35 min into a half |
| Rugby Union | 2nd half, ≤ 10:00 remaining | ≤ 12 pts | 10:00 left in H2 |
| Soccer | Minute ≥ 80 | ≤ 1 goal | 80' |
| Cricket | `isCricketFlyTime` (runs req ≤ 20, overs left ≤ 2) | — | last ~2 overs |

### 2.3 What this means

Every gate is a logical **AND of a late-clock condition and an already-tight-margin condition**. Consequences:

1. **It cannot fire early.** The earliest green for basketball is 5:00 left — and only if the margin is *already* ≤ 8. A taut game tied at the 8-minute mark shows nothing.
2. **It is binary.** Margin 8 → green; margin 9 → nothing. A 1-point difference in score flips the entire signal. There is no notion of "almost FlyTime".
3. **It is memoryless about trajectory.** Two matches both at margin 8 with 5:00 left are identical to the engine, even if one is a collapsing 25-point lead (high drama) and the other a stable nip-and-tuck (also drama, but different). It sees the snapshot, not the path.
4. **It treats clock as a wall, not a variable.** 5:01 left = nothing; 4:59 = eligible. The threshold is a cliff.

This is a *confirmation* detector dressed as a *prediction* feature.

---

## 3. Green engine — lock and exit behaviour

The raw gate is wrapped by three pinning functions that add persistence:

```js
// index.html:1990–2006
function flyTimeMargin(m){ return Math.abs((m.hInt||0)-(m.aInt||0)); }
function isFlyTimeBlowout(m){
  if(!m || !matchHadFlyTime(m.id)) return false;
  const max = FLY_BLOWOUT_MARGIN[m.sportKey];   // e.g. basketball 16
  if(max == null) return false;
  return flyTimeMargin(m) > max;
}
function isFlyTimePinned(m){
  if(!m || !m.id) return false;
  if(isFlyTime(m)) return true;                 // currently in FlyTime
  if(!matchHadFlyTime(m.id)) return false;      // never was
  return !isFlyTimeBlowout(m);                  // stay pinned unless it blew out
}
```

**Lock:** Once `isFlyTime()` returns true, `markFlyTimeMatch(id)` records the match id in `flyTimeMatches` (localStorage, pruned at 35 days). From then the match is *pinned* (stays surfaced) even if it briefly dips out of the raw gate.

**Exit / unpin:** Pinning is removed only if the margin **blows out** past `FLY_BLOWOUT_MARGIN` (roughly 2× the close threshold):

```js
FLY_BLOWOUT_MARGIN = { basketball:16, football:16, hockey:3, baseball:5,
  'australian-football':24, 'rugby-league':24, rugby:24, soccer:3 }
```

**Red fly (after-match):** Any match that was ever marked stays in `flyTimeMatches`, so completed games render a red fly on Results. This is the *only* persisted ground-truth signal in the whole system.

**Edge case in the lock model:** the blowout buffer means a game that touches margin 8 once (e.g. a garbage-time three) gets pinned and keeps the red fly forever, even if it immediately reverts to a 20-point gap and stays there. The lock has no "must sustain" requirement.

---

## 4. Yellow engine — pre-match prediction

### 4.1 The v1 scoring formula

```
score = close_rate×0.35 + form_balance×0.25 + margin_balance×0.25 + matchup×0.15
isFlyMatch = (score >= league.threshold)
```

(`FORMULA_VERSIONS.v1` in [config.py:193](../../scorefly/flytime-engine/flytime_engine/config.py); mirrored in `index.html`.)

Where, from each `*-flytime-v1.json`:
- `close_rate` — historical % of this matchup's games finishing within the sport's close margin.
- `form_balance = 100 − |form(home) − form(away)|` — how evenly matched current form is.
- `margin_balance = 100 − |avgMargin(home) − avgMargin(away)|` — typical scoring-margin similarity.
- `matchup` — historical average "excitement" rating for this specific pairing.

If any input is missing, the result is `None`/non-fly (no guessing). See [flytime.py:100–135](../../scorefly/flytime-engine/flytime_engine/flytime.py).

### 4.2 Thresholds

Per-league `threshold` lives in `FLY_V1_REGISTRY` (45 leagues; see [config.py:135](../../scorefly/flytime-engine/flytime_engine/config.py) and [StatFly_FlyTime_Threshold_Recommendations.md](../../scorefly/StatFly_FlyTime_Threshold_Recommendations.md)). Examples: NBA 88, NFL 95, AFL 75, NRL 85, EPL 96, CFL 70, WNBA 75. Leagues without a v1 table fall back to legacy `FLYMATCH_THRESHOLD` = 62 (with margins) / 82 (without).

Thresholds are calibrated offline by `scripts/calibrate_flytime.py` to a **volume** target (~2 yellow flies per round-chunk), **not** to a measured precision/recall against live outcomes.

### 4.3 The ledger

`flyLedger` (localStorage, `scorefly_fly_ledger_v1`, 35-day prune) records per match: predicted (`p`), achieved live (`a`), blue-fly hit (`bf`), finished (`fin`), red-fly (`rf`), plus the rating and threshold used. This is the intended feedback loop for tuning yellow against green. **Today it is effectively empty of outcomes** — the prior audit found every exported row was `p:1, a:0, fin:0`, meaning live FlyTime detection has not yet been confirmed flowing back into the ledger ([StatFly doc §1](../../scorefly/StatFly_FlyTime_Threshold_Recommendations.md)). The learning loop exists structurally but has never closed.

---

## 5. Data inputs — complete inventory

### 5.1 Inputs the green engine actually uses

| Input | Source field | Used by | Notes |
|-------|--------------|---------|-------|
| Score differential | `m.hInt`, `m.aInt` → `margin` | all sports | absolute value only |
| Period / quarter / inning | `m.period` | all | integer; OT detected as `p > regulation` |
| Clock remaining | `m.clockSec` | basketball, football, hockey, rugby | seconds **remaining** |
| Clock elapsed | `m.clockSec` reinterpreted | AFL, NRL | same field, opposite meaning (see §7.1) |
| Soccer minute | `parseInt(m.clockRaw)` | soccer | string parse; ignores stoppage `+` |
| Cricket runs required | `m.cricket_runs_req` | cricket | chase context |
| Cricket overs left | `m.cricket_overs_left` | cricket | chase context |
| Sport key | `m.sportKey` | dispatch | selects the rule branch |

### 5.2 Inputs the yellow engine uses

Pre-match only: `close_rate`, `form_strength`, `team_margin_rating`, `matchup_rating`, `matchup_close_rate` (all from the league JSON), plus the per-league `threshold`.

### 5.3 Inputs that exist in the app but FlyTime **ignores**

This is the most important part of the inventory, because it is the raw material for 2.0:

| Available signal | Where | Currently feeds FlyTime? |
|------------------|-------|--------------------------|
| Per-side momentum scalar (0–100) | FlySense `hMom`/`aMom` | **No** |
| FlySense state (warming/onrun/onfire/cold/comeback) | `hState`/`aState` | **No** |
| Largest deficit faced (comeback magnitude) | `hMaxDef`/`aMaxDef` | **No** |
| Recent peak momentum (collapse detection) | `hPeak`/`aPeak` | **No** |
| Scoring rate / drought | FlySense `droughtNorm`, burst calc | **No** |
| Pre-match yellow rating | `flyMatchRating` | **No** (yellow and green never talk live) |
| Lead history / trajectory | implied by polling, not stored | **No** |
| Home advantage | not modelled | **No** |

The app already computes a rich momentum picture every poll (FlySense), and a credible pre-match closeness estimate (yellow). The live FlyTime gate uses **none of it**. It reads three numbers (margin, period, clock) and branches. This is the single biggest opportunity surfaced by the audit.

---

## 6. Architecture & data flow

```
                        ┌─────────────────────────────────────────────┐
  ESPN feed  ──poll──▶  │ parse match → m {hInt,aInt,period,clockSec,…} │
  (8–60s)               └─────────────────────────────────────────────┘
                                   │                  │
                   ┌───────────────┘                  └───────────────┐
                   ▼                                                   ▼
        ┌──────────────────────┐                          ┌────────────────────────┐
        │ FlySense updateFly()  │  (momentum, states)      │  isFlyTime(m)  GREEN    │
        │  hMom/aMom, hState…   │  ── ignored by FlyTime ─▶ │  margin & period & clk │
        └──────────────────────┘                          └────────────────────────┘
                                                                       │ true
                                                                       ▼
                                                          markFlyTimeMatch(id) → pin
                                                                       │
                                                            isFlyTimePinned() until blowout
                                                                       │
                                                                       ▼
                                                          green fly UI / red on Results
                                                                       │
                                                                  ledger a:1 (intended)

  Pre-match:  FLY_V1_REGISTRY + *-flytime-v1.json ──▶ computeFlyMatch ──▶ YELLOW fly + rating
                                                              │
                                                       ledger p:1 (ledgerPredict)
```

### Polling cadence (config.py:216)

| Mode | Interval |
|------|----------|
| FlyTime live (`POLL_FLYTIME_SEC`) | 8 s |
| Fast (`POLL_FAST_SEC`) | 12 s |
| Idle (`POLL_IDLE_SEC`) | 60 s |
| Full resweep | every 15 fast cycles |

So the engine sees a live match roughly every 8–12 s while it is interesting. This cadence is more than fast enough for a continuous probability model — the data is being thrown away, not under-sampled.

### State management

- **In-memory:** parsed match objects, FlySense `flyState` per match.
- **localStorage:** `scorefly_flytime_matches` (red-fly memory, 35d), `scorefly_fly_ledger_v1` (predictor ledger, 35d), `scorefly_fly_lab` (debug flag).
- No server-side persistence of live trajectories — every match's history is lost between sessions. **2.0 needs at least a rolling in-session trajectory buffer** to compute rate/momentum-of-margin.

### Performance implications

- `isFlyTime()` is O(1), pure arithmetic — negligible cost, runs per match per poll.
- FlySense already does the heavier momentum maths every poll, so reusing its outputs adds **near-zero** marginal cost. A 2.0 probability model that consumes FlySense outputs is cheap.
- The main new cost in 2.0 is keeping a short rolling buffer of (t, margin, momentum) per live match — trivial memory.

---

## 7. Edge cases & failure modes

### 7.1 The `clockSec` polarity overload (latent bug class)
`clockSec` means **remaining** for basketball/football/hockey/rugby but is treated as **elapsed** for AFL (`c >= 20*60`) and NRL (`c >= 35*60`). This dual meaning is correct only if the ESPN parser populates the field differently per sport. It is a fragile contract: any parser change that normalises clock to "remaining" everywhere would silently break AFL/NRL FlyTime (they'd fire at the *start* of the period instead of the end). No assertion guards this.

### 7.2 Soccer stoppage time discarded
`parseInt('90+4', 10)` → `90`, but `parseInt("45'", 10)` → `45`. The `minute >= 80` gate works, but stoppage-time drama (the most FlyTime-dense moment in soccer) is compressed to the same minute value. A 1-goal game in the 96th minute and the 80th look identical; there is no escalation as injury time runs down.

### 7.3 Margin-only blindness in low-event sports
Soccer/hockey gate on margin ≤ 1. A 2-goal game with a flurry of late chances (xG screaming) is invisible. Conversely a dull 1-0 with no shots is "FlyTime" from the 80th minute. The engine has no event-quality signal.

### 7.4 Binary cliff flicker
A basketball game oscillating around margin 8 (8→9→8→9) flips green on/off each poll until the first true crossing pins it. Between polls this can produce a visibly twitchy fly. Pinning mitigates it *after* the first trigger but not *before*.

### 7.5 Blowout-buffer over-persistence
§3: a single momentary touch of the close margin pins the red fly permanently (until 35-day prune), even if the game was never genuinely close again. This inflates red-fly counts and corrupts any precision measurement built on `flyTimeMatches`.

### 7.6 Final-margin proxy ≠ FlyTime (already known)
Offline calibration and the close-rate tables use **final** margin. A game can finish at margin 3 having never been tense (steady 3-point game) or finish at margin 15 after being tied with 3:00 left (a real FlyTime that "got away"). Using final margin as truth both over- and under-counts. The prior program flagged this as the blocking issue ([FlyTime-Intelligence README](../FlyTime-Intelligence/README.md)).

### 7.7 No cross-engine consistency
Yellow can predict FlyTime and green never fires (false yellow), or green fires with no yellow (missed prediction). Because the ledger never closes, neither error is currently being measured in production.

### 7.8 Cricket fragility
Cricket green requires `cricket_runs_req` and `cricket_overs_left`; if either is null the function returns false. First-innings excitement (a huge total being built) is entirely outside the model — only run-chases can be FlyTime.

---

## 8. The complete FlyTime system map (summary)

```
ASSUMPTION EMBEDDED IN TODAY'S SYSTEM          REALITY / 2.0 RESPONSE
─────────────────────────────────────          ─────────────────────────────────
"FlyTime = tight margin in the final minutes"  → FlyTime = a TRAJECTORY toward a
                                                  tense finish; detectable earlier.
"A single margin threshold per sport"          → Lead safety is a CURVE in
                                                  (margin, time, volatility).
"Binary on/off"                                → Continuous 0–100 FlyTime Index
                                                  with multi-stage triggers.
"Clock + margin are the only inputs"           → Momentum, scoring rate, comeback
                                                  state, pre-match rating all matter.
"Final margin is ground truth"                 → Late-tension trajectory is truth.
"Yellow and green are separate"                → One probability spine, fed by both.
"Tune to a volume target (~2/round)"           → Tune to measured precision/recall.
```

**Conclusion of Phase 1:** the green engine is a clean, cheap, *reactive confirmation gate* with several latent fragilities (clock polarity, binary flicker, over-persistent pinning) and one fundamental limitation — **it cannot predict**. The yellow engine is principled but disconnected and unvalidated (open ledger). The richest available signals (FlySense momentum/comeback, scoring rate, pre-match rating) are computed and discarded. FlyTime 2.0's job is to fuse them into a single continuous, early, calibrated probability. Proceed to [Phase 2](./02-sport-by-sport-analysis.md).
