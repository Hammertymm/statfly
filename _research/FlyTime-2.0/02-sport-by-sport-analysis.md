# Phase 2 — Sport-by-Sport Analysis

**Premise:** FlyTime must **not** behave the same across sports. Each sport has its own scoring quantum, clock model, lead-decay physics and comeback distribution. This document models each sport independently and derives, for each: the **earliest viable prediction point**, **optimal margin band**, **confidence ceiling**, and **2.0 trigger logic**.

> All percentages are modelled lead-survival / close-finish estimates anchored to the historical close-rate tiers in [StatFly_FlyTime_Threshold_Recommendations.md §7](../../scorefly/StatFly_FlyTime_Threshold_Recommendations.md) and each sport's scoring structure. They are design hypotheses with a test attached (see [Phase 12](./12-validation-framework.md)), not measured production output.

---

## The unifying concept: lead safety as a curve

Replace "margin ≤ X" with a continuous function:

```
LeadSafety(margin, timeLeft, volatility) = P(leader still wins | current state)
CloseFinishProb = f(1 − LeadSafety, timeLeft, momentum)
```

The right variable is not raw margin but **margin measured in "scores"** — how many scoring events the trailing side needs — divided by **how many scoring opportunities remain**. A 6-point NRL deficit = one converted try = very alive. A 6-point AFL deficit = one goal = trivial in a sport that scores ~25 times. Same number, opposite meaning. This "possessions/scores to tie vs scores remaining" ratio is the cross-sport backbone; every sport below is an instance of it.

---

## AFL (Australian Football)

- **Scoring quantum:** goal = 6, behind = 1. High event count (~25–30 scoring shots/team). Margins are large and continuous.
- **Lead survival:** AFL has the **lowest historical close rate of all feeds (~27.5%)** — leads are *sticky*. A 4-goal (24-pt) lead late is usually safe.
- **Typical late swings:** runs of 3–4 goals happen but take time; the clock is long (~20 min quarters + time-on).
- **Comeback probability:** low relative to scoring volume; "six-goal final quarter" comebacks are memorable precisely because they are rare.
- **Margin significance by time:** 24 pts with a full Q4 ≈ live-ish; 24 pts with 8:00 left ≈ mostly safe; ≤ 12 pts at any Q4 point ≈ genuinely open.

**Current rule:** Q4 with ≥ 20:00 elapsed AND margin ≤ 12, blowout buffer 24.
**Weakness:** waits until ~half the final quarter is gone; misses a tight three-quarter-time game that stays tight.
**2.0:**
- Earliest viable: **start of Q4** (sometimes 3QT) when margin ≤ ~18 and closing.
- Margin band: tense ≤ 12; watch 13–18; safe > 24.
- Confidence ceiling: **moderate** — AFL's stickiness means high-confidence "will be close" is only honest late.
- Trigger: `FlyIndex = g(margin/6 "goals to tie", minutesLeft, momentumSwing)`. Escalate to Confirmed only ≤ ~10:00 with margin ≤ 12.

---

## NRL (Rugby League)

- **Scoring quantum:** try 4 (+2 conversion) ≈ 6; penalty/field goal 1–2. A converted try erases 6.
- **Try conversion impact:** a single set can flip a 6-point game; "one score" games (≤ 6, sometimes ≤ 8) are the live band.
- **Possession value:** very high — the team with the ball in the last set controls the outcome; field position matters as much as margin.
- **Lead security:** ≤ 6 is one play; 7–12 is two plays (often two sets); > 12 needs a collapse.
- **Late patterns:** golden-point OT is common after draws; the last 10 minutes are dense.

**Current rule:** ≥ 35:00 elapsed in a half OR OT, margin ≤ 12, buffer 24.
**Weakness:** fires only in the back third of a half; a tight game at 25:00 of the 2nd half shows nothing.
**2.0:**
- Earliest viable: **~20:00 into the 2nd half** with margin ≤ 8.
- Margin band: tense ≤ 6 (one converted try); watch 7–12; safe > 18.
- Confidence ceiling: **high** in the band — NRL one-score games genuinely go to the wire.
- Trigger: weight **possession** if available; a trailing-by-6 side with the ball ≤ 5:00 is near-certain FlyTime.

---

## NBA / WNBA / NBL (Basketball)

- **Scoring quantum:** 2–3 per possession, ~100 possessions/game. Fast, high-variance, frequent lead changes.
- **Possession-based:** the standard model is "points / (possessions remaining × points-per-poss)". The classic heuristic: a lead is roughly safe if `points > 3×√(seconds_left) + ...` — i.e. lead safety scales with the **square root of time remaining**.
- **Foul game:** the last 2:00 distort time — fouls stop the clock, so an 8-point gap at 1:00 is more alive than wall-clock suggests. This is a *known structural reason the current 5:00/margin-8 gate is too coarse late.*
- **Clutch scoring rate:** elevated; 3-pointers create instant 3-possession swings.
- **OT frequency:** ~6–7% of NBA games.

