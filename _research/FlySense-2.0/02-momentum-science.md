# 02 — Momentum Science (Part 2)

**Question:** What do humans actually perceive as momentum?

Momentum is a perception, not a measurement. A crowd "feels" a run before the scoreboard justifies it. This document breaks that feeling into eight measurable dimensions, states which the current engine captures, and proposes a computable signal for each using **only score+time data** (the inputs FlySense actually has — see [01-current-system-audit.md](./01-current-system-audit.md) §2).

A guiding constraint throughout: FlySense has no play-by-play. Every signal below must be derivable from the sequence of `(scoreHome, scoreAway, timestamp)` samples.

---

## The single-scalar baseline

Today momentum is one number per side:

```
mom = clamp(prev*decay + min(delta/bigPlay,1.6)*gain, 0..100)
```

This is, in perceptual terms, **decayed recent scoring volume**. It is a strong backbone but it implicitly fuses several distinct human perceptions and omits others entirely. The eight dimensions below are the decomposition.

---

## 1. Scoring volume — *how much scoring occurred?*

**Perception:** A side that has scored a lot recently feels dominant.

**Current capture:** Strong. The `gain` term is volume, normalised by `bigPlay` so "a lot" is sport-relative.

**Signal:** Sum of points scored in a trailing window `W`, normalised by `bigPlay`.

```
volume = sum(myDelta over last W seconds) / bigPlay
```

**Gap:** Volume is currently entangled with decay; it is never available as a clean number for, e.g., distinguishing "scored a lot slowly" from "scored a little fast".

---

## 2. Scoring velocity — *how quickly did scoring occur?*

**Perception:** 14 points in 90 seconds feels far hotter than 14 points across a quarter.

**Current capture:** Partial. Velocity is implied because `gain` is added per poll and decays, so faster scoring stacks before it decays. But it is never measured as rate.

**Signal:** Points per unit time over the trailing window.

```
velocity = sum(myDelta over W) / W      // points per second
velocityNorm = velocity / expectedRate(sport)
```

`expectedRate(sport)` is the sport's typical scoring rate (see [10-sport-specific.md](./10-sport-specific.md)). Normalising makes velocity comparable across sports.

**Why it matters for 2.0:** Velocity is the cleanest driver of the "on fire" feeling. Two sides on the same volume but different velocity should not look identical.

---

## 3. Scoring acceleration — *is momentum increasing?*

**Perception:** A run that is *speeding up* feels different from one that is steady. Acceleration is the leading edge of "something is happening".

**Current capture:** None. The engine has no second-order term.

**Signal:** Change in velocity between two trailing windows (recent vs prior).

```
accel = velocity(recentHalf of W) - velocity(priorHalf of W)
```

`accel > 0` => intensifying (candidate for brightening / motion onset). `accel < 0` => fading (candidate for desaturation even before momentum decays). This is the signal that lets FlySense 2.0 react *before* the scalar fully reflects a surge.

---

## 4. Opponent suppression — *has the opposition stopped scoring?*

**Perception:** Dominance is not only your scoring — it is *also* the other team going silent. A 10-0 run feels more dominant than 10-8.

**Current capture:** Indirect only. Because momentum is per side and the opponent's momentum decays independently, a quiet opponent simply fades; cold uses `oppMom >= 42` but nothing rewards *suppression* in the dominant side's own score.

**Signal:** Ratio of my recent scoring to total recent scoring.

```
suppression = mySum(W) / (mySum(W) + oppSum(W) + epsilon)
```

`suppression -> 1` means I own the run outright. A useful **dominance** composite is `velocityNorm * suppression`: fast scoring *while* the opponent is shut out.

**Why it matters:** Suppression is the dimension that separates "on a run" from "in total control", and is the natural input to a stronger Cold state for the *other* side (see [07-cold-state.md](./07-cold-state.md)).

---

## 5. Momentum persistence — *how long has pressure been sustained?*

**Perception:** A run that has lasted three minutes feels more "real" and stable than a 20-second flurry. Persistence builds trust in the state.

**Current capture:** Weak/none. Decay actively works *against* persistence — momentum starts fading 49s after the last score regardless of how long the run has lasted. There is no memory of run duration.

