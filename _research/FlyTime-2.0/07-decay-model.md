# Phase 7 — FlyTime Decay Model

**Goal:** specify how FlyTime probability **rises, holds, falls, and recovers** over the course of a match, and how the stage triggers stay **stable** (no flicker) while remaining **responsive**. This is what makes a continuous probabilistic engine feel trustworthy rather than twitchy.

This design borrows directly from FlySense 2.0's decay work ([FlySense 03](../FlySense-2.0/03-decay-research.md)) and the existing per-sport `halflife` table already in production ([index.html:1761](../../scorefly/index.html)).

---

## 1. Two things decay, and they are different

| Quantity | What decays | Driver |
|----------|-------------|--------|
| **The FlyIndex itself** | the underlying probability estimate | match state (margin, time, momentum) changes |
| **The displayed stage** | the user-facing Potential/Likely/Confirmed | the index *crossing* hysteresis bands, with sustain |

The index is allowed to move freely every poll. The **stage** is deliberately sticky. Keeping these separate is the core of anti-flicker.

---

## 2. FlyIndex dynamics

### 2.1 Rise
The index rises when the match tightens or momentum turns toward the trailing side. Rise should be **fairly quick** — earliness is the goal. A converted try in NRL or a 9–0 NBA run should bump the index within a poll or two.

### 2.2 Natural time pressure (the index rises *on its own* as time runs out)
Unlike FlySense momentum (which only decays toward zero with time), FlyTime has a built-in **clock term that *raises* tension as the decisive window shrinks** for a still-close game. A 1-goal hockey game becomes *more* FlyTime at 1:00 than at 8:00. So the `LeadSafetyDeficit` term ([Phase 4](./04-predictive-engine.md)) increases monotonically as time→0 *while the margin stays in band*. This is the opposite of momentum decay and must not be conflated with it.

### 2.3 Decay (the index falls)
The index falls when the game de-escalates:
- **Lead extends** → `LeadSafetyDeficit` drops sharply (the dominant decay driver).
- **Momentum disappears** → `MomentumPressure` decays on the FlySense half-life.
- **Scoring rate slows** with a stable margin → volatility term fades.

Each input term has its **own decay speed**:

| Term | Decay behaviour |
|------|-----------------|
| `LeadSafetyDeficit` | event-driven (recomputed from margin/time each poll) — can drop instantly when the lead jumps |
| `MomentumPressure` | exponential, per-sport half-life (reuse FlySense `halflife`: NBA 40s, soccer 90s, NHL 70s, AFL/NRL 55s, MLB 75s, cricket 90s) |
| `ScoringVolatility` | rolling window (e.g. last ~3–5 min of game-time) |
| `ContextPrior` | constant (pre-match), only fades in relative weight as live evidence accumulates |

### 2.4 Recovery (can FlyTime rebuild?)
**Yes, and this is a required feature.** A game that blows out to +18 and then claws back to +6 must be able to re-enter FlyTime. Because the index is recomputed from live state every poll, recovery is automatic — there is no "used up" flag. This fixes a conceptual flaw in today's pin model (once pinned, always pinned until blowout; once blown out, no clean re-entry path). The 2.0 index simply tracks reality up and down.

---

## 3. Stage stability — asymmetric hysteresis + sustain

To stop the displayed stage flickering while the index wiggles around a band edge:

### 3.1 Asymmetric (enter-high / exit-low) bands
Each stage has **two** thresholds — a higher one to **enter**, a lower one to **exit**:

| Stage | Enter at FlyIndex ≥ | Exit (drop) at FlyIndex < |
|-------|---------------------|----------------------------|
| Potential | 62 | 55 |
| Likely | 82 | 74 |
| Confirmed | 95 | 88 |

(Illustrative; calibrated per sport.) A match at index 80 that briefly dips to 78 stays "Likely". This is exactly the hysteresis pattern FlySense 2.0 already uses for its tiers ([index.html:1873](../../scorefly/index.html)), so the codebases stay consistent.

### 3.2 Sustain (debounce on entry)
A stage is only **shown** after the enter-threshold is held for a minimum sustained period (e.g. ~2 polls / ~15–20s, per sport). Kills single-poll spikes (a stat-correction blip, a momentary margin touch — Phase 1 §7.5/§7.4). Exit can be **faster** than entry for safety on genuine blowouts (we'd rather drop a dead game quickly than show a stale Confirmed).

### 3.3 Index smoothing
Apply light EMA smoothing to the raw FlyIndex before band-testing, so the input to the hysteresis logic is already de-noised. Smoothing constant is per-sport (volatile sports smooth less to preserve earliness).

### 3.4 Directional asymmetry summary
```
RISE:    quick   (earliness)         + sustain gate on first show  (anti-spike)
HOLD:    sticky  (hysteresis band)
FALL:    medium  (let genuine blowouts clear) but never instant from a single poll
RECOVER: automatic (recomputed live, no lockout)
```

---

## 4. Worked trajectory (NBA, illustrative)

```
Q4 time→  10:00   8:00    6:00    4:30    3:00    1:30    0:30   FINAL
margin     +14    +11     +12     +8      +5      +3      +6     +4
momentum    —    trail▲  flat   trail▲▲  swing   tense   —       —
FlyIndex    48     74      66      85      92      97      90     —
stage      —    POTENTL  POTENTL LIKELY  LIKELY  CONFIRM CONFIRM (red fly)
```

Note the behaviours this exercises:
- **Early Potential at 8:00** (index 74) driven by trailing momentum on a 14→11 cut — *legacy gate shows nothing here.*
- **Held through the 11→12 wobble** (66, dipped but stayed above Potential exit 55) — no flicker.
- **Escalation to Likely at 4:30** when margin enters one-score AND momentum corroborates.
- **Brief late stretch to +6 at 0:30** — index dips to 90 but stays **Confirmed** (above exit 88) — no embarrassing drop in the final seconds of a one-score game.
- Legacy gate would have first fired around 4:30–3:00; 2.0 first surfaced ~3.5 minutes earlier.

---

## 5. Why this matters for trust

Flicker is the fastest way to lose credibility: a fly that blinks on/off reads as "the app doesn't know either". The decay/hysteresis architecture guarantees that once FlyTime 2.0 makes a claim, it **stands by it** until the match genuinely changes — rising early, holding steady, falling only on real de-escalation, and recovering when drama returns. This is the behavioural contract that lets the engine be aggressive about earliness without feeling unreliable. Proceed to [Phase 8](./08-flysense-integration.md).
