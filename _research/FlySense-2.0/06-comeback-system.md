# 06 — Comeback System Audit (Part 6)

The comeback state (purple) is the most advanced piece of FlySense logic today — it is the only state that uses **score history** (worst deficit) rather than just recent momentum. This document audits it and proposes **comeback intensity**.

---

## Current logic

```2357:2365:index.html
function resolveSide(myMom, oppMom, myDeficit, myMaxDef, tune) {
  // Comeback (purple): was down by a real margin, has clawed back at least half of it,
  // is now roughly level (not yet a runaway lead), and still has positive momentum.
  if (myMaxDef >= tune.cbMin &&
      (myMaxDef - myDeficit) >= myMaxDef * 0.5 &&
      myDeficit <= tune.cbMin && myDeficit >= -tune.cbMin &&
      myMom >= 20) {
    return 'comeback';
  }
```

Inputs:
- `myMaxDef` — largest deficit this side has faced (tracked monotonically, L2345-2346).
- `myDeficit` — current deficit (`opp - me`; negative means leading).
- `myMom` — current momentum.
- `tune.cbMin` — per-sport deficit threshold (`FLY_TUNING`, L1727).

### The four current requirements

| Requirement | Condition | Meaning |
|---|---|---|
| **Deficit** | `myMaxDef >= cbMin` | Was down by a *real* margin (not noise). |
| **Recovery** | `myMaxDef - myDeficit >= 0.5 * myMaxDef` | Has erased at least half the worst deficit. |
| **Timing/position** | `-cbMin <= myDeficit <= cbMin` | Now roughly level (not a runaway lead). |
| **Live momentum** | `myMom >= 20` | The comeback is *active*, not stalled. |

### `cbMin` by sport

| Sport | `cbMin` |
|---|---|
| soccer | 2 |
| hockey | 2 |
| baseball | 3 |
| basketball | 10 |
| football | 11 |
| rugby-league / rugby | 12 |
| AFL | 18 |

Scaled to each sport's scoring units — a 2-goal soccer comeback is huge; a 10-point NBA one is meaningful.

### State priority

Comeback **outranks every heat state** (`comeback > onfire > onrun > warming > cold`, L2356). A team completing a comeback shows purple even if its momentum would otherwise read "on fire" — correct, because the *story* (the recovery) is what the user should see.

---

## Audit findings

**Strengths**
- Uses real history (worst deficit), making it genuinely different from momentum colour.
- Sport-scaled via `cbMin`.
- The "roughly level, not runaway" clause correctly ends the comeback once the team takes a commanding lead (the story becomes "dominating", not "coming back").
- Requires live momentum, so a team that clawed level then went quiet does not falsely stay purple.

**Weaknesses**
1. **Binary.** A team back from `cbMin` exactly looks identical to a team back from a 40-point abyss. The most thrilling comebacks in sport are precisely the *largest* ones, and FlySense cannot tell them apart.
2. **No timing dimension.** A comeback over two minutes vs one grinding over a half are visually identical. Speed is part of how dramatic a comeback feels ([02](./02-momentum-science.md) §7 reversal).
3. **Recovery is a flat 50%.** A team that has erased 50% of a deficit (still behind) and one that has fully drawn level both qualify equally; arguably "drawn level / taken the lead after a big deficit" deserves more emphasis than "halfway back".
4. **`myMaxDef` never resets.** Late-game, a long-ago early deficit can still satisfy the deficit clause even if the game has since been a blowout-then-normalise; generally fine, but worth noting for very long matches.
5. **Exit is implicit.** Comeback ends when any single clause fails (e.g. momentum dips under 20 for one poll), which can flicker comeback off/on near the boundary — same hysteresis concern as [04](./04-threshold-research.md).

---

## Proposal: comeback intensity

Make comeback a **scaled** state (like the heat ramp), not a binary. Compute a `comebackMagnitude` and map it to purple intensity + (at the extreme) motion.

### Magnitude inputs

```
deficitScale  = myMaxDef / cbMin                       // how big was the hole (>=1 to qualify)
recoveryFrac  = (myMaxDef - myDeficit) / myMaxDef      // 0.5..1.0+, how much erased
speedFactor   = recoveredPoints / recoverySeconds      // how fast (reversal rate)
positionBonus = (myDeficit <= 0) ? bonus : 0           // drawn level / taken the lead
```

```
comebackMagnitude = f(deficitScale, recoveryFrac, speedFactor, positionBonus)
```

### Proposed intensity tiers (labels for semantics/legend; colour is continuous)

| Tier | Rough trigger | Visual |
|---|---|---|
| **Minor comeback** | deficit ~1-1.5x `cbMin`, clawed to level | soft purple |
| **Comeback** | deficit ~1.5-2.5x `cbMin` | full purple `#bf5af2` |
| **Major comeback** | deficit ~2.5-4x `cbMin`, now level or ahead | vivid purple + subtle glow |
| **Historic comeback** | deficit >4x `cbMin`, fully erased + leading, fast | brightest purple + brief motion/pulse |

As with heat ([05](./05-gradient-system-design.md)), the colour is a **continuous purple intensity ramp** driven by `comebackMagnitude`; the tier names exist only for the legend, accessibility text and to gate the extreme motion effect.

### Stability

Apply the same **hysteresis** as the heat bands: enter comeback when all clauses clear by a small margin, exit only when they fail by a margin, so a one-poll momentum dip under 20 does not drop the purple. Let comeback decay its purple briefly on exit rather than snapping (consistent with [03](./03-decay-research.md) state-specific decay — comeback holds through the swing then releases).

---

## "Should comeback intensity exist?" — conclusion

**Yes.** It is the single highest-drama event FlySense can show, and intensity is exactly what distinguishes a routine level-up from a historic, talked-about-for-years recovery. It also reuses the same intensity machinery as the heat ramp and cold severity, so it adds *expressiveness without adding a new visual concept* — directly serving the information-density goal ([09](./09-information-density.md)).

Inputs required are all already available or trivially derivable: `myMaxDef` and `myDeficit` exist (L2345-2346); recovery speed needs only a timestamp on when the deficit peaked (one extra field in `flyState`).

---

## Recommendations

1. Replace binary comeback with a **`comebackMagnitude`** scaled by deficit size, recovery fraction, speed and position.
2. Map magnitude to a **continuous purple intensity** ramp; reserve brief motion for **historic** only.
3. Add **hysteresis** + brief release decay so comeback does not flicker.
4. Record the **timestamp of peak deficit** in `flyState` to enable the speed factor.
5. Keep comeback's **top priority** over heat states.