**Signal:** Duration since the run began (the time since the side's momentum first crossed a "warming" floor and has stayed above it).

```
persistence = now - runStartTs     // seconds the side has held elevated momentum
```

**Use:** Persistence should *slow decay* (a long-established run cools more gently) and can drive **stability** — a persistent state should be slower to relinquish its colour. This is the antidote to flicker that does not require simply slowing all decay. See [03-decay-research.md](./03-decay-research.md).

---

## 6. Momentum recovery — *how quickly can momentum return after fading?*

**Perception:** A team that scored, went quiet, then scored again "re-ignites" faster than a cold-start team. Humans give credit for a recent prior run.

**Current capture:** Partial and accidental. If momentum has not fully decayed, the next gain stacks on the residue — so recovery is faster while embers remain. But once it hits 0 there is no memory.

**Signal:** A slow-decaying "ember" floor that remembers recent peak momentum.

```
ember = max(ember*slowDecay, momPeakRecent)
recoveryBoost = f(ember)   // a new gain after a lull is amplified while ember > 0
```

**Use:** Lets FlySense 2.0 re-light a team quickly on a second surge (matching perception) without making cold-start surges over-react.

---

## 7. Momentum reversal — *how quickly can momentum switch teams?*

**Perception:** The most dramatic moment in sport is the swing — momentum visibly transferring from one side to the other. Users should *feel* the handover.

**Current capture:** Implicit. Each side rises/decays independently, so a reversal happens as one fades and the other rises — but there is no explicit cross-over signal and no special treatment of the moment of crossing.

**Signal:** Sign and rate of the momentum differential.

```
diff = myMom - oppMom
reversalRate = d(diff)/dt
```

A fast `reversalRate` through zero is a **swing event**. This is the natural trigger for the comeback intensity tiers ([06-comeback-system.md](./06-comeback-system.md)) and for a brief transition emphasis in the gradient ([05-gradient-system-design.md](./05-gradient-system-design.md)).

---

## 8. Momentum inertia — *should momentum continue after scoring pauses?*

**Perception:** This is the subtle one the brief calls out explicitly. Humans perceive momentum **continuing during a pause** — a team that just scored three times still "has it" even in the 40 seconds before the next play. Momentum does not vanish the instant scoring stops.

**Current capture:** This is exactly what the 49s exponential half-life models — the gentle, principled core of the current system. It is the system's best-implemented perceptual property.

**Signal:** The decay curve *is* the inertia model. The research question is the *shape* and *rate*:

- Pure exponential (current) gives smooth, ever-slowing fade.
- Inertia likely wants a **plateau-then-decay** shape: momentum should hold near its level briefly (the "they've still got it" window) and only then decay. See dynamic/state-specific decay in [03-decay-research.md](./03-decay-research.md).

**Key insight:** Inertia and persistence interact. A short flurry should have short inertia; a sustained run should coast longer. So inertia (decay rate) should be *modulated by persistence* (dimension 5), not fixed at 49s.

---

## Summary: capture matrix

| # | Dimension | Current capture | 2.0 signal (score+time only) |
|---|---|---|---|
| 1 | Volume | Strong | `sum(myDelta, W)/bigPlay` |
| 2 | Velocity | Partial | `sum(myDelta, W)/W / expectedRate` |
| 3 | Acceleration | None | `velocity(recent) - velocity(prior)` |
| 4 | Suppression | Indirect | `mySum / (mySum+oppSum)` |
| 5 | Persistence | Weak | `now - runStartTs` |
| 6 | Recovery | Partial | slow-decay `ember` floor |
| 7 | Reversal | Implicit | `d(myMom-oppMom)/dt` |
| 8 | Inertia | Strong | the decay curve, modulated by persistence |

---

## Recommendation for FlySense 2.0

Do **not** replace the scalar with eight numbers on screen — that would violate the simplicity criterion. Instead:

- Keep **one displayed momentum scalar** per side as the backbone (volume + inertia, as today).
- Use **acceleration (3)** and **recovery (6)** to make the scalar *respond faster and re-ignite faster* — improving perceived accuracy without adding UI.
- Use **suppression (4)** to drive **dominance**, feeding a stronger Cold for the opponent.
- Use **persistence (5)** to **modulate decay** (stability without sluggishness).
- Use **reversal (7)** to trigger **comeback intensity** and brief swing emphasis.

In other words: the eight dimensions are mostly *internal modulators* of a single, still-simple displayed number. This is what makes "increase information density without increasing learning burden" achievable. The concrete formula is assembled in [13-flysense-2.0-spec.md](./13-flysense-2.0-spec.md).
