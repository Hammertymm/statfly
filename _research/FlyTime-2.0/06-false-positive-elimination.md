# Phase 6 — False Positive & False Negative Elimination

**Goal:** identify *why* FlyTime predictions fail and design systems to minimise false positives, false negatives, and delayed detection — the three error modes that destroy user trust.

---

## The three failure modes

| Mode | Definition | User experience | Trust cost |
|------|------------|-----------------|------------|
| **Early trigger (False Positive)** | flagged FlyTime, never became competitive | "I switched over and it was a blowout" | **Severe** — the worst error; one burned user stops trusting flies |
| **Late trigger (Delayed detection)** | became close *before* the fly appeared | "I found it myself; the app was slow" | Moderate — feature feels useless, not harmful |
| **Missed FlyTime (False Negative)** | genuine close finish never flagged | "I missed a classic" | Moderate–severe — silent failure, hard to notice but corrosive |

A predictive engine inherently trades these against each other. The design goal is **per-stage asymmetry**: Confirmed prioritises precision (no false positives), Potential tolerates more false positives to buy recall and earliness.

---

## Root-cause analysis of current failures

Traced to Phase 1 findings:

### Early triggers (FP) in today's system
1. **Blowout-buffer over-persistence (§7.5):** a single momentary margin-8 touch pins the match and stamps a red fly permanently — a blowout gets a FlyTime badge. **Top current FP source.**
2. **Margin-only, quality-blind gates (§7.3):** a dull 1-0 soccer game from the 80th minute is "FlyTime" with zero late chances.
3. **Binary cliff flicker (§7.4):** oscillation around the threshold creates on/off bursts before pinning.

### Late triggers (delayed) in today's system
4. **The late-clock cliff (§2.3):** by construction the gate cannot fire before 5:00 (basketball) / 80' (soccer) / 35:00 (NRL). Any tension before that window is invisible — *every* early-tense game is a delayed detection.

### Missed FlyTimes (FN) in today's system
5. **Tense-then-resolved games:** tied at 7:00, pulled away to +12 by 4:00 — never satisfied "margin ≤ 8 inside 5:00", so never flagged, despite being genuinely unmissable at 7:00.
6. **2-goal NHL goalie-pull drama, soccer stoppage time, MLB base/out tension** (Phase 2) — all structurally outside the gate.
7. **Open ledger (§4.3):** because `a`/`fin` never populate, today *none* of these errors are even being measured. You cannot fix what you do not count.

---

## Mitigation system (2.0)

### Against False Positives (precision)

| Mechanism | How it kills the FP | Stage |
|-----------|---------------------|-------|
| **Sustain requirement** | A stage requires the FlyIndex to hold above its band for ≥ N seconds, not a single poll. Kills momentary-touch FPs (§7.5) and flicker (§7.4). | all |
| **Exit hysteresis** | Once a game blows out, the index must fall well below the entry band to drop the stage — but a genuine blowout *will* fall, so the fly clears instead of persisting falsely. Replaces the crude blowout-buffer with a smooth, correct exit. | all |
| **Momentum corroboration** | Confirmed requires not just a tight number but a non-collapsing trajectory (the trailing side isn't already dead). | Confirmed |
| **Quality gate where available** | Soccer/NHL: require late chance activity / shots, not just margin, before high stages (when event data exists). | Likely+ |
| **Per-sport precision calibration** | Confirmed threshold set to the FlyIndex that historically yields ≥ 95% True FlyTime ([Phase 3](./03-historical-close-finish-research.md)). | Confirmed |

### Against Delayed detection (earliness)

| Mechanism | How it helps |
|-----------|--------------|
| **Continuous index from kickoff of the decisive window** | No clock cliff; the engine evaluates every poll and can surface Potential the moment evidence appears. |
| **Momentum/volatility leading indicators** | A lead being actively eaten raises the index *before* the margin is close ([Phase 4](./04-predictive-engine.md) Option C). |
| **Pre-match prior** | A fixture rated likely-close (yellow) reaches Potential on weaker live evidence → earliest possible flag. |

### Against False Negatives (recall)

| Mechanism | How it helps |
|-----------|--------------|
| **Trajectory label as truth** | Training/tuning against True FlyTime ([Phase 3](./03-historical-close-finish-research.md)) means "tense-then-resolved" games count as positives the engine is rewarded for catching. |
| **Sport-specific physics** | Goalie-pull, stoppage time, base/out, possessions explicitly modelled (Phase 2) → the structural FNs disappear. |
| **Potential's permissive band** | Recall is bought at the Potential stage, where a ~60% precision is acceptable. |
| **Closed ledger** | 2.0 mandates the live→ledger loop actually fires (`a:1`, `fin:1`, `rf:1`) so FNs are counted and fed back. |

### Against flicker specifically — see [Phase 7](./07-decay-model.md)
Asymmetric hysteresis + sustain + index smoothing together guarantee a stage, once shown, behaves predictably.

---

## The precision/recall operating point per stage

```
                    high recall ◀───────────────▶ high precision
Potential   ●──────────────●                         (≈60% precision, ~90% recall target)
Likely               ●──────────────●                (≈85% precision)
Confirmed                       ●──────────────●     (≈95%+ precision, the trust anchor)
```

Each stage is a different point on the same curve, so the system is *simultaneously* high-recall (via Potential) and high-precision (via Confirmed) — which a single binary gate can never be. This directly satisfies the brief's "minimum false positives AND minimum false negatives" by **refusing to pick one operating point**.

---

## Measurement-first principle

The single most important fix is non-algorithmic: **close the ledger loop.** Today every FP/FN is invisible because live detection never writes back ([§4.3](./01-current-system-audit.md)). 2.0 treats "every live stage transition is logged with its later outcome" as a launch requirement, so the confusion matrix in [Phase 12](./12-validation-framework.md) is computed from real production data, not just backtests. Proceed to [Phase 7](./07-decay-model.md).