**Current rule:** Q4/OT, ≤ 5:00, margin ≤ 8.
**Weakness:** an 8-point game at 7:00 (very unsafe by the √time rule) is invisible; foul-game inflation of late comebacks unmodelled.
**2.0:**
- Earliest viable: **~8:00 left in Q4** when `margin ≤ 3×√(min_left×60)/... ` — i.e. an adaptive band, not flat 8.
- Margin band: time-scaled. ≈ ≤ 6 at 2:00, ≤ 9 at 5:00, ≤ 12 at 8:00.
- Confidence ceiling: **high** — basketball lead-safety curves are the best-studied in sport (ESPN/Inpredictable), so calibration can be tight.
- Trigger: adopt a √time lead-safety curve; add **foul-game adjustment** in the final 2:00.

---

## NFL / NCAAF / CFL (Gridiron)

- **Scoring quantum:** TD 7, FG 3. "One-score game" (≤ 8) is the canonical live band; "two-score" (9–16) is recoverable with time.
- **Possession value:** dominant — *who has the ball and how many possessions remain* is more predictive than margin. Down 8 with the ball and 2:00 + a timeout ≈ very live; down 8 without the ball and 0:50 ≈ nearly dead.
- **Clock management / timeouts:** the two-minute warning and timeout count change the number of remaining possessions dramatically — the true "time remaining" is *possessions remaining*, not seconds.
- **FG threshold:** trailing by ≤ 3 means a single FG drive ties; a huge psychological/strategic band.

**Current rule:** Q4, ≤ 5:00, margin ≤ 8.
**Weakness:** ignores possession and timeouts — the two variables that actually decide NFL endgames. An 8-point game can be functionally over at 1:30 if the leader has the ball and the trailer has no timeouts.
**2.0:**
- Earliest viable: **~6:00–8:00 in Q4** for one-score games; two-score games only with possession + timeouts favourable.
- Margin band: ≤ 8 core; extend to ≤ 16 when ≥ ~4:00 and possession/timeouts favour the trailer.
- Confidence ceiling: **high** if possession+timeout data is available; **moderate** on margin alone.
- Trigger: model **possessions remaining**, not clock seconds.

---

## NHL (Hockey)

- **Scoring quantum:** 1 goal, low frequency (~3/team/game). Every goal is huge.
- **Empty-net dynamics:** trailing by 1 (or 2) late → goalie pulled → 6v5 → elevated scoring *both ways*. A 1-goal game in the last 3:00 is maximally volatile; a 2-goal game can become a 1-goal game then tie via empty-netters or concede an ENG.
- **One-goal games:** the dominant FlyTime case. ~ a quarter of games are one-goal.
- **Lead security:** 1 goal is never safe late; 2 goals are *mostly* safe until the goalie pull window (~last 2–3 min), then partially unsafe; 3 goals safe.

**Current rule:** P3+, ≤ 5:00, margin ≤ 1.
**Weakness:** ignores the 2-goal → goalie-pull volatility, the single most exciting NHL endgame. A 2-goal game at 2:00 with a pulled goalie is *peak* FlyTime and the engine shows nothing.
**2.0:**
- Earliest viable: 1-goal games from **~middle of P3**; 2-goal games inside the **goalie-pull window (~last 3:00)**.
- Margin band: ≤ 1 always live late; ≤ 2 live inside pull window.
- Confidence ceiling: **high** for 1-goal; **moderate** for 2-goal (depends on pull).
- Trigger: explicit **empty-net / goalie-pull** state if detectable (score state + time); otherwise treat margin-2, last-3:00 as elevated.

---

## MLB (Baseball)

- **Structure:** innings, not clock. "Time remaining" = **outs remaining**. Run expectancy by base/out state is the canonical model.
- **Run expectancy / comeback:** trailing by ≤ 2 with the tying run coming to the plate is the live band; a save situation (≤ 3, bases empty, 9th) is structurally tense.
- **Comeback likelihood:** falls sharply with outs; bottom-9 down 2 with runners on is far more alive than top-9 down 2.

