# Phase 12 — Validation Framework

**Goal:** a testing system that evaluates FlyTime across thousands of historical and live matches, measures precision/recall/lead-time/usefulness, and defines what "success" means concretely. No parameter set ships to a sport until it passes here.

This builds on the existing harness: `flytime-engine` (`backfill`/`analyze`/`report`), [validate_flytime_rules.py](../../scorefly/flytime-engine/validate_flytime_rules.py) (22 rule tests), and [replay_proxy_analysis.py](../../scorefly/flytime-engine/replay_proxy_analysis.py).

---

## 1. Three evaluation layers

| Layer | Data | Answers | Cadence |
|-------|------|---------|---------|
| **A. Backtest** | reconstructed historical timelines ([Phase 3](./03-historical-close-finish-research.md)) | "Would 2.0 have caught past FlyTimes earlier and cleaner?" | every parameter change |
| **B. Shadow (live)** | live polls, 2.0 computed but **not shown** | "Does 2.0 behave well on real live data vs the legacy gate?" | continuous pre-launch |
| **C. Production (live)** | the closed ledger | "Is 2.0 accurate in users' hands?" | ongoing post-launch |

The same metrics are computed in all three layers so a parameter set's backtest score can be compared to its live score (drift detection).

---

## 2. Ground truth

The **True FlyTime** label from [Phase 3 §1.1](./03-historical-close-finish-research.md) (trajectory-based, sustained tense state in the decisive window) — **not** final margin. Each historical match is labelled once; each live match is labelled retrospectively when it finishes (and that label closes the ledger row).

---

## 3. Core metrics (per sport, per stage)

| Metric | Definition | Target |
|--------|------------|--------|
| **Precision** | TP / (TP + FP) — of flagged, how many were truly FlyTime | Confirmed ≥ 95%, Likely ≥ 85%, Potential ≥ 60% |
| **Recall** | TP / (TP + FN) — of true FlyTimes, how many we flagged | ≥ 90% (Potential-or-higher) |
| **Accuracy** | (TP+TN)/all | report (less meaningful given class imbalance) |
| **F1 / Fβ** | precision/recall balance (β>1 at Potential to favour recall) | per-stage |
| **False-positive rate** | FP / (FP+TN) | < 10% |
| **False-negative rate** | FN / (FN+TP) | < 10% |
| **Avg trigger timing** | game-time at first stage fire | per sport |
| **Prediction lead time** | (legacy first-fire time) − (2.0 first-fire time) | **+5 to +10 min** where sport allows |
| **Stability** | stage transitions per match | ≤ per-sport cap (anti-flicker) |
| **Calibration error** | |predicted CFP − observed freq| across index bins | small; reliability curve ≈ diagonal |
| **Usefulness (proxy)** | of Confirmed flies, % that a neutral fan would rate "worth switching to" | high (panel/heuristic) |

### Calibration (reliability) check
Bin live matches by FlyIndex (e.g. 60–65, 65–70, …). Within each bin, the observed True FlyTime frequency should ≈ the bin's index. A 90 should be FlyTime ~90% of the time. This is the test that the *number means what it says* — without it, the stages are arbitrary.

---

## 4. The confusion-matrix harness (design)

```
for each match in dataset:
    truth          = TrueFlyTime(match)                 # Phase 3 label
    legacyFired    = retro_isFlyTime_everTrue(match)    # baseline
    v2_first_stage = simulate_v2(match.timeline)        # {stage, t_first} per stage
    record(sport, truth, legacy, v2)

per sport:
    legacy_confusion  = confusion(legacyFired, truth)   # the baseline to beat
    v2_confusion[stg] = confusion(v2_reached(stg), truth)
    lead_time         = mean(legacy_first_t − v2_first_t | both fired)
    calibration       = reliability_curve(v2_index, truth)
    stability         = mean(stage_transition_count)
report: per-sport table + pass/fail vs targets
```

Extends the existing `analyze`/`report` commands; reuses the season-window backfill already configured per league.

---

## 5. Live shadow-mode protocol (Layer B)

1. Compute FlyIndex + stage every poll for every live match; **log, don't render**.
2. On match completion, apply the True FlyTime label and write the full ledger row (`p`, stage-reached, `a`, `fin`, `rf`, first-fire times, legacy comparison).
3. Nightly job rolls up the same metrics as the backtest.
4. **Gate:** a sport graduates from shadow to live UI only when, over a meaningful sample, it **meets all targets AND beats the legacy baseline** for that sport.

This finally **closes the ledger loop** that has been open since launch ([Phase 1 §4.3](./01-current-system-audit.md)) — the prerequisite for any honest tuning.

---

## 6. Live manual validation (carry-over from FlyTime-Intelligence)
Retain the manual spot-checks from [FlyTime-Intelligence/03-live-validation-protocol](../FlyTime-Intelligence/03-live-validation-protocol.md): watch one genuine close finish per major sport with the app open, confirm the stage escalation and timing feel right to a human. Automated metrics catch aggregate behaviour; human checks catch "this is technically a FlyTime but feels wrong" cases.

---

## 7. Regression tests
Extend [validate_flytime_rules.py](../../scorefly/flytime-engine/validate_flytime_rules.py) (currently 22 `isFlyTime` rule tests) with FlyIndex/stage tests:
- monotonicity (tightening margin never lowers index, all else equal);
- hysteresis (no stage toggles inside a band);
- sustain (single-poll spike never shows a stage);
- degradation (missing FlySense caps stage at Potential);
- per-sport boundary cases (NHL goalie-pull window, soccer stoppage, MLB base/out, cricket last over).

---

## 8. What success looks like

FlyTime 2.0 is a success when, per sport:

> **It catches ≥ 90% of genuinely tense finishes, is right ≥ 95% of the time when it says "Confirmed", fires its first warning 5–10 minutes earlier than today, never flickers, its index is well-calibrated, and the closed ledger confirms all of this on real users' live matches — beating the legacy gate on every sport before it replaces it.**

Until those numbers exist from real reconstructed and live data, every threshold in this program is an explicit hypothesis, and 2.0 stays in shadow mode. Proceed to [Phase 13](./13-migration-strategy.md).
