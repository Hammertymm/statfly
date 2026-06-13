# Phase 11 — FlyTime 2.0 Specification

The consolidated rebuild specification. This is the single document an engineer implements from; everything earlier is the evidence behind it.

---

## 1. Core philosophy

> **FlyTime answers one question: "Is this match about to become unmissable?" — and answers it as early as the evidence honestly allows, with a confidence the user can trust.**

FlyTime 2.0 replaces a **binary, late, snapshot gate** with a **continuous, early, trajectory-aware probability** — the **Close-Finish Probability (CFP)** — surfaced as a **0–100 FlyTime Index** and a **three-stage trigger** (Potential → Likely → Confirmed), stabilised so it never flickers, fed by everything the app already computes.

Design commitments:
- **Earliest honest detection** over latest certain detection.
- **One feature, two operating points:** high recall at Potential, high precision at Confirmed.
- **Per-sport physics, shared framework.**
- **Reuse, don't recompute:** consume FlySense, the yellow rating, the existing tuning tables.
- **Degrade honestly:** thin data → lower confidence stage, never a false Confirmed.
- **Measure everything:** close the ledger loop; tune against precision/recall, not volume.

---

## 2. The model

### 2.1 Output
Per live match, per poll:
```
FlyIndex ∈ [0,100]   (= 100 × CFP, sport-calibrated)
Stage    ∈ { none, Potential, Likely, Confirmed }
Reasons  ∈ list of contributing factors (for UI + lab)
```

### 2.2 CFP estimator (launch = calibrated additive, Option D)
```
raw = w_base · LeadSafetyDeficit(sport, margin, timeLeft, structuralCtx)
    + w_rate · ScoringVolatility(recentRate, lateLeadChanges)
    + w_mom  · MomentumPressure(flySense)            // trailing-side momentum, leader collapse, comeback
    + w_ctx  · ContextPrior(flyMatchRating, homeEdge)

FlyIndex = 100 · calibrate_sport(raw)                // monotone logistic → honest probability
```
- Weights `w_*` and the curves are **per sport** (per league where data justifies).
- **Graceful degradation:** drop any unavailable term, renormalise the rest, and **cap the max stage** (no momentum/context → Potential ceiling; full inputs → Confirmed eligible).
- **Upgrade slot:** `calibrate_sport(raw)` may be replaced by a learned CFP model (Option E) on data-rich sports with no change to anything below.

### 2.3 Per-sport `LeadSafetyDeficit` ("time" variable & band)
| Sport | Time variable | Band logic |
|-------|---------------|-----------|
| Basketball | √(seconds left) | margin vs `≈3·√(s_left)` curve + foul-game adj last 2:00 |
| Gridiron | possessions remaining | one-score (≤8) core; ≤16 if possession+timeouts favour trailer |
| AFL | minutes left in Q4 (+time-on) | margin in goals (÷6); sticky → decays fast with time |
| NRL/Rugby | minutes left in H2 | margin in converted-tries (÷6); possession weight |
| NHL | minutes left in P3 | ≤1 always; ≤2 inside goalie-pull window |
| MLB | outs remaining + base state | ≤2 core; ≤3 in 9th with tying run on/at plate |
| Soccer | minute incl. stoppage | 0–1 goal; stoppage time escalates |
| Cricket | balls remaining | required-rate vs capacity + wickets (reuse FlySense run-rate engine) |

### 2.4 `MomentumPressure` (from FlySense — [Phase 8 §4](./08-flysense-integration.md))
Signed term, positive only when the **trailing** side has momentum; boosted by leader collapse (fall from `peak`) and comeback/on-fire state; scaled by deficit already clawed back.

### 2.5 Stages, hysteresis, sustain ([Phase 5](./05-confidence-system.md), [Phase 7](./07-decay-model.md))
| Stage | Enter ≥ | Exit < | Sustain to show | Precision target |
|-------|---------|--------|-----------------|------------------|
| Potential | 62 | 55 | ~2 polls | ≥ 60% |
| Likely | 82 | 74 | ~2 polls | ≥ 85% |
| Confirmed | 95 | 88 | ~1–2 polls | ≥ 95% |
(Thresholds illustrative; calibrated per sport so each stage = the same *probability* everywhere.)
- Enter-high / exit-low (anti-flicker). Exit may be faster than entry on genuine blowouts.
- Light EMA smoothing on FlyIndex before band tests.
- **Recovery is automatic** (index recomputed live; no lockout). Replaces the legacy pin/blowout-buffer.

