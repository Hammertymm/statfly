# 10 — Sport-Specific Research (Part 10)

Does momentum behave differently across sports? **Yes** — scoring rhythm, the size of a "big play", how long a score stays relevant, and how fast momentum can swing all differ. This document collects per-sport behaviour and proposes a unified parameter table.

Today the only per-sport knobs are `bigPlay` and `cbMin` (`FLY_TUNING`, L1727 of [index.html](../../index.html)); decay (49s) and thresholds (20/42/68) are global. FlySense 2.0 adds per-sport **half-life** and **expected scoring rate / drought norm** (see [03](./03-decay-research.md), [07](./07-cold-state.md)).

---

## Dimensions that vary by sport

| Dimension | Meaning | Why it varies |
|---|---|---|
| **Scoring rhythm** | Frequency + size of scores | A soccer goal is rare and huge; an NBA basket is frequent and small. |
| **Decay rate** | How long a score stays "relevant" | Rare-event sports keep momentum longer. |
| **Velocity expectation** | Normal scoring rate | Sets what "fast" means for acceleration/velocity ([02](./02-momentum-science.md)). |
| **Persistence** | How long runs naturally last | Drive/set/inning structure vs continuous play. |

---

## Per-sport profiles

### AFL (`australian-football`)
- **Rhythm:** frequent (goals 6pts, behinds 1pt); flowing, high totals. `bigPlay: 9`, `cbMin: 18`.
- **Momentum:** builds over multi-minute surges; quarters create natural runs.
- **Decay:** medium (~55s). **Drought:** minutes are normal.

### NRL / Rugby League (`rugby-league`) and Rugby (`rugby`)
- **Rhythm:** spaced, large (try+conversion = 6). `bigPlay: 6`, `cbMin: 12`.
- **Momentum:** set-by-set pressure; a try shifts feel strongly and lingers.
- **Decay:** medium (~55s). **Drought:** several minutes normal.

### NBA / basketball (`basketball`)
- **Rhythm:** constant, small (2-3 pt). `bigPlay: 6`, `cbMin: 10`.
- **Momentum:** real "runs" (8-0, 12-2) but turn over fast; the most volatile.
- **Decay:** short (~40s) — a run that stops feels over quickly. **Drought:** a 90s scoreless stretch is already notable.

### NFL / Football (`football`)
- **Rhythm:** infrequent but large (7, 3). `bigPlay: 7`, `cbMin: 11`.
- **Momentum:** drive-paced; scores are big events separated by minutes.
- **Decay:** medium (~50s, ≈ current). **Drought:** long gaps are normal (a whole drive).

### NHL / Hockey (`hockey`)
- **Rhythm:** scarce (goals of 1). `bigPlay: 2`, `cbMin: 2`.
- **Momentum:** a goal is momentum-defining; pressure exists between goals (shots) but FlySense only sees goals.
- **Decay:** long (~70s) — goals are rare so each stays relevant. **Drought:** many minutes normal.

### MLB / Baseball (`baseball`)
- **Rhythm:** clustered by inning (runs of 1+). `bigPlay: 3`, `cbMin: 3`.
- **Momentum:** an inning rally is the unit; quiet between.
- **Decay:** long (~75s) — runs stay relevant across at-bats. **Drought:** innings can pass scoreless normally.

### Soccer (`soccer`)
- **Rhythm:** rarest scoring (goals of 1). `bigPlay: 1`, `cbMin: 2`.
- **Momentum:** a single goal reshapes the match for a long time; "pressure" without goals is real but invisible to a score-only feed.
- **Decay:** longest (~90s) — a goal must linger. **Drought:** the default state is scoreless; absolute-drought cold must be very lenient here ([07](./07-cold-state.md)).

---

## Proposed unified parameter table

`bigPlay` and `cbMin` are the **current** shipped values (kept). `baseHalflife` and `droughtNorm` are **new proposals** for FlySense 2.0 (validate before locking — [11](./11-historical-validation-framework.md), [03](./03-decay-research.md)).

| Sport | `sportKey` | `bigPlay` | `cbMin` | `baseHalflife` (new) | `droughtNorm` (new) |
|---|---|---|---|---|---|
| Basketball (NBA/WNBA/NBL/NCAA) | `basketball` | 6 | 10 | 40s | ~90s |
| Football (NFL/NCAAF/CFL) | `football` | 7 | 11 | 50s | ~5 min |
| Hockey (NHL) | `hockey` | 2 | 2 | 70s | ~8 min |
| Soccer (all leagues) | `soccer` | 1 | 2 | 90s | ~15 min |
| Baseball (MLB) | `baseball` | 3 | 3 | 75s | ~2 innings |
| AFL | `australian-football` | 9 | 18 | 55s | ~5 min |
| Rugby League (NRL) | `rugby-league` | 6 | 12 | 55s | ~6 min |
| Rugby (URC/Top14) | `rugby` | 6 | 12 | 55s | ~6 min |

`droughtNorm` = a scoreless gap that is *typical* for the sport; the absolute-drought cold trigger ([07](./07-cold-state.md)) should fire only well beyond this. Values are starting hypotheses.

> Note: cricket has bespoke FlyTime handling (`isCricketFlyTime`, L1800) but is **not** in `FLY_TUNING`, so it currently falls back to the basketball defaults for momentum. If cricket momentum matters, it needs its own row (run-rate-based) — flagged as an open item.

---

## Design implication

All sport differences in FlySense 2.0 should flow through **this one table** (`FLY_TUNING` extended with `baseHalflife` and `droughtNorm`). The momentum scalar then stays sport-neutral on the 0-100 scale ([04](./04-threshold-research.md)), the gradient mapping stays identical across sports, and only the *inputs* (what counts as a big play, how fast it cools, what counts as a drought) are sport-aware. This keeps the visual language universal while the underlying feel is sport-correct.

---

## Recommendations

1. Extend `FLY_TUNING` with **`baseHalflife`** and **`droughtNorm`** per sport (table above).
2. Keep `bigPlay`/`cbMin` as shipped; they already encode scoring-unit differences well.
3. Keep the **0-100 scale and gradient sport-neutral**; route all sport variation through the tuning table.
4. Add a **cricket** row (run-rate based) or explicitly document the basketball fallback.
5. Treat all new per-sport numbers as **hypotheses** pending historical validation.
