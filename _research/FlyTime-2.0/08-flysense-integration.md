# Phase 8 — Integration with FlySense

**Goal:** define how FlyTime and FlySense interact. The headline finding from Phase 1: FlySense already computes a rich, per-poll momentum picture that FlyTime **completely ignores**. Wiring them together is the single highest-leverage accuracy upgrade available with **zero new data**.

---

## 1. What FlySense already produces (free inputs)

From [index.html](../../scorefly/index.html) (`updateFly`, `flyState`, tuning table at line 1761):

| FlySense output | Field | What it means | FlyTime use |
|-----------------|-------|---------------|-------------|
| Per-side momentum 0–100 | `hMom`, `aMom` | recent scoring weighted by acceleration, decayed on a per-sport half-life | core **MomentumPressure** term |
| Resolved state | `hState`/`aState` ∈ {warming, onrun, onfire, cold, comeback} | the human-readable momentum tier | stage gating + corroboration |
| Largest deficit faced | `hMaxDef`/`aMaxDef` | how big a hole a side climbed out of | comeback magnitude → drama weight |
| Deficit-peak time | `hDefPeakTs`/`aDefPeakTs` | how *fast* the comeback is | recovery speed → escalation |
| Recent peak momentum | `hPeak`/`aPeak` | collapse detection (fall from peak) | leader **collapse** signal |
| Per-sport tuning | `bigPlay`, `cbMin`, `halflife`, `droughtNorm` | sport rhythm | reuse directly — don't re-derive |
| Cricket run-rate engine | `updateCricketFly` | format-aware RRR momentum | cricket FlyTime input |

The FlySense states map to a **clean semantic vocabulary** FlyTime can consume directly:
- **On Fire** (trailing side) = a comeback is *actively happening* → strong FlyTime signal.
- **Cold** (leading side) = the leader has stalled → lead is less safe than the margin suggests.
- **Comeback** = an explicit "clawing back a deficit" state → the textbook precursor to FlyTime.
- **Control** / dominant On Fire (leading side) = the opposite — drama draining away.

---

## 2. The four interaction questions (answered)

### Q1. Can momentum forecast future FlyTime?
**Yes — this is the mechanism that delivers earliness.** Margin tells you the *current* gap; momentum tells you *which way it is moving and how fast*. A 14-point lead with the trailing side On Fire and the leader Cold is a FlyTime in the making **before** the margin closes. The legacy gate can't see this; the FlyIndex's `MomentumPressure` term is precisely this forecast. Momentum is the leading indicator; margin is the lagging one.

### Q2. Can FlySense increase prediction confidence?
**Yes — as corroboration for stage escalation.** A tight FlyIndex driven only by margin/time is "Likely at best"; the **same** index *corroborated* by a real momentum swing (trailing On Fire / leader collapsing) earns **Confirmed**. Conversely, a tight margin with *no* momentum and a *dropping* trailing side (already spent its comeback) should be held back — the game may be settling. FlySense is the confidence multiplier in both directions.

### Q3. Can FlyTime improve FlySense?
**Yes — contextual prioritisation and shared truth.** FlyTime knows *which matches matter most right now*. FlySense rendering can use FlyTime stage to prioritise visual attention (a Confirmed-FlyTime card earns the richest momentum animation; a dead game's momentum can be visually quieter). They also share the same per-sport rhythm constants (`halflife`, `bigPlay`) and should share the **same trajectory truth label** ([Phase 3](./03-historical-close-finish-research.md)) so the two systems never disagree about what "exciting" meant historically.

### Q4. Should they merge?
**No — keep them separate systems with a one-way data dependency.** FlySense answers *"what are the teams doing right now?"* ([FlySense README](../FlySense-2.0/00-README.md)); FlyTime answers *"is this match about to become unmissable?"*. These are different questions with different consumers. FlyTime **depends on** FlySense (reads its outputs); FlySense does **not** depend on FlyTime (only optionally uses its stage for visual priority). This keeps FlySense pure and testable, and keeps FlyTime cheap (it reuses, never recomputes, momentum).

---

## 3. The integrated architecture

```
            ┌──────────────────────── per poll (8–12s) ────────────────────────┐
ESPN feed → parse → m
                     │
                     ├──▶ FlySense updateFly(m)
                     │        ├─ hMom/aMom (momentum 0–100)
                     │        ├─ hState/aState (onfire/cold/comeback/…)
                     │        ├─ maxDef / peak (comeback magnitude, collapse)
                     │        └─ per-sport halflife/bigPlay tuning
                     │                      │  (read-only)
                     │                      ▼
                     └──▶ FlyTime 2.0 computeFlyIndex(m, flySense)
                              ├─ LeadSafetyDeficit(margin, timeLeft)      [A]
                              ├─ ScoringVolatility(rate, leadChanges)     [B]
                              ├─ MomentumPressure(hMom,aMom,state,collapse) [C] ◀── FlySense
                              ├─ ContextPrior(flyMatchRating, homeEdge)   [D]
                              └─ calibrate_sport() → FlyIndex 0–100
                                          │
                              hysteresis + sustain ([Phase 7])
                                          │
                              Potential / Likely / Confirmed
                                          │
                     ◀─── (optional) FlyTime stage informs FlySense visual priority ───┘
```

One-way solid arrow FlySense→FlyTime (data dependency); dashed optional arrow FlyTime→FlySense (visual priority only).

---

## 4. `MomentumPressure` — concrete definition

A signed, bounded term that captures "the margin is about to move toward zero":

```
trailingSide   = side currently behind
momSwing       = mom[trailingSide] − mom[leadingSide]        // −100..+100
collapse       = max(0, peak[leadingSide] − mom[leadingSide]) // leader falling from peak
comebackBoost  = (state[trailingSide] == 'comeback' || 'onfire') ? k1 : 0
deficitClimbed = maxDef[trailingSide] recovered fraction      // already-clawed drama

MomentumPressure = clamp(
      a1·momSwing/100
    + a2·collapse/100
    + comebackBoost
    + a3·deficitClimbed , 0, 1)
```

- Positive only when the trailing side has the momentum — momentum *for the leader* does **not** raise FlyTime (it lowers it; the game is being decided).
- `collapse` lets a leader's stall raise FlyTime even before the trailing side scores.
- Per-sport coefficients (`a1..a3`, `k1`) tuned alongside the FlyIndex weights.

---

## 5. Why this is the top-priority upgrade

| Upgrade | New data needed | Effort | Accuracy/earliness gain |
|---------|-----------------|--------|--------------------------|
| **FlySense fusion (this)** | **none** (already computed) | low (read existing fields) | **high** — the earliness mechanism |
| Per-sport lead-safety curves | reconstructed history | medium | high |
| Possession/timeout (gridiron), goalie-pull (NHL) | richer live feed | medium–high | sport-specific high |
| Learned model (Option E) | labelled dataset | high | highest ceiling, later |

FlySense fusion is the rare upgrade that is both **cheap** and **transformative** — it is what turns the lagging margin signal into a leading one. It should be in the first shippable 2.0 increment. Proceed to [Phase 9](./09-advanced-models.md).