### 2.6 Inputs summary
| Input | Source | Status today |
|-------|--------|--------------|
| margin, period, clock | parsed match | used |
| per-sport structural ctx (possession, outs, goalie-pull, stoppage, RRR/wickets) | feed | partly available |
| momentum, states, collapse, comeback magnitude | FlySense | computed, **unused** → now used |
| pre-match closeness | yellow `flyMatchRating` | computed, **unused live** → now used |
| home edge | new (small) | to add |
| rolling trajectory (t, margin, momentum) | new in-session buffer | to add (cheap) |

---

## 3. Trigger logic (pseudocode)

```
function computeFlyTime(m, flySense, trajectory):
    if not inDecisiveWindow(m.sport, m.period, m.clock):     # cheap early-out
        return { index: 0, stage: 'none' }

    ctx   = structuralContext(m)                              # sport-specific
    base  = leadSafetyDeficit(m.sport, margin(m), timeLeft(m, ctx), ctx)
    rate  = scoringVolatility(trajectory)
    mom   = momentumPressure(flySense)                        # 0 if FlySense absent
    prior = contextPrior(m.flyMatchRating, homeEdge(m))       # 0 if absent

    raw, cap = combineWithDegradation(base, rate, mom, prior) # cap = max allowed stage
    idx = 100 * calibrateSport(m.sport, raw)
    idx = emaSmooth(m.id, idx)

    stage = resolveStage(m.id, idx, cap)                      # hysteresis + sustain + cap
    ledgerObserve(m, idx, stage)                              # ALWAYS log (close the loop)
    return { index: idx, stage, reasons: explain(base,rate,mom,prior) }
```

`inDecisiveWindow` keeps the engine O(1)-cheap for the 95% of match-time that can't be FlyTime, then does the richer maths only when it could be.

---

## 4. UI specification

One fly, intensity = stage (mirrors FlySense 2.0 visual grammar):

| Stage | Fly appearance | Behaviour |
|-------|----------------|-----------|
| Potential | faint/outline, muted, static | ambient — discoverable, not shouting |
| Likely | solid, full colour, gentle pulse | draws the eye |
| Confirmed | bright, stronger pulse/glow | today's green-fly energy, reachable earlier |
| (finished) | red fly | only if it genuinely reached a sustained tense state |

- Keep **yellow** (pre-match) and **blue** (Y→G diagnostic) flies as-is; they slot into the same language.
- Optional **"Potentials" rail** = the "top FlyTime right now" discovery surface.
- Raw FlyIndex + stage history live in **FlyTime Lab** (`?flylab=1`) only.

---

## 5. Performance requirements

| Metric | Target | Rationale |
|--------|--------|-----------|
| Per-match compute | < 1 ms | reuses FlySense outputs; only arithmetic |
| Added memory/match | small rolling buffer (~last 5 min of polls) | rate/volatility |
| Update latency | within one poll (8–12s live) | matches existing cadence ([config.py:216](../../scorefly/flytime-engine/flytime_engine/config.py)) |
| No new network calls | reuse existing ESPN polls | |
| UI transition | smooth crossfade, consistent with FlySense | no jarring flips |

---

## 6. Validation requirements (success metrics)

Per sport, measured by [Phase 12](./12-validation-framework.md):
- **Recall ≥ 90%** of True FlyTime matches (Potential-or-higher ever fired).
- **Confirmed precision ≥ 95%**; **Likely ≥ 85%**; **Potential ≥ 60%**.
- **Lead-time:** first stage fires **5–10 min earlier** than legacy gate (where sport volatility allows).
- **Stability:** stage changes per match ≤ a small per-sport cap (no flicker).
- **Calibration:** FlyIndex bins match observed True FlyTime frequency (reliability curve near diagonal).

A 2.0 parameter set ships to a sport **only after it beats the legacy baseline** on that sport's confusion matrix in shadow mode.

---

## 7. What is kept, changed, removed

| Component | Fate |
|-----------|------|
| Yellow engine (`computeFlyMatch`, `FLY_V1_REGISTRY`) | **kept**, now also feeds live `ContextPrior` |
| Green `isFlyTime()` binary gate | **replaced** by FlyIndex/stages (retained internally as a Confirmed corroborator + shadow baseline) |
| `FLY_BLOWOUT_MARGIN` pin/buffer | **removed**, superseded by hysteresis decay |
| `flyTimeMatches` red-fly memory | **kept** but written on sustained tense state, not a single touch |
| Ledger (`flyLedger`) | **kept and made to actually close** (live→outcome) |
| FlySense | **kept**, becomes a FlyTime input |
| Per-sport tuning (`halflife`, `bigPlay`, close margins) | **reused** |

This is the complete target. The path to get here without risk is [Phase 13](./13-migration-strategy.md); how to prove each step is [Phase 12](./12-validation-framework.md).
