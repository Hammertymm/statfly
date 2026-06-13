# 12 — User Perception Testing (Part 12)

**Status: designed, not executed.** No user panel is run in this deliverable. This is the protocol to run once 2-3 candidate configs survive historical validation ([11](./11-historical-validation-framework.md)).

The premise from the brief:

> The ultimate test is not mathematics. The ultimate test is: does FlySense *feel* correct?

Everything in the quantitative work is in service of this. A config can win every metric in [11](./11-historical-validation-framework.md) and still feel wrong; this protocol is the final arbiter.

---

## What we are testing

Four user-facing outcomes, mapped to the success criteria:

| Outcome | Definition | Success criterion served |
|---|---|---|
| **Recognition speed** | How fast a user reads the state from a glance | "instantly understandable", ~1s |
| **User confidence** | How sure the user is they read it right | "require no explanation" |
| **User understanding** | Whether their read matches reality | "improve momentum accuracy" |
| **Visual clarity** | Whether the card feels clean, not cluttered | "preserve simplicity / premium feel" |

---

## Test 1 — One-second recognition (the headline test)

Directly tests the final principle ("look for one second and instinctively know").

- **Stimulus:** a single match card (from a replayed historical moment via [11](./11-historical-validation-framework.md)) shown for **1000 ms**, then hidden.
- **Task:** "Which team had momentum, and how strongly?" (pick a side + intensity on a 5-point scale, or "even/neutral").
- **Measure:** accuracy vs the objective run label; response time.
- **Compare:** Current vs each candidate config on the *same* moments.
- **Pass:** candidate ≥ current on accuracy **and** not slower; gradient configs are expected to win on *intensity* accuracy specifically (the cliff problem, [04](./04-threshold-research.md)).

---

## Test 2 — Live recognition / confidence (Fly Mode)

- **Stimulus:** a 30-60s replayed live sequence in Fly Mode (colours evolving in real time).
- **Task:** narrate or tap when "a team is taking over" / "the momentum just swung" / "a team has gone cold".
- **Measure:** latency from the objective event to the user's response; self-rated confidence (1-5) afterward.
- **Tests:** responsiveness ([03](./03-decay-research.md)), reversal/swing emphasis ([02](./02-momentum-science.md) §7), cold recognition ([07](./07-cold-state.md)).

---

## Test 3 — Blind state identification (legend-free)

- **Stimulus:** static cards across the full momentum range, **no legend visible**.
- **Task:** describe what each colour means in the user's own words.
- **Measure:** do users spontaneously map colours to the intended meaning without being taught? ("require no explanation").
- **Watch for:** confusion pairs flagged in [05](./05-gradient-system-design.md) accessibility (orange vs red, purple vs blue).

---

## Test 4 — Clutter / premium perception (extremes)

- **Stimulus:** a feed list containing a few Extreme On Fire / Extreme Cold cards among normal ones ([08](./08-visual-intensity.md)).
- **Task:** preference + "does anything feel gimmicky / hard to read?"
- **Measure:** A/B preference (effects on vs off), readability rating of the score digit on effect cards.
- **Pass:** effects must *increase* perceived drama **without** decreasing readability or premium ratings; if an effect fails this, cut it (the constraint from [08](./08-visual-intensity.md)).

---

## Test 5 — Accessibility panel

- **Participants:** include colour-vision-deficient users (protan/deutan/tritan) and test in **outdoor/high-glare** and **low-brightness** conditions ([05](./05-gradient-system-design.md)).
- **Task:** intensity ordering ("which card is hotter?") relying on the luminance-monotonic ramp.
- **Pass:** CVD users can order intensity correctly using luminance even when hue is ambiguous; all states distinguishable at lowest Fly Mode brightness and in glare.

---

## Method notes

- **Within-subjects, counterbalanced:** each participant sees Current and candidates on the same moments in randomised order to control for moment difficulty.
- **Ground truth:** the objective run/drought/comeback labels from [11](./11-historical-validation-framework.md), so "understanding" is scored against the same standard the quantitative engine used.
- **Sample:** enough participants for a stable preference signal across sports; recruit some sport-savvy and some casual users (FlySense must work for both).
- **Pilot small:** a lightweight in-app or clickable-prototype version using replayed moments is sufficient; no production changes needed.

---

## Decision rule

A candidate config replaces Current only if it:
1. Wins or ties **Test 1** (1s recognition accuracy + speed), **and**
2. Improves intensity/responsiveness on **Tests 2-3**, **and**
3. Does **not** regress clarity/premium (**Test 4**) or accessibility (**Test 5**).

This enforces the core promise: richer information, **no** added burden, no loss of clarity.

---

## Recommendations

1. Run perception testing **only on configs that passed [11](./11-historical-validation-framework.md)** (cheap filter first).
2. Make **Test 1 (one-second recognition)** the primary gate — it is the literal product promise.
3. Score "understanding" against the **same objective labels** used quantitatively.
4. Require **no regression** in clarity/premium/accessibility before adopting any change.
5. Use replayed real moments (no production changes) so testing can run before any code ships.