**Current rule:** inning ≥ 8, margin ≤ 2.
**Weakness:** ignores base/out state and which side is batting; a 3-run save with the bases loaded is more tense than a sleepy 2-run game.
**2.0:**
- Earliest viable: **8th inning** for ≤ 2; 9th for ≤ 3 with traffic.
- Margin band: ≤ 2 core; ≤ 3 in the 9th with the tying run on base/deck.
- "Time" variable: **outs remaining + base state**, not innings alone.
- Confidence ceiling: **moderate** — baseball variance is high; honest high-confidence only with base/out context.

---

## Soccer

- **Scoring quantum:** rare (~2.7 goals/game total). A 1-goal game is the canonical tense state; level games in the 80th+ are FlyTime.
- **Expected late scoring:** low base rate but spikes in stoppage time; xG and "shots in the box" would massively improve signal if available.
- **One-goal significance:** a 1-goal lead at 80' is recoverable; at 90+4' it is nearly safe unless a set-piece is live.
- **Two goals:** generally safe but not impossible (rare 2-goal stoppage comebacks).

**Current rule:** minute ≥ 80, margin ≤ 1.
**Weakness:** discards stoppage time (no escalation as 90→90+5), ignores chance quality, treats a frantic 2-1 with late chances as non-FlyTime.
**2.0:**
- Earliest viable: **~75'** for level/1-goal games trending tense (momentum + chances).
- Margin band: 0 or 1 core; consider 2 only with strong late momentum + stoppage time.
- "Time" variable: include **stoppage time** properly (90+X escalates confidence).
- Confidence ceiling: **moderate** on score alone; **high** with event quality (future data).

---

## Cricket (format-specific)

Cricket is three different sports; one rule cannot serve all.

- **T20:** ~10+ runs/over is "on fire"; chases are tense when **required run rate ≈ current capacity** and wickets in hand are low. A chase needing 30 off 18 with 4 wickets is peak FlyTime.
- **ODI:** longer; tension builds when RRR climbs above ~8–9 with wickets falling; the last ~10 overs are the FlyTime window.
- **Test:** FlyTime is rare and situational (last session, result possible for either side, or a tense follow-on/last-wicket stand). Largely out of scope for a margin model.
- **Run-rate pressure & wickets:** the two real variables — required rate vs achievable rate, modulated by wickets in hand.

**Current rule:** `isCricketFlyTime` — runs req ≤ 20 AND overs left ≤ 2 (chase only).
**Weakness:** only the very last 2 overs of a chase; ignores RRR pressure earlier, first-innings drama, and wickets.
**2.0:**
- Earliest viable: **final ~5 overs (T20) / ~10 overs (ODI)** when RRR pressure is high and wickets are a constraint.
- Variables: **required run rate vs current run rate**, **wickets in hand**, **balls remaining**.
- Confidence ceiling: **high** in the last few overs of a tight chase (deterministic maths), **lower** earlier.
- Reuse FlySense's existing **run-rate momentum engine** (already format-aware: T20 10+/over, ODI 6+/over) as the FlyTime input.

---

## Cross-sport summary table

| Sport | "Time" variable | Tense band (one-score) | Earliest honest trigger | Confidence ceiling | Biggest current miss |
|-------|-----------------|------------------------|--------------------------|--------------------|----------------------|
| AFL | minutes in Q4 (+time-on) | ≤ 12 (2 goals) | start of Q4, ≤ 18 closing | Moderate | tight 3QT games before 20:00 elapsed |
| NRL | minutes in 2nd half | ≤ 6 (one converted try) | ~20:00 H2 | High | tight games before 35:00 |
| NBA/WNBA/NBL | √(seconds left) | time-scaled (≤6→≤12) | ~8:00 Q4 | High | unsafe leads at 6–8 min; foul game |
| NFL/NCAAF/CFL | possessions remaining | ≤ 8 (one score) | ~6–8:00 Q4 | High (w/ possession) | possession + timeouts ignored |
| NHL | minutes in P3 | ≤ 1 (≤2 in pull window) | mid-P3 | High (1-goal) | 2-goal goalie-pull drama |
| MLB | outs + base state | ≤ 2 (≤3 w/ traffic) | 8th inning | Moderate | base/out state ignored |
| Soccer | minute incl. stoppage | 0–1 goal | ~75' trending | Moderate (High w/ xG) | stoppage time + chance quality |
| Cricket | balls remaining | RRR pressure + wickets | last 5 overs (T20) | High late | first innings + RRR before last 2 overs |

**The through-line:** every "weakness" column is the same failure — the current gate uses **raw margin + a late clock cliff**, ignoring the sport-specific variable that actually governs lead safety (possessions, outs, goalie pulls, run rate, stoppage time, √time). FlyTime 2.0's per-sport modules each replace "margin ≤ X late" with the right physics. Proceed to [Phase 3](./03-historical-close-finish-research.md) to measure these curves against real history.
