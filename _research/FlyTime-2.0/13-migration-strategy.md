# Phase 13 — Migration Strategy

**Goal:** get from today's binary gate to FlyTime 2.0 **without ever shipping a regression** and without a risky big-bang rewrite. The principle: **shadow first, prove per sport, ramp confidence, never remove the safety net until the replacement has earned it.**

---

## 1. Guiding rules

1. **No UI change ships before the engine beats the legacy baseline in shadow** for that sport ([Phase 12](./12-validation-framework.md)).
2. **The legacy gate stays alive** as a Confirmed corroborator and rollback target until 2.0 has months of green metrics.
3. **One sport at a time.** Start where data is richest and the win is biggest (NBA, NRL, NHL — volatile, well-studied, early-detectable).
4. **Reuse before you build.** Every early step consumes existing outputs (FlySense, yellow rating, tuning tables); no new data dependencies until later stages.
5. **Everything logged from day one** — the closed ledger is the prerequisite, not a finishing touch.

---

## 2. Phased rollout

### Stage 0 — Instrument (close the loop) — *foundational*
- Make live detection write back to `flyLedger`: `a:1` when a stage is reached, `fin:1`/`rf:1` on completion, plus first-fire times and the legacy comparison.
- Add the in-session rolling trajectory buffer (t, margin, momentum) per live match.
- **Ship nothing visible.** This alone fixes the "open ledger" blind spot ([Phase 1 §4.3](./01-current-system-audit.md)) and starts collecting the dataset 2.0 needs.
- *Exit criteria:* ledger rows populate with real outcomes for ≥ 2 weeks across sports.

### Stage 1 — Build the index in shadow
- Implement `computeFlyTime()` (the [Phase 11](./11-flytime-2.0-spec.md) additive CFP model) reading FlySense + yellow rating; compute FlyIndex + stage every poll; **log only**.
- Implement the backtest harness ([Phase 12](./12-validation-framework.md)) over reconstructed history; fit per-sport weights/curves against the True FlyTime label ([Phase 3](./03-historical-close-finish-research.md)).
- Surface FlyIndex + stage + reasons in **FlyTime Lab** (`?flylab=1`) for internal eyes.
- *Exit criteria:* per-sport backtest meets targets and beats legacy for the launch sports.

### Stage 2 — Pilot one sport in UI (Confirmed only)
- Pick the strongest shadow performer (likely **NRL** or **NBA**).
- Render **only the Confirmed stage** at first — visually ≈ today's green fly, so users see no behaviour change except it may fire a bit earlier and more accurately.
- Keep legacy gate running in parallel; alert internally on any divergence where legacy fired and 2.0 didn't (guard against new FNs).
- *Exit criteria:* live precision ≥ 95% Confirmed, recall ≥ legacy, no flicker, for the pilot sport over a meaningful sample.

### Stage 3 — Introduce Potential & Likely (the earliness payoff)
- Turn on the **Potential** (ambient) and **Likely** (pulse) stages for the pilot sport.
- This is the first time users get the *earlier-than-before* signal — monitor trust signals and the Potential→fizzle rate closely.
- Add the optional **"Potentials" rail** for power users.
- *Exit criteria:* Likely ≥ 85% / Potential ≥ 60% precision live; positive lead-time vs legacy confirmed; no rise in user-reported false alarms.

### Stage 4 — Roll out sport by sport
- Repeat Stages 2–3 per sport, in data-richness order: NBA/NRL/NHL → NFL/AFL/MLB → soccer → cricket → Tier B/C leagues (on shared sport-family curves).
- Each sport graduates independently; a sport stays on the legacy gate until it passes.
- *Exit criteria:* all sports live on 2.0 with metrics met.

### Stage 5 — Retire legacy & add learned models
- Once every sport has sustained green metrics, demote `isFlyTime()` from primary gate to internal corroborator/test-oracle; remove `FLY_BLOWOUT_MARGIN` pinning (superseded by hysteresis).
- Introduce the learned CFP model (Option E) on data-rich sports via the `calibrate_sport()` slot — no UI change ([Phase 9](./09-advanced-models.md)).
- *Exit criteria:* hybrid (learned + additive) live; legacy retained only as a frozen baseline.

---

## 3. Risk register & mitigations

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| New engine introduces FNs legacy caught | medium | Stage 2 parallel-run alert; Confirmed corroborated by legacy initially |
| Potentials feel noisy / erode trust | medium | ambient visual; per-sport Potential threshold; fizzle-rate monitoring; can disable Potential per sport |
| Flicker on live data | medium | hysteresis + sustain + EMA ([Phase 7](./07-decay-model.md)); stability metric gates rollout |
| Thin-data sports overconfident | medium | degradation cap (no momentum/context → Potential ceiling) |
| Clock-polarity bug (AFL/NRL) carried forward | low | add explicit assertion/test for `clockSec` meaning ([Phase 1 §7.1](./01-current-system-audit.md)) in Stage 0 |
| Backtest ≠ live (drift) | medium | same metrics both layers; nightly comparison; per-sport re-gate |
| Scope creep into FlySense | low | one-way dependency only ([Phase 8 §2 Q4](./08-flysense-integration.md)) |

**Rollback:** at any stage, a sport can revert to the legacy gate by a single per-sport flag (mirrors how `FLY_V1_REGISTRY` thresholds are already per-league config). No data is lost; the ledger keeps recording.

---

## 4. Sequencing summary

```
Stage 0  Instrument + buffer          (invisible)        ── unblocks everything
Stage 1  Index in shadow + backtest   (lab only)         ── prove it on paper + live data
Stage 2  Confirmed in UI, 1 sport     (≈ today's fly)    ── no-regression beachhead
Stage 3  Potential + Likely, 1 sport  (the earliness)    ── deliver the headline value
Stage 4  Sport-by-sport rollout       (data-rich first)  ── scale safely
Stage 5  Retire legacy + learned model (hybrid)          ── end state
```

Each arrow is gated by [Phase 12](./12-validation-framework.md) metrics. The user never experiences a downgrade; they experience FlyTime getting quietly earlier and more trustworthy, one sport at a time.

---

## 5. Files this will touch when implementation begins (reference)

| File | Change |
|------|--------|
| `scorefly/index.html` | new `computeFlyTime()`, FlyIndex/stage state on match objects, stage-based fly rendering, ledger write-back, trajectory buffer; `isFlyTime()` demoted to corroborator |
| `scorefly/flytime-engine/flytime_engine/flytime.py` | CFP estimator + per-sport `LeadSafetyDeficit`, `MomentumPressure`, `calibrate_sport`; True FlyTime labeller |
| `scorefly/flytime-engine/flytime_engine/config.py` | per-sport 2.0 weights/curves alongside existing thresholds |
| `scorefly/flytime-engine/validate_flytime_rules.py` | add FlyIndex/stage/hysteresis/degradation tests |
| `*-flytime-v1.json` | unchanged (yellow); optionally extended with reconstructed True-FlyTime base rates |

*(No code is changed in this research pass — this is the implementation map for when the program moves from spec to build.)*
