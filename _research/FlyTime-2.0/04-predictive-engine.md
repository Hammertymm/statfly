# Phase 4 — Predictive FlyTime Engine

**Goal:** move from a static threshold gate to an engine that **forecasts FlyTime before it happens**. This document evaluates the five candidate formulations (A–E), then specifies the recommended model.

---

## The shift in one line

> Today: `isFlyTime = (margin ≤ X) AND (clock ≤ Y)` — a snapshot test.
> 2.0: `FlyIndex(t) = P(this match is/【becomes】True FlyTime | everything known at time t)` — a continuously updated forecast.

The output is a **0–100 FlyTime Index** per live match, updated every poll, feeding the multi-stage trigger ([Phase 5](./05-confidence-system.md)) and decay model ([Phase 7](./07-decay-model.md)).

---

## Evaluation criteria

Each option is scored on: **earliness** (can it fire ~10 min out?), **accuracy** (precision/recall ceiling), **robustness** (cross-sport, data-thin tolerance), **cost** (compute + data + maintenance), and **explainability** (can we tell a user *why*?).

---

## Option A — Time + Score differential

This is **essentially today's system** (margin + clock), just made continuous via a lead-safety curve.

- **Earliness:** Limited but real — a √time curve already says "8 pts at 8:00 is unsafe", which is earlier than the flat gate. Best for volatile sports.
- **Accuracy:** Moderate. Ignores *direction* — a stable 8-point game and a collapsing 8-point game look identical.
- **Robustness:** High; works everywhere, degrades gracefully when data is thin.
- **Cost:** Minimal (one curve per sport).
- **Explainability:** Excellent ("8 points, 8 minutes left").
- **Verdict:** The right **floor**. Always available; should be the fallback when richer signals are missing. Not sufficient alone.

## Option B — A + Scoring rate

Add the recent scoring rate / lead-change frequency (volatility). Now a high-scoring shootout at margin 10 reads more dangerous than a defensive grind at margin 10.

- **Earliness:** Better — volatility is a *leading* indicator of swings.
- **Accuracy:** Noticeably higher; volatility is exactly what distinguishes "will tighten" from "will stay put".
- **Robustness:** Good; rate is computable from the score timeline the engine already sees.
- **Cost:** Low (rolling rate from the trajectory buffer added in 2.0).
- **Verdict:** Strict improvement over A. Should be **in** the model.

## Option C — A + Momentum

Add directional momentum: *who is scoring lately and how fast is the margin moving toward zero?* FlySense already computes per-side momentum (0–100), comeback state, and collapse (peak) detection — all free to consume ([08](./08-flysense-integration.md)).

- **Earliness:** Best single addition for earliness — a 14-point lead being actively eaten (trailing side On Fire, leader Cold) is FlyTime-bound *before* the margin is close.
- **Accuracy:** High; momentum captures trajectory, the dimension A/B lack.
- **Robustness:** Depends on FlySense being live (it is, every poll).
- **Cost:** ~Zero marginal (reuse FlySense outputs).
- **Verdict:** The highest-leverage addition. Must be **in**.

## Option D — A + Momentum + Match context

Add pre-match and structural context: the **yellow `flyMatchRating`** (this fixture was predicted close), **home advantage**, **possession/timeouts** (gridiron), **base/out** (MLB), **goalie-pull** (NHL), **required run rate** (cricket). Context acts as a **prior** that shifts the live curve.

- **Earliness:** Best — a fixture pre-rated as a likely nailbiter can be flagged Potential *very* early on modest live evidence; a pre-rated mismatch needs stronger live proof.
- **Accuracy:** Highest of the heuristic options; context resolves the ambiguous mid-game states.
- **Robustness:** Good, *if* missing context degrades gracefully to C→B→A.
- **Cost:** Moderate (per-sport context adapters), but each piece already exists somewhere in the app.
- **Explainability:** Still strong ("predicted close, now within one score, trailing team surging").
- **Verdict:** **Recommended.** It is the natural fusion of every signal the app already produces.

## Option E — Advanced learned probability model

A trained model (gradient-boosted trees or a small logistic/NN) over the full feature set, fit on the labelled history from [Phase 3](./03-historical-close-finish-research.md), outputting calibrated P(True FlyTime).

