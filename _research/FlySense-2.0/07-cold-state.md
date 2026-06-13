# 07 — Cold State Research (Part 7)

Cold (blue) is the only "negative" state in FlySense — it tells the user a team has been shut down. Today it is **relative, binary, and opponent-dependent**. This document evaluates its accuracy and proposes **severity levels** including Extreme Cold.

---

## Current logic

```2368:2370:index.html
  // Gone cold (blue): I've stalled while my opponent is heating up.
  if (myMom < 12 && oppMom >= 42) return 'cold';
  return '';
```

Cold is true iff **both**:
- `myMom < 12` — I have effectively stalled.
- `oppMom >= 42` — my opponent is at least "on a run".

It sits **below** all heat states and comeback in priority (only neutral is lower).

---

## Audit findings

**What it gets right**
- Cold-as-contrast is perceptually sound: a team feels "cold" mainly *because the other team is hot*. Requiring `oppMom >= 42` captures that.
- It cannot fire spuriously during a lull where neither team scores (opponent must be hot), avoiding "everyone is blue" in slow periods.

**Accuracy gaps**
1. **Purely relative.** Cold requires a hot opponent. A team in a genuine **scoring drought** while the opponent merely ticks over (opp momentum 30, not 42) shows **neutral**, not cold — even though the team is objectively freezing. Human perception of "cold" includes *absolute* drought, not only relative.
2. **Binary, no severity.** A team at momentum 11 with a hot opponent looks identical to a team at 0 that has not scored in 15 minutes while being buried. The depth of cold is invisible.
3. **No duration memory.** Cold does not know *how long* the team has been cold. A 20-second quiet spell and a 6-minute shutout render the same.
4. **No "collapse" recognition.** A team that was on fire and then fell off a cliff (a *momentum collapse*) is perceptually very cold, but the engine only sees the current low number, not the fall.

---

## Proposal: cold as a severity ramp

Mirror the heat ramp ([05](./05-gradient-system-design.md)): compute a **coldSeverity** (0-1) and map it to a continuous blue ramp (pale blue -> deep frozen blue), with Extreme Cold at the top.

### Severity inputs (all derivable from score+time)

| Input | Signal | Why |
|---|---|---|
| **Own stall depth** | `1 - myMom/12` (how far below the stall floor) | Absolute coldness. |
| **Opponent dominance** | `oppMom` and **suppression** ([02](./02-momentum-science.md) §4) | Relative coldness / being buried. |
| **Drought duration** | `now - lastMyScoreTs` vs sport norm | Sustained shutout. |
| **Collapse** | recent **negative acceleration** from a prior high ([02](./02-momentum-science.md) §3) | The fall from hot to cold. |

```
coldSeverity = combine(stallDepth, oppDominance, droughtNorm, collapse)
```

### Make cold partly absolute

Allow cold to trigger on **either**:
- the current relative rule (`myMom < 12 && oppMom >= 42`), **or**
- a strong **absolute drought** (no scoring for >> sport-normal gap while behind), even if the opponent is only moderately active.

This fixes gap #1 without making cold noisy, because the absolute trigger requires a genuinely long drought scaled per sport ([10](./10-sport-specific.md)).

---

## Cold severity levels

| Level | Rough trigger | Visual |
|---|---|---|
| **Cooling** | mild stall, opponent warm | faint blue tint |
| **Cold** | current rule (`myMom<12`, `oppMom>=42`) | blue `#409cff` |
| **Deep cold** | long drought + dominant opponent | saturated deep blue |
| **Extreme cold** | momentum collapse + sustained drought + opponent dominance | darkest blue + frost treatment ([08](./08-visual-intensity.md)) |

### Extreme Cold (momentum 0-10) — the three signals

The brief asks to investigate three things; here is how each feeds Extreme Cold:

1. **Momentum collapse** — a large negative acceleration from a recent high (was hot, now nothing). The *fall*, not just the floor.
2. **Scoring drought duration** — time since this side last scored, normalised to the sport (a 4-minute soccer drought is normal; a 4-minute NBA drought is dire).
3. **Opposition dominance** — opponent momentum × suppression: the opponent is not just scoring but scoring *unanswered*.

Extreme Cold requires **all three** to be elevated, so it is rare and meaningful — the visual equivalent of "this team has completely frozen and is being run over". This is the natural counterpart to Extreme On Fire on the opposing side, and the two will frequently co-occur (one team's fire is the other's frost).

---

## Relationship to the opponent's heat

Because cold is the shadow of the opponent's run, FlySense 2.0 can derive much of cold severity directly from the **opponent's heat + suppression**, keeping the two sides consistent: if side A is Extreme On Fire with high suppression, side B should read Extreme Cold almost automatically. This symmetry keeps the card coherent (you will not see one side blazing while the other looks merely neutral).

---

## Stability

Apply hysteresis and gentle decay to cold just like heat ([03](./03-decay-research.md), [04](./04-threshold-research.md)) so a single score by the cold team does not instantly clear deep blue — recovery from cold should feel gradual, matching perception (one bucket does not mean a team is "back").

---

## Recommendations

1. Convert cold from binary to a **continuous severity ramp** (pale -> frozen blue).
2. Add an **absolute drought trigger** alongside the current relative rule.
3. Define **Extreme Cold** as the conjunction of **collapse + drought + opponent dominance** (momentum 0-10).
4. Derive cold severity partly from the **opponent's heat + suppression** for a coherent two-sided card.
5. Add **hysteresis + gradual recovery** so cold clears smoothly.
