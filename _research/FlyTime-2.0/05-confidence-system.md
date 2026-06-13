# Phase 5 — FlyTime Confidence System

**Question:** should FlyTime operate with explicit confidence levels, and if so, should confidence be hidden internal machinery or a user-facing part of the FlyTime language?

**Recommendation:** **Yes — confidence is essential, and it should be user-facing, but expressed as a small number of named stages, not raw percentages.**

---

## Why confidence is unavoidable in a predictive system

The moment FlyTime stops being "margin ≤ 8 right now" (a fact) and becomes "this will be a close finish" (a forecast), it acquires uncertainty by definition. A forecast with no confidence attached is either over-claiming (fires early and is sometimes wrong → erodes trust) or over-cautious (waits until certain → loses the earliness that is the entire point). Confidence is the dial that lets us be **early AND trusted** at the same time: be loud when sure, tentative when not.

The current binary system hides this by only ever firing when it is ~certain (margin already tight, clock already late). 2.0 trades some of that certainty for earliness — and confidence is how we manage that trade honestly.

---

## The three live stages

Map the continuous FlyIndex (0–100) to three named stages with the brief's bands:

| Stage | FlyIndex band | Meaning to the user | Posture |
|-------|---------------|---------------------|---------|
| **Potential FlyTime** | ≈ 60–80 | "This could get tense — keep an eye on it." | early, soft, low commitment |
| **Likely FlyTime** | ≈ 80–95 | "This is heading for a close finish." | confident, draw attention |
| **Confirmed FlyTime** | 95%+ | "This is a nailbiter right now — switch over." | full alert, the classic green fly |

- **Below ~60:** no fly (normal match).
- **Confirmed** is the spiritual successor to today's green fly — but now it can be *reached earlier* and via *more paths* than "margin ≤ 8, ≤ 5:00".
- The stages are the same across all sports; the **FlyIndex required to reach each stage is calibrated per sport** ([Phase 4](./04-predictive-engine.md)) so "Likely" means the same *probability* everywhere even though the *evidence* differs.

### Honesty cap by data availability
A match scored from thin inputs (Option A only — no momentum, no pre-match rating) is **capped at Potential**. To reach Likely it needs live trajectory evidence; to reach Confirmed it needs either the legacy-style tight-late state OR a high calibrated index with corroborating momentum. This guarantees the loudest signal is never built on the weakest data.

---

## Benefits

1. **Earliness without crying wolf.** Potential lets the engine surface a developing game ~10 min out at low commitment; if it fizzles, the user was only ever told "could" — trust intact.
2. **Graduated attention.** Users self-select: casual fans act on Confirmed; FlyTime power-users hunt Potentials. One feature serves both.
3. **A natural UI escalation.** A fly that "warms up" (Potential → Likely → Confirmed) is more engaging and informative than one that blinks on at the last moment. It mirrors the drama itself building.
4. **Calibratable & measurable.** Each stage gets its own precision target ([Phase 12](./12-validation-framework.md)): Confirmed must be ~95% precise; Potential is allowed to be ~60% because it only ever promised "could".
5. **Graceful degradation has a home** — thin data → capped stage, communicated honestly.

## Risks (and mitigations)

| Risk | Mitigation |
|------|------------|
| Stage flicker (Potential↔Likely every poll) | Asymmetric hysteresis — enter high, exit low ([Phase 7](./07-decay-model.md)). |
| Too many Potentials → noise/banner blindness | Per-sport Potential threshold tuned to a sane volume; Potentials are visually quiet (see UI). |
| Users distrust a Potential that fizzles | Frame as "could", never "will"; only Confirmed makes a strong promise. |
| Cognitive load of three states | Use **one fly that changes intensity**, not three different icons. Glanceable. |
| Confidence % looks like fake precision | Show **named stages**, not "73.4%". Reserve the raw number for the debug lab. |

---

## UI implications

The fly stays a single recognisable mark; **stage = intensity**, not a new symbol:

| Stage | Visual (recommendation) |
|-------|--------------------------|
| Potential | faint/outline fly, muted colour, no motion — "ambient" |
| Likely | solid fly, full colour, gentle pulse — "notice me" |
| Confirmed | solid fly, bright, stronger pulse/glow — today's green-fly energy |

This deliberately mirrors the FlySense 2.0 direction (continuous intensity, motion reserved for extremes — [FlySense 08](../FlySense-2.0/08-visual-intensity.md)), keeping ScoreFly's visual language coherent: **colour = what kind of state, intensity = how strong/sure.** A user already fluent in FlySense reads FlyTime stages with zero new learning.

Optional surfaces:
- A **"Potentials" rail** for power users (the natural home for the "top FlyTime picks" idea from the StatFly doc).
- The numeric FlyIndex and stage history stay in **FlyTime Lab** (`?flylab=1`) for tuning, never in the default UI.

---

## Recommendation

**Confidence becomes a first-class, user-facing part of FlyTime — as three named stages (Potential / Likely / Confirmed) driven by the calibrated FlyIndex, rendered as one fly with escalating intensity, stabilised by hysteresis, and capped honestly by data availability.** Keep the raw percentage internal. This is what lets FlyTime 2.0 be dramatically earlier than today's gate **without** spending the user trust that makes the feature valuable. Proceed to [Phase 6](./06-false-positive-elimination.md).