- **Earliness/Accuracy:** Highest ceiling — learns the per-sport curves and interactions directly, properly calibrated.
- **Robustness:** Good once trained, but needs enough labelled data per sport; risky for Tier B/C leagues.
- **Cost:** Highest — data pipeline, training, calibration, versioning, drift monitoring, and (for a client-side app) shipping/serving the model.
- **Explainability:** Lower (needs SHAP-style attributions to stay glanceable).
- **Verdict:** The **long-term target**, gated on the Phase-3 dataset existing and the validation harness proving it beats D. Not the launch model.

---

## Scorecard

| | Earliness | Accuracy | Robustness | Cost | Explainability | Ship now? |
|---|---|---|---|---|---|---|
| A Time+margin | ◑ | ◑ | ●●● | ●●● | ●●● | floor/fallback |
| B + rate | ●○ | ●○ | ●●● | ●●● | ●●● | yes |
| C + momentum | ●● | ●● | ●● | ●●● | ●● | yes |
| **D + context** | **●●●** | **●●●** | **●●** | **●●** | **●●** | **recommended** |
| E learned | ●●● | ●●●● | ●● (data-gated) | ◔ | ◑ | later |

---

## Recommended model: **D, structured as a calibrated additive index with graceful degradation**

### Core formula (per live match, per poll)

```
FlyIndex(t) = 100 × calibrate_sport(
     w_base   · LeadSafetyDeficit(margin, timeLeft)        // Option A spine (√time / possessions / outs / overs)
   + w_rate   · ScoringVolatility(recentRate, leadChanges) // Option B
   + w_mom    · MomentumPressure(hMom, aMom, comeback, collapse) // Option C  (from FlySense)
   + w_ctx    · ContextPrior(flyMatchRating, homeEdge, sportContext) // Option D
)
```

- `LeadSafetyDeficit` = `1 − LeadSafety(...)` from the Phase-2 per-sport curve. **Always present** (the floor).
- `ScoringVolatility` = normalised recent scoring rate + late lead-change count.
- `MomentumPressure` = a signed term: trailing side's momentum minus leader's, boosted if comeback/collapse states are active. This is what makes the index move *before* the margin does.
- `ContextPrior` = bounded shift from the pre-match yellow rating + sport-specific structural context.
- `calibrate_sport()` = a per-sport monotone calibration (logistic) so the index reads as a true probability and matches the Phase-3 base rate.

### Graceful degradation (robustness requirement)
Each term is **optional**. If FlySense isn't available → drop `w_mom` and renormalise (model → B). If no pre-match rating → drop `w_ctx` (→ C). If only score+clock → A. The engine **never errors**; it reports the best estimate its inputs allow and **caps its confidence stage** accordingly ([Phase 5](./05-confidence-system.md)). A score computed from A alone can reach "Potential" but not "Confirmed".

### Why additive-calibrated rather than a single learned model at launch
1. **Explainable** — every fly can show its reason ("within one score + trailing team On Fire").
2. **Tunable per sport** without retraining — weights/curves are config, mirroring how `FLY_V1_REGISTRY` already works.
3. **Safe in shadow mode** — runs alongside the legacy gate, logged, before it drives UI ([Phase 13](./13-migration-strategy.md)).
4. **A clean on-ramp to E** — the same features and the same `calibrate_sport()` slot accept a learned model later with no UI change.

### Per-sport instantiation
The four weights and the curve are **per sport** (and where needed per league), exactly like today's thresholds. Volatile sports (NRL, NBA, NHL 1-goal) get higher `w_mom`/`w_rate` (early movement is trustworthy). Sticky sports (AFL, NFL two-score) lean on `w_base` and demand more momentum evidence before escalating. Starting weights are a design hypothesis; the harness ([Phase 12](./12-validation-framework.md)) fits them against the Phase-3 labels.

### Worked example (NBA, illustrative)
Margin 11, 9:00 left in Q4, trailing team on a 9–2 run (On Fire), leader Cold, fixture pre-rated 86 (likely close):
- `LeadSafetyDeficit` (√time): 11 pts at 9:00 ≈ moderately unsafe → 0.55
- `ScoringVolatility`: recent burst high → 0.70
- `MomentumPressure`: trailing +On Fire, leader Cold → 0.80
- `ContextPrior`: pre-rated close → +0.15 shift
- Calibrated → **FlyIndex ≈ 74 → Stage "Likely"** with ~9:00 left.

The legacy gate shows **nothing** here (margin 11 > 8, and 9:00 > 5:00). That delta — flagging a Likely FlyTime ~4 minutes before the legacy gate could even become eligible — is the entire value proposition. Proceed to [Phase 5](./05-confidence-system.md) for how the index becomes user-facing stages.
