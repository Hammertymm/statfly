# ScoreFly FlySense 2.0 — Research, Audit, Validation & Evolution Program

**Status:** Research deliverables (docs only — no application code changes)
**Repository:** `scorefly` (this repo — docs live in `_research/FlySense-2.0/`)
**Subject system:** FlySense — ScoreFly's visual momentum language
**Grounded in:** [index.html](../../index.html)

---

## What FlySense is

FlySense is ScoreFly's visual momentum language. Its job is to let a user understand what is happening in a match **without reading text** — by glancing at a score card and instinctively knowing:

- Who is building momentum
- Who is dominating
- Who is cooling off
- Who is mounting a comeback

It communicates through **colour, intensity and motion**.

## The one question FlySense answers

> What are the teams doing **right now**?

FlySense deliberately does **not** measure match quality, excitement, FlyTime probability, importance, betting value or watchability. Those belong to other ScoreFly systems (e.g. the FlyTime engine — see [_research/FlyTime-Intelligence](../FlyTime-Intelligence/README.md)).

---

## Deliverable index

| # | Document | Program part | Description |
|---|----------|--------------|-------------|
| 00 | [00-README.md](./00-README.md) | Framing | This index + executive summary + success criteria |
| 01 | [01-current-system-audit.md](./01-current-system-audit.md) | Part 1 | Complete logic map of the existing FlySense engine |
| 02 | [02-momentum-science.md](./02-momentum-science.md) | Part 2 | Eight perceptual dimensions of momentum |
| 03 | [03-decay-research.md](./03-decay-research.md) | Part 3 | Decay models + per-sport momentum half-life |
| 04 | [04-threshold-research.md](./04-threshold-research.md) | Part 4 | Threshold cliffs vs adaptive bands |
| 05 | [05-gradient-system-design.md](./05-gradient-system-design.md) | Part 5 | Continuous colour ramp + accessibility |
| 06 | [06-comeback-system.md](./06-comeback-system.md) | Part 6 | Comeback audit + intensity tiers |
| 07 | [07-cold-state.md](./07-cold-state.md) | Part 7 | Cold detection, severity, Extreme Cold |
| 08 | [08-visual-intensity.md](./08-visual-intensity.md) | Part 8 | Extreme Cold / Extreme On Fire effects |
| 09 | [09-information-density.md](./09-information-density.md) | Part 9 | Visual channel assignment |
| 10 | [10-sport-specific.md](./10-sport-specific.md) | Part 10 | Per-sport momentum behaviour + parameters |
| 11 | [11-historical-validation-framework.md](./11-historical-validation-framework.md) | Part 11 | Historical validation engine (design) |
| 12 | [12-user-perception-testing.md](./12-user-perception-testing.md) | Part 12 | User perception testing protocol (design) |
| 13 | [13-flysense-2.0-spec.md](./13-flysense-2.0-spec.md) | Synthesis | Consolidated FlySense 2.0 model + migration path |
| 14 | [14-refresh-anomaly-investigation.md](./14-refresh-anomaly-investigation.md) | Integrity | Stale refresh / batched score false-positive investigation + mitigations |

---

## Executive summary

**The current system works and is principled.** FlySense today computes a per-side momentum scalar (0-100) that gains on scoring bursts and decays on a wall-clock exponential half-life, then maps that scalar into one of five discrete states (warming / on a run / on fire / cold / comeback) rendered as solid score colours with a 2.5s crossfade. See [01-current-system-audit.md](./01-current-system-audit.md).

**Four structural limitations motivate FlySense 2.0:**

1. **Hard threshold cliffs.** A side at momentum 67 renders identically to a side at 43 (both "on a run"), while 67 -> 68 flips colour entirely. The discrete tiers throw away most of the 0-100 signal the engine already computes. See [04-threshold-research.md](./04-threshold-research.md).

2. **One momentum number, many human perceptions.** Humans perceive momentum as a blend of volume, velocity, acceleration, opponent suppression, persistence, recovery, reversal and inertia. The current scalar mostly captures *recent volume with decay* and conflates the rest. See [02-momentum-science.md](./02-momentum-science.md).

3. **No per-sport rhythm beyond `bigPlay`.** Decay half-life (49s) and the tier thresholds are global; only `bigPlay`/`cbMin` differ by sport. A soccer goal and an NBA basket decay identically, which does not match how long each "feels" relevant. See [03-decay-research.md](./03-decay-research.md) and [10-sport-specific.md](./10-sport-specific.md).

4. **Colour is the only channel; extremes look like mid-states.** There is no visual difference between "comfortably on fire" (70) and "historic, unstoppable" (99), or between "quiet" cold and a total collapse. Intensity and motion are unused. See [08-visual-intensity.md](./08-visual-intensity.md) and [09-information-density.md](./09-information-density.md).

**The recommended direction (Part 5, the stated preference) is a continuous gradient system:** keep the existing momentum scalar as the backbone, enrich it with the perceptual dimensions, map it through a continuous colour ramp instead of five hard tiers, and reserve intensity/motion for the extremes only. The full proposal and a phased, low-risk migration path that maps onto the existing functions are in [13-flysense-2.0-spec.md](./13-flysense-2.0-spec.md).

---

## Success criteria (carried into every document)

FlySense 2.0 must:

- Remain instantly understandable — recognisable in ~1 second, no explanation required.
- Better reflect human perception of momentum.
- Work across all supported sports.
- Preserve ScoreFly's simplicity and premium feel.
- Increase information density **without** increasing the learning burden.
- Improve momentum accuracy and stability (less flicker, fewer false states).
- Create a richer visual language without adding complexity.

> The best FlySense system is not the one with the most calculations. It is the one where a user looks at a match for one second and instinctively knows exactly what is happening.

---

## How to read this set

- Parts 1-4 are **analysis** (what exists, what humans perceive, how to model decay and thresholds).
- Parts 5-10 are **design** (gradient, comeback, cold, visual intensity, density, sport tuning).
- Parts 11-12 are **validation frameworks** — delivered as runnable-later designs, not executed here (no historical dataset / user panel is wired up yet).
- Document 13 is the **synthesis**: the proposed FlySense 2.0 model plus a migration path expressed against the real functions in [index.html](../../index.html).
