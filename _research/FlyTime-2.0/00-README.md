# ScoreFly FlyTime 2.0 — Research, Audit, Prediction, Validation & Rebuild Program

**Status:** Research deliverables (docs only — no application code changed in this pass)
**Repository:** `C:\Projects\ScoreFly\scorefly`
**Subject system:** FlyTime — ScoreFly's "this match is worth watching right now" intelligence
**Grounded in:** [scorefly/index.html](../../scorefly/index.html) (`isFlyTime`, `FLY_V1_REGISTRY`, `computeFlyMatch`), [scorefly/flytime-engine/](../../scorefly/flytime-engine/), the 45 `*-flytime-v1.json` tables, and [_research/FlyTime-Intelligence](../FlyTime-Intelligence/README.md).
**Companion program:** [_research/FlySense-2.0](../FlySense-2.0/00-README.md) (momentum language — the systems must interlock).

---

## What FlyTime is

FlyTime is ScoreFly's answer to one question:

> **Is this match about to become unmissable?**

A FlyTime match is one heading toward a genuinely close, tense finish — the kind of game a fan would drop everything to switch to. Today FlyTime is surfaced through coloured "flies":

| Fly | Meaning | Engine |
|-----|---------|--------|
| **Yellow** | Upcoming match the engine predicts *could* be FlyTime (`isFlyMatch`) | Pre-match v1 table (`FLY_V1_REGISTRY`) |
| **Green** | Live match that **is in FlyTime right now** (`isFlyTime()`) | Live rule gate |
| **Red** | Finished match that reached FlyTime at some point | Memory of green |
| **Blue** | Diagnostic: yellow predicted → green achieved (Y→G hit) | Ledger |

## The mandate

The brief is explicit and deliberately ambitious: **do not deliver an incremental improvement.** Maximise **earliest accurate detection** — ideally flag a developing FlyTime with ~10 minutes left where the evidence supports it — while keeping false positives and false negatives low across every sport. Challenge every existing assumption and rebuild from first principles where the evidence justifies it.

---

## The one structural finding that drives the rebuild

**The current live engine cannot predict. It can only confirm.**

`isFlyTime()` ([index.html:1949](../../scorefly/index.html)) is a pure *reactive gate*. For basketball it returns true only when **all** of these are already true simultaneously:

```js
case 'basketball': return p >= 4 && c > 0 && c <= 300 && margin <= 8;
```

i.e. 4th quarter, clock already inside the final 5:00, and margin already ≤ 8. By the time those conditions hold, the close finish is no longer a *prediction* — it is a *present-tense fact* the user can see on any scoreboard. The system therefore delivers the green fly at roughly the latest possible moment, not the earliest. Every sport's rule has the same shape (a hard clock gate AND a hard margin gate). This is the central thing FlyTime 2.0 replaces: a binary, late, threshold gate becomes a **continuous, early, probabilistic forecast**.

The recommended 2.0 core is a **Close-Finish Probability** model expressed as a 0–100 **FlyTime Index**, evolving continuously through the match, surfaced through a **multi-stage trigger** (Potential → Likely → Confirmed) with **hysteresis-based decay** so it can rise early, fall when a game blows out, and recover when it tightens — without flickering. See [04-predictive-engine.md](./04-predictive-engine.md) and [11-flytime-2.0-spec.md](./11-flytime-2.0-spec.md).

---

## Deliverable index

| # | Document | Phase | Description |
|---|----------|-------|-------------|
| 00 | [00-README.md](./00-README.md) | Framing | This index + executive summary + success criteria |
| 01 | [01-current-system-audit.md](./01-current-system-audit.md) | Phase 1 | Full forensic map of both FlyTime engines: triggers, inputs, state, edge cases, failure modes |
| 02 | [02-sport-by-sport-analysis.md](./02-sport-by-sport-analysis.md) | Phase 2 | Independent per-sport lead-survival / scoring / comeback modelling + earliest viable trigger |
| 03 | [03-historical-close-finish-research.md](./03-historical-close-finish-research.md) | Phase 3 | Methodology to measure "what actually becomes FlyTime" + probability curves |
| 04 | [04-predictive-engine.md](./04-predictive-engine.md) | Phase 4 | Evaluation of options A–E + recommended predictive engine |
| 05 | [05-confidence-system.md](./05-confidence-system.md) | Phase 5 | Confidence tiers: benefits, risks, UI, recommendation |
| 06 | [06-false-positive-elimination.md](./06-false-positive-elimination.md) | Phase 6 | Early/late/missed trigger taxonomy + mitigations |
| 07 | [07-decay-model.md](./07-decay-model.md) | Phase 7 | Probability decay, recovery, trigger stability (anti-flicker) |
| 08 | [08-flysense-integration.md](./08-flysense-integration.md) | Phase 8 | How FlyTime and FlySense feed each other |
| 09 | [09-advanced-models.md](./09-advanced-models.md) | Phase 9 | Win probability, close-finish probability, FlyTime Index, multi-stage |
| 10 | [10-benchmarking.md](./10-benchmarking.md) | Phase 10 | Benchmark vs ESPN / NBA WP / AFL models / betting markets |
| 11 | [11-flytime-2.0-spec.md](./11-flytime-2.0-spec.md) | Phase 11 | Consolidated FlyTime 2.0 rebuild specification |
| 12 | [12-validation-framework.md](./12-validation-framework.md) | Phase 12 | Precision/recall/lead-time validation harness design |
| 13 | [13-migration-strategy.md](./13-migration-strategy.md) | Synthesis | Phased migration from the current gate to 2.0, shadow-mode first |

