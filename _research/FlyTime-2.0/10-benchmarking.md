# Phase 10 — Benchmarking

**Goal:** position FlyTime against the established live-prediction systems, identify what to borrow, and define the differentiation that is defensible long-term.

The essential framing: **almost every public system predicts the wrong thing for our purpose.** They predict *who will win* (Win Probability). FlyTime predicts *whether the match is worth watching* (Close-Finish Probability). The benchmark is therefore partly "are we as accurate at the shared sub-problem (lead safety)?" and partly "are we solving a problem nobody else is?".

---

## 1. The comparison set

| System | Predicts | Sports | Public live? | Relevance to FlyTime |
|--------|----------|--------|--------------|----------------------|
| **ESPN Win Probability** | win % per team | NFL/NBA/MLB/soccer + | yes (in-game) | Best WP feed; ingest as a feature where available |
| **NBA WP models** (Inpredictable, ESPN, others) | win % | NBA | yes | Gold standard for √time lead-safety curves — borrow the math |
| **AFL predictive models** (Squiggle, club/media) | win % / margin | AFL | partial | Validates AFL "sticky lead" thesis; sparse live |
| **Betting market implied probability** | win % (vig-adjusted) | all major | yes (odds move live) | Most accurate live WP that exists; use as a *ceiling benchmark* |
| **Public live predictors** (broadcast graphics, fan apps) | win % / "excitement" | varies | varies | Some "excitement"/"watchability" attempts — our closest conceptual competitors |

---

## 2. Strengths & weaknesses vs each

### vs ESPN Win Probability
- **Their strength:** mature, multi-sport, well-calibrated WP; live timelines.
- **Their weakness (for us):** WP ≠ FlyTime ([Phase 9 §1](./09-advanced-models.md)). ESPN tells you the favourite is 78% — it does **not** tell you "this is a one-possession game with 6:00 left and the trailing team surging, switch over." It also isn't framed for *discovery across many simultaneous games*.
- **FlyTime edge:** we answer the watchability question and rank *across* matches; we can *consume* ESPN WP as an input where present.

### vs NBA WP models
- **Their strength:** the best-studied lead-safety curves in sport (the √time relationship, foul-game adjustments).
- **Their weakness:** single-sport; not a cross-sport discovery product.
- **FlyTime action:** **borrow their curve shape directly** for basketball ([Phase 2](./02-sport-by-sport-analysis.md)); it's a solved problem we shouldn't reinvent.

### vs AFL models (Squiggle etc.)
- **Their strength:** good margin/win models; community-validated.
- **Their weakness:** limited live in-play granularity; win-focused.
- **FlyTime action:** use to **validate the "AFL leads are sticky" thesis** (low close rate ~27.5%) and calibrate honest (lower) early-confidence for AFL.

### vs Betting markets
- **Their strength:** the most accurate live probabilities in existence — real money, fast updates, all signals priced in.
- **Their weakness:** predict win, not watchability; carry vig and bias; legally/commercially sensitive to embed; not a fan-discovery UX.
- **FlyTime action:** use implied probability as a **benchmark ceiling** for the lead-safety sub-problem in [Phase 12](./12-validation-framework.md) — "how close is our `LeadSafety` to the market's?" — but never as a product surface.

### vs public excitement predictors
- **Their strength:** some target watchability directly (closest to us conceptually).
- **Their weakness:** typically post-hoc ("this was a great game") or single-sport, rarely a live, cross-sport, glanceable, momentum-aware **discovery** layer.
- **FlyTime edge:** live + predictive + cross-sport + integrated with a momentum language (FlySense) + a glanceable confidence UI.

---

## 3. Where FlyTime can be genuinely best-in-class

| Dimension | Incumbents | FlyTime 2.0 opportunity |
|-----------|------------|--------------------------|
| **Target variable** | Win probability | **Close-Finish / watchability probability** — the thing fans actually want |
| **Cross-sport** | mostly single-sport | one coherent index across 45+ leagues |
| **Discovery** | per-game widgets | "what should I watch *right now*" ranking |
| **Earliness framing** | WP just is what it is | explicit Potential→Likely→Confirmed escalation |
| **Momentum fusion** | rare | FlySense-driven leading indicator ([Phase 8](./08-flysense-integration.md)) |
| **Glanceability** | numbers/charts | one fly, intensity = confidence |

---

## 4. Differentiation strategy (the moat)

1. **Own "watchability", not "who wins".** Nobody owns the cross-sport "is this worth switching to" question as a polished consumer product. That is the wedge — and it aligns with the commercial framing in [FlyTime-Intelligence/09-competitive-advantage](../FlyTime-Intelligence/09-competitive-advantage.md).
2. **Cross-sport unification.** A single FlyTime Index that means the same thing in NRL and NBA is something single-sport incumbents structurally cannot offer.
3. **Momentum-aware earliness.** Fusing FlySense makes FlyTime a *leading* indicator; pure WP feeds are lagging on the watchability question.
4. **Proprietary trajectory truth label.** The True FlyTime label + the closed ledger ([Phase 6](./06-false-positive-elimination.md)) become a dataset nobody else has — the long-term data moat ([FlyTime-Intelligence/17-roadmap-12-month](../FlyTime-Intelligence/17-roadmap-12-month.md)).

**Phase 10 conclusion:** benchmark *components* against the best (borrow NBA √time curves, validate against ESPN WP and market implied probability), but compete on a *different target* — Close-Finish Probability — delivered as a cross-sport, momentum-aware, glanceable discovery layer. That combination is not currently offered by any incumbent. Proceed to [Phase 11](./11-flytime-2.0-spec.md).
