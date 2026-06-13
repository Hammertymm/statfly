# Phase 3 — Historical Close-Finish Research

**Goal:** define a rigorous, reproducible methodology to answer the only question that matters for calibration — **what actually becomes FlyTime?** — and to build the **FlyTime probability curves** the 2.0 engine reads.

The existing backfill pipeline (`flytime-engine` → `backfill` → `analyze`) already pulls multi-season ESPN history per league ([config.py:31](../../scorefly/flytime-engine/flytime_engine/config.py), `DEFAULT_SEASON_WINDOWS` etc.). This phase specifies how to turn that history into truth labels and curves.

---

## 1. The ground-truth problem (restated and fixed)

The whole system currently leans on **final margin** as a proxy for FlyTime. Phase 1 (§7.6) and the prior FlyTime-Intelligence program both flagged this as invalid. We need a label that captures *late tension*, not the final scoreline.

### 1.1 Proposed truth label: "True FlyTime"

A historical match is **True FlyTime** for a sport if, at any point in its **decisive window**, it was in a *tense state* for a *sustained* time:

```
TrueFlyTime(match) = ∃ t in DecisiveWindow(sport) such that
                     LeadSafety(state_t) ≤ TENSE_CEIL(sport)
                     AND this holds for ≥ MIN_SUSTAIN(sport) of game-time
```

