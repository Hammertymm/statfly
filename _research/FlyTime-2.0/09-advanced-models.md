# Phase 9 — Advanced Models

**Goal:** evaluate next-generation FlyTime concepts and recommend the highest-performing architecture. The candidates: Dynamic Win Probability, Close-Finish Probability, the FlyTime Index, and Multi-Stage Prediction.

---

## 1. The crucial distinction: Win Probability ≠ FlyTime

This is the most important conceptual point in the whole program.

**Win Probability (WP)** measures *how likely each team is to win*. It is **maximally uncertain (≈50/50) when a game is close** — which sounds like FlyTime, but is not the same thing.

**FlyTime** measures *how likely the match is to be a tense, watchable finish*. The key divergence cases:

| Situation | Win Probability | FlyTime |
|-----------|-----------------|---------|
| Tied, 30s left, both teams trading scores | ~50/50 | **Maximum** ✓ (WP and FlyTime agree) |
| Tied at *half-time* | ~50/50 | **Low** — plenty of time, no tension yet |
| +3 with 10s left, leader has the ball | ~85/15 | **High** — one play decides it (WP says "decided", FlyTime says "watch!") |
| +20, garbage time | ~99/1 | Zero (agree) |

So FlyTime ≈ **a function of (1 − |WP − 0.5|×2) gated by time-remaining and recency-of-uncertainty.** WP is an *ingredient*, not the answer. A naive "show flies when WP ≈ 50%" would fire at half-time of every even game and miss the +3-with-10-seconds nailbiter. **This is exactly the trap a generic win-probability integration would fall into**, and why FlyTime needs its own target.

### Recommendation on WP
Use WP (or our `LeadSafety` curve, which is WP's close cousin) as an **input**, transformed by a time-and-tension envelope, **not** as the FlyTime output itself. Where ESPN provides a live WP timeline, ingest it as a strong feature; where not, our per-sport `LeadSafety` curve stands in.

---

## 2. Close-Finish Probability (CFP) — the right target variable

Define the quantity the engine actually estimates:

```
CFP(t) = P( the match will be in a sustained tense state during its
            decisive window | everything known at time t )
```

This is the **True FlyTime** label from [Phase 3](./03-historical-close-finish-research.md) turned into a live forecast. It is:
- **Forward-looking** (a forecast, enabling earliness) — not "is it close now" but "will it finish close".
- **Trajectory-aware** (rewards catching tense-then-resolved games).
- **Directly trainable** against the historical truth label.

CFP **is** the conceptual core of FlyTime 2.0. Everything else (FlyIndex, stages) is presentation of CFP.

---

## 3. FlyTime Index (0–100) — the presentation layer

The **FlyTime Index = round(100 × CFP)**, calibrated per sport so the number is an honest probability. It is the single continuous scalar that:
- replaces the binary `isFlyTime()` boolean,
- drives the three stages via hysteresis ([Phase 5](./05-confidence-system.md), [Phase 7](./07-decay-model.md)),
- powers ranking ("top FlyTime matches right now"),
- gives the FlyTime Lab a tunable, loggable quantity.

A 0–100 index is the right abstraction because it is **already the mental model** of the rest of ScoreFly (FlySense momentum is 0–100, yellow `flyMatchRating` is 0–100). FlyTime joins the family.

---

## 4. Multi-Stage Prediction — the recommended user-facing structure

Map the index to the brief's three stages, which are simply CFP confidence bands with hysteresis:

| Stage | CFP band | Role |
|-------|----------|------|
| **Stage 1 — Potential** | ≈ 0.60–0.80 | early warning; high recall; "could get tense" |
| **Stage 2 — Likely** | ≈ 0.80–0.95 | confident lean-in; "heading for a close finish" |
| **Stage 3 — Confirmed** | ≥ 0.95 | the trust anchor; "nailbiter — switch now" |

Multi-stage is strictly superior to both the binary gate (no earliness, no nuance) and a bare percentage (fake precision, not glanceable). It is the structure that lets one feature be simultaneously high-recall and high-precision ([Phase 6](./06-false-positive-elimination.md)).

---

## 5. Architecture options ranked

| Architecture | Description | Pros | Cons | Verdict |
|--------------|-------------|------|------|---------|
| **A. Binary gate (today)** | margin+clock threshold | trivial, explainable | late, binary, no earliness | replace |
| **B. CFP via calibrated additive index (Option D)** | the [Phase 4](./04-predictive-engine.md) model → FlyIndex → stages | early, explainable, cheap, per-sport tunable, shadow-safe, on-ramp to ML | hand-tuned weights until data confirms | **launch architecture** |
| **C. CFP via learned model (Option E)** | GBM/logistic on Phase-3 features → calibrated CFP | highest accuracy ceiling, learns interactions | needs labelled data per sport, serving cost, explainability work | **target after data exists** |
| **D. Hybrid** | learned where data-rich (Tier A), additive elsewhere (Tier B/C) | best of both, graceful | two code paths to maintain | **end state** |

### Recommended evolution
```
Today          →  Launch 2.0           →  2.0.x                →  End state
Binary gate       Calibrated additive      + learned model on      Hybrid: learned (rich
(replace)         CFP index + stages       Tier-A sports           leagues) + additive
                  (B)                      (C, validated)          (thin leagues) (D)
```

The same `FlyIndex → stages → UI` contract holds across all stages of this evolution, so the learned model can be swapped into the `calibrate_sport()` / index slot **without any UI or product change** — only the number's provenance changes. This is the payoff of separating CFP (the estimate) from the FlyTime Index (the presentation).

---

## 6. Concepts considered and explicitly deprioritised

- **Pure live WP display** — wrong target (§1), would mislead users at half-time.
- **Betting-odds passthrough** — legally/commercially fraught, not differentiated, and odds bake in vig + market bias; use as a *benchmark* ([Phase 10](./10-benchmarking.md)), not a source.
- **Heavy per-event xG-style models at launch** — high value for soccer/NHL but data-gated; slot in as features when the feed supports them.

**Phase 9 conclusion:** the highest-performing *shippable* architecture is **Close-Finish Probability, estimated by the calibrated additive index (Option D), presented as a 0–100 FlyTime Index and a three-stage trigger**, with a clear, UI-stable upgrade path to a learned model on data-rich sports. Proceed to [Phase 10](./10-benchmarking.md).