---

## Executive summary

**1. The product idea is sound; the live implementation is the weak link.** The yellow (pre-match) engine is a principled weighted model over real historical tables. The green (live) engine is a hand-tuned binary gate that is *correct but late* and *cannot forecast*. ([01](./01-current-system-audit.md))

**2. FlyTime is not one phenomenon — it is sport-specific.** Lead-survival curves differ enormously: an 8-point NBA lead with 5:00 left is genuinely unsafe; a 12-point AFL lead at the same relative time is nearly safe (AFL's historical close rate is the lowest of all feeds, ~27.5%). One global rule shape cannot be right for all. ([02](./02-sport-by-sport-analysis.md))

**3. "Close final margin" is the wrong ground truth and the program already knows it.** The prior FlyTime-Intelligence work flagged that final-margin proxy ≠ a true FlyTime window. 2.0 formalises a *trajectory-based* label: a match is "true FlyTime" if it spent meaningful late time in a tense state, regardless of the very final scoreline. ([03](./03-historical-close-finish-research.md))

**4. The optimal engine is Option D++ — a calibrated close-finish probability.** Pure time+margin (A) is what we have. Adding scoring rate (B) and momentum (C) helps. The recommended model (D) combines **lead size, time remaining, scoring-rate volatility, momentum (from FlySense), and match context (pre-match yellow rating + home edge)**, fitted as a lightweight, sport-specific calibrated model and surfaced as the **FlyTime Index (0–100)**. A full learned win-probability model (E) is the long-term target but is gated on data collection. ([04](./04-predictive-engine.md), [09](./09-advanced-models.md))

**5. Confidence should become first-class, but expressed as stages, not raw percentages.** Three live stages — **Potential (≈60–80%) → Likely (≈80–95%) → Confirmed (95%+)** — give early signal without crying wolf, and map cleanly onto a fly that "warms up" before it locks. ([05](./05-confidence-system.md))

**6. Stability is a feature, not a detail.** A probabilistic engine that updates every poll will flicker. 2.0 uses **asymmetric hysteresis** (enter a stage high, exit low) plus **probability decay/recovery** so the fly rises early, holds steady, and only drops when the game genuinely de-escalates. ([07](./07-decay-model.md))

**7. FlySense is an input, not a sibling.** Momentum, On Fire, Cold, Comeback and Control already quantify *what is happening now*. Feeding the momentum scalar and comeback state into the FlyTime Index is the single highest-leverage accuracy upgrade available without new data. ([08](./08-flysense-integration.md))

---

## Success criteria (carried into every document)

FlyTime 2.0 must:

- **Detect ≥ 90%** of genuine late-tense matches (recall) per sport.
- **Hold false positives < 10%** (precision) per sport.
- **Predict 5–10 minutes earlier** than the current gate, where the sport's volatility allows it honestly.
- **Never flicker** — no stage should toggle on/off more than is physically justified by the match.
- **Stay glanceable** — a user sees one fly and instantly trusts it; confidence is legible, not noisy.
- **Be cross-sport robust** — the *framework* is shared; the *parameters* are per-sport and data-derived.
- **Degrade honestly** — when data is thin, the engine says "Potential", not "Confirmed".

> The best FlyTime system is not the one that fires the most flies. It is the one a user learns to trust completely: when the fly turns green, they switch over — and they are right almost every time.

---

## How to read this set

- **01–03** are *analysis*: what exists, how each sport behaves, and how to measure truth.
- **04–10** are *design*: the engine, confidence, false-positive control, decay, FlySense fusion, advanced models, and competitive benchmarking.
- **11** is the *synthesis*: the consolidated FlyTime 2.0 spec.
- **12–13** are *operationalisation*: how to validate it and how to ship it without risk (shadow mode → ramp).

> Note on numbers: where this set cites lead-survival percentages, half-lives, or curve values, they are **modelled estimates and design targets** derived from the existing close-rate tables and sport structure, framed so the validation harness in [12](./12-validation-framework.md) can confirm or correct each one against real data before it ships. They are explicitly *hypotheses with a test attached*, not measured production results.