Where:
- **DecisiveWindow** = the portion of the match where a tense state is FlyTime-worthy (e.g. basketball: final ~8:00 of Q4 + OT; soccer: 75'→end; NRL: final ~20:00 of H2 + OT).
- **LeadSafety** = the per-sport curve from Phase 2 (margin in "scores" vs time/possessions remaining).
- **TENSE_CEIL** = the safety level below which a neutral fan would call it "anyone's game".
- **MIN_SUSTAIN** = minimum sustained duration so a single fluke possession doesn't label a blowout as FlyTime (kills the §7.5 over-persistence error).

This label is **trajectory-based**, not endpoint-based. A game tied with 3:00 left that ends in a 12-point flurry is **True FlyTime** (it was unmissable) even though the final margin says "comfortable". A steady 3-point game that was never actually in doubt (one side always controlling) is **not** True FlyTime even though final margin says "close". This is the key correction.

### 1.2 Why not just reuse `isFlyTime()` retroactively?
We should compute it as a *baseline* (it's the production rule), but it inherits the late/binary limitations. The point of the research label is to be **better than the production rule** so we can measure the production rule's recall against it.

---

## 2. Data requirements & reconstruction

ESPN historical endpoints give final box scores and (for many sports) play-by-play / win-probability timelines. The reconstruction pipeline:

| Step | What | Source |
|------|------|--------|
| 1 | Pull season windows per league | existing `backfill` |
| 2 | For each game, reconstruct **(t, homeScore, awayScore)** timeline | play-by-play where available; else scoring-play log |
| 3 | Derive **margin(t)**, **scores-to-tie(t)**, **time/possessions remaining(t)** | computed |
| 4 | Compute **LeadSafety(t)** via the Phase-2 per-sport curve | computed |
| 5 | Apply the True FlyTime label (§1.1) | computed |
| 6 | Also compute legacy `isFlyTime()` retro-label and final-margin proxy | for comparison |
| 7 | Store per-game: label, first-tense-time, max-tension, final margin | DB |

Where play-by-play is unavailable (some lower leagues), fall back to **scoring-play timestamps** (enough to reconstruct margin(t) at every score change, which is all the curve needs).

> Honest limitation: not all 45 leagues have rich PBP. Tier leagues by data richness (A: full PBP — NBA/NFL/NHL/MLB/AFL/NRL/EPL; B: scoring-play only; C: final + line score). Curves for Tier A are trustworthy; Tier B/C inherit a shared sport-family curve until they earn their own.

---

## 3. Per-sport metrics to extract

For each sport, from the reconstructed timelines:

| Metric | Definition | Use |
|--------|------------|-----|
| **Close-finish base rate** | % of games that are True FlyTime | sets the prior; sanity-checks thresholds |
| **Entry-time distribution** | when True FlyTime first becomes true | sets earliest-viable trigger |
| **Margin-at-time survival** | P(stays tense \| margin m, time t) | the core curve |
| **Comeback distribution** | P(trailing side ties/leads \| deficit d, time t) | feeds decay/recovery |
| **False-positive rate of legacy gate** | legacy green but not True FlyTime | benchmark to beat |
| **False-negative rate of legacy gate** | True FlyTime but legacy never fired | benchmark to beat |
| **Lead-change frequency late** | volatility proxy | scoring-rate volatility input |

The **close-finish base rate** can be seeded today from the `matchup_close_rates` already in each `*-flytime-v1.json` (tiered in [StatFly §7](../../scorefly/StatFly_FlyTime_Threshold_Recommendations.md): AFL ~27.5% low; NRL/MLB/IRL high 49–68%). These are *final-margin* close rates and will be **higher** than the trajectory-based True FlyTime rate for sticky sports and roughly similar for volatile ones — a useful cross-check.

---

## 4. FlyTime probability curves

The deliverable of this phase is, per sport, a function:

```
FlyTimeProb(margin, timeLeft, [volatility]) → P(match is/【will be】True FlyTime)
```

estimated empirically (binning + smoothing, then a fitted logistic for compactness). Worked illustrative shapes (to be confirmed by the harness — these are the *hypotheses*):

### 4.1 NBA — "+8 with 10:00 left"
Basketball lead safety ≈ governed by √time. With ~10:00 (600s) left, an 8-point lead is **not** safe:
```
P(True FlyTime | margin 8, 10:00 left) ≈ 0.70–0.80
```
By contrast at 2:00 left the same 8 points is much safer (fewer possessions):
```
P(True FlyTime | margin 8, 2:00 left)  ≈ 0.35–0.45
```
This non-monotonicity in *time* (more time left → an 8-pt lead is *less* safe) is exactly what the flat "≤5:00, ≤8" gate cannot express, and is why NBA can be predicted early.

### 4.2 AFL — "+14 with 12:00 left"
AFL leads are sticky (base close rate ~27.5%). 14 points ≈ 2.3 goals:
```
P(True FlyTime | margin 14, 12:00 left in Q4) ≈ 0.35–0.45
```
Lower than the NBA case despite similar "score units", because AFL scoring is steady and high-volume — the trailing side rarely manufactures the required burst. Honest early confidence in AFL is therefore *lower*; the engine should say "Potential", not "Likely", here.

### 4.3 NRL — "+6 with 9:00 left"
6 points = one converted try; NRL one-score games are genuinely volatile late:
```
P(True FlyTime | margin 6, 9:00 left in H2) ≈ 0.75–0.85
```
High and early — NRL supports a confident early trigger in the one-score band.

### 4.4 The general shape

```
P(FlyTime)
  1 │                         NRL +6        ░░░░░░░░  (volatile sports: high & flat-ish)
    │                    ░░░░░░░░░░░░░░░░░░
0.7 │        NBA +8 ░░░░░
    │      ░░░░░
0.5 │   ░░░          AFL +14 ▒▒▒▒▒▒▒▒▒
    │ ░░          ▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒  (sticky sports: lower, decays faster with time)
0.3 │░         ▒▒▒
    └────────────────────────────────────────── time left →
```

Two families emerge:
- **Volatile** (NBA, NRL, NHL 1-goal, soccer level, cricket tight chase): high FlyTime probability that is detectable **early** — these are where the "10 minutes out" goal is most achievable.
- **Sticky** (AFL, NFL two-score, MLB multi-run): lower probability for the same nominal margin; honest early detection is harder, so the engine should lean to lower-confidence stages earlier and reserve "Confirmed" for genuinely tight late states.

---

## 5. Methodology for false-positive / false-negative discovery

Using the True FlyTime label as truth, for **every historical game** classify the legacy production gate:

| Quadrant | Legacy gate | True FlyTime | Name |
|----------|-------------|--------------|------|
| TP | fired | yes | hit |
| FP | fired | no | **false alarm** (e.g. momentary margin-8 touch in a blowout — §7.5) |
| FN | never | yes | **miss** (e.g. tied at 3:00, ended +12, but legacy only fires while margin≤8) |
| TN | never | no | correct reject |

Aggregate per sport → legacy precision/recall baseline. **This is the number FlyTime 2.0 must beat**, and the harness in [Phase 12](./12-validation-framework.md) computes it directly.

Expected pattern from the structural analysis:
- **High FN in sticky sports** measured against a trajectory label is less of an issue; the bigger FN source is the **late-clock cliff** (games that were tense at 7:00 but tidy by 5:00).
- **High FP from the blowout-buffer pin** (§7.5) — single touches inflating red-fly counts.
- **Soccer FN** from discarded stoppage time and margin-2 frantic finishes.

---

## 6. Deliverables of Phase 3

1. **`TrueFlyTime` labeller** — per-sport function over reconstructed timelines (design above; implement in `flytime-engine`).
2. **Per-sport FlyTime probability curves** — fitted `FlyTimeProb(margin, timeLeft, volatility)`.
3. **Entry-time distributions** — earliest-viable trigger per sport (feeds Phase 2 bands).
4. **Legacy-gate confusion matrix** — the precision/recall baseline to beat.
5. **Base-rate table** — True FlyTime % per sport (the prior for the probability model).

These five artifacts are the empirical foundation the predictive engine ([Phase 4](./04-predictive-engine.md)) consumes. Until they are produced from real reconstructed timelines, every threshold in 2.0 ships in **shadow mode** ([Phase 13](./13-migration-strategy.md)) and is treated as a hypothesis, not a fact.
