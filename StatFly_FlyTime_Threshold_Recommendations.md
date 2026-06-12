# StatFly / ScoreFly — FlyTime Threshold Recommendations

**Document purpose:** Analyse ChatGPT’s threshold-tuning advice (ledger review + launch-readiness framing), compare it to ScoreFly’s offline research calibration, and produce actionable updated thresholds.

**Date:** 12 Jun 2026  
**Status:** Recommendations only — not yet applied to `index.html`  
**Sources:** `FLY_V1_REGISTRY` in `index.html`, `*-flytime-v1.json` (45 leagues), `scripts/calibrate_flytime.py`, live ledger export (Jun 2026), ChatGPT ledger analysis

---

## 1. Executive summary

ChatGPT’s core insight is correct: **yellow-fly rate per league/round should eventually resemble red-fly rate** for that league/round. A yellow fly is a prediction; a red fly is ground truth (the match actually entered FlyTime).

However, **today’s ledger cannot validate that ratio** — every exported entry is `p:1, a:0, fin:0` (predicted, never achieved, not finished). Until live FlyTime detection is confirmed (green fly in play → red fly on Results), threshold tuning from the ledger alone is blind.

What we *can* do now:

1. Apply **five research-backed threshold changes** where offline calibration disagrees with the app.
2. Keep the other **40 leagues unchanged** — they already match the “~2 yellow flies per round-chunk” target baked into `calibrate_flytime.py`.
3. Run a **live validation sprint** (one close finish per major sport with the app open) before any wider retune.

---

## 2. What ChatGPT recommended (interpreted)

From the ChatGPT ledger review and launch-audit framing:

| ChatGPT observation | Technical reading | ScoreFly response |
|---------------------|-------------------|-------------------|
| High conviction in NRL, MLB, League of Ireland (~95 ratings) | Thresholds (85–90) are low relative to scores; many games qualify | Expected — those leagues have high historical close-game rates (49–68%). Not a bug. |
| Lower conviction in AFL (~73 ratings at thr 72) | Many AFL games barely clear the bar | Expected — AFL historical close rate is only **27.5%**, lowest of major feeds. Recommend **raising** threshold to 75. |
| WNBA duplicate ledger rows (reversed home/away) | Two ESPN event IDs for one fixture | Ledger keys by `m.id` — dedupe by `(leagueKey, team-pair, date)` is a future improvement, not a threshold issue. |
| “Top six picks” rail (Bulldogs/Sea Eagles, White Sox/Braves, etc.) | Highest `r` scores in export | Valid surface list; all are `r >= thr` with room to spare. |
| Run dual-model audit before launch | Opus for code, GPT for UX | Agree — separate from threshold maths but high ROI. |
| Tune until yellow ≈ red per league | Precision/recall calibration | **Correct goal**, but requires finished ledger rows with `rf:1` or `a:1`. |

ChatGPT did **not** produce a full 45-league threshold table — it inferred league *quality* from one ledger snapshot. This document fills that gap using ScoreFly’s research pipeline.

---

## 3. How thresholds work in ScoreFly

### Two engines

| Engine | Feeds | Threshold location |
|--------|-------|-------------------|
| **FlyTime v1** | 45 leagues with `*-flytime-v1.json` | Per-league `threshold` in `FLY_V1_REGISTRY` |
| **Legacy FlyMatch** | Cricket, tennis, any feed without v1 table | `FLYMATCH_THRESHOLD` = **62** (with margins), **82** (without) |

### v1 scoring formula

```
score = close_rate×0.35 + form_balance×0.25 + margin_balance×0.25 + matchup×0.15
isFlyMatch = (score >= threshold)
```

Yellow fly appears when `isFlyMatch` is true on an upcoming card.

### Red fly definition (ground truth)

A match gets a red fly if it **entered FlyTime live** (`isFlyTime()` returned true during polling) and then finished. Rules are sport-specific (e.g. basketball: Q4, clock running, margin ≤ 8).

**Important:** Offline research tables measure **final close margin**, not retroactive FlyTime windows. Close rate is a *proxy* for red-fly rate, not identical.

### Offline calibrator target

`scripts/calibrate_flytime.py` picks the threshold that yields **~2 yellow flies per week-chunk** (chunk size varies by league: 4–50 games). That is a *volume* target, not strict yellow:red parity.

---

## 4. Goal: yellow rate ≈ red rate

Per league **L** and round **R**:

```
yellow_rate(L,R) = yellow_flies / games_in_round
red_rate(L,R)    = red_flies    / finished_games_in_round

Target: yellow_rate ≈ red_rate  (within ~±30% once sample size ≥ 20 games)
```

### Tuning rules (FlyTime Lab)

| Symptom | Ledger signal | Action |
|---------|---------------|--------|
| Too many yellows, few reds | High `falseAlarm` (p=1, fin=1, rf=0) | **Raise** threshold (+2 to +5) |
| Reds without yellows | High `missed` (p=0, rf=1) | **Lower** threshold (−2 to −5) |
| Good hits | Blue flies (p=1 and a=1) | Hold threshold |

Enable monitor: `scorefly.app/?flylab=1` → Teams tab → FlyTime Lab → “Per-league threshold monitor”.

---

## 5. Current thresholds (production)

### Legacy

| Constant | Value |
|----------|------:|
| `FLYMATCH_THRESHOLD` | 62 |
| `FLYMATCH_THRESHOLD_NODATA` | 82 |

### V1 registry (all 45 leagues)

| Tag | League | Current | Chunk size |
|-----|--------|--------:|-----------:|
| FT | AFL | 72 | 16 |
| NFL | NFL | 93 | 16 |
| NBA | NBA | 88 | 16 |
| WNBA | WNBA | 70 | 6 |
| NBL | NBL | 70 | 8 |
| NCAAM | NCAAM | 97 | 50 |
| NCAAF | NCAAF | 96 | 50 |
| MLB | MLB | 85 | 16 |
| NHL | NHL | 78 | 16 |
| CFL | CFL | 85 | 4 |
| NRL | NRL | 85 | 8 |
| MLS | MLS | 96 | 10 |
| EPL | EPL | 96 | 10 |
| LIGA | La Liga | 96 | 10 |
| BUN | Bundesliga | 92 | 9 |
| SER | Serie A | 95 | 10 |
| L1 | Ligue 1 | 95 | 9 |
| CH | Championship | 98 | 12 |
| ERE | Eredivisie | 88 | 9 |
| POR | Primeira Liga | 97 | 9 |
| SCO | Scottish Prem | 85 | 6 |
| TUR | Super Lig | 95 | 9 |
| BRA | Brasileirão | 97 | 10 |
| ARG | Liga Argentina | 98 | 10 |
| MX | Liga MX | 90 | 9 |
| ALE | A-League | 85 | 6 |
| IRL | League of Ireland | 90 | 5 |
| ISL | Indian Super League | 85 | 6 |
| PSL | SA Premier League | 95 | 6 |
| WSL | WSL | 78 | 6 |
| UCL | Champions League | 93 | 8 |
| UEL | Europa League | 95 | 8 |
| LIB | Libertadores | 96 | 8 |
| J1 | J-League | 96 | 10 |
| LO | League One (ENG) | 97 | 12 |
| LT | League Two (ENG) | 97 | 12 |
| CSL | Chinese Super League | 94 | 10 |
| BEL | Belgian Pro | 88 | 8 |
| SUI | Swiss Super League | 85 | 8 |
| GRE | Greek Super League | 93 | 8 |
| SB | Serie B | 97 | 10 |
| KSA | Saudi Pro League | 96 | 9 |
| RUS | Russian Premier | 94 | 8 |
| URC | United Rugby Championship | 90 | 8 |
| T14 | Top 14 | 88 | 8 |

---

## 6. Research-calibrated thresholds (offline re-run, Jun 2026)

Re-ran `calibrate_flytime.py` logic against all 45 JSON files. Target: ~2 yellows per chunk.

### Changes recommended (5 leagues)

| Tag | Current | **Recommended** | Δ | Rationale |
|-----|--------:|----------------:|--:|-----------|
| **CFL** | 85 | **70** | −15 | App far stricter than research; at 85 almost nothing flags. Calibrated chunk avg 2.05 yellows at 70. |
| **IRL** | 90 | **80** | −10 | `soccer-thresholds.json` already had 80; app was raised to 90. High close rate (68%) — lower bar restores ~2.5 yellows/chunk. |
| **AFL** | 72 | **75** | +3 | ChatGPT noted weak AFL picks at 72–74 scores. Low close rate (27.5%) — tighten to reduce false yellows. |
| **NFL** | 93 | **95** | +2 | Minor tighten; close rate 53.7%, currently ~1.97 yellows/chunk at 93. |
| *All others* | — | *unchanged* | 0 | Already within ~1.4–2.6 yellows/chunk at current threshold. |

### Full recommended registry (apply only the 4 changes above)

All leagues not listed in the “Changes” table keep their **Current** value from Section 5.

---

## 7. Historical close-game rate by league (proxy for red-fly density)

From `matchup_close_rates` in each JSON file (% of games finishing within sport close margin):

| Tier | Close % | Leagues |
|------|--------:|---------|
| **High** (65%+) | 66–75 | PSL, ARG, LT, BRA, LIB, IRL, GRE, TUR, SER, LIGA |
| **Mid** (50–65%) | 50–64 | Most soccer, NRL, NFL, UCL, UEL, CFL, URC, T14 |
| **Low** (<50%) | 27–46 | **AFL**, NBA, NBL, NHL, MLB, NCAAM, NCAAF, WNBA |

**ChatGPT implication:** High-rated NRL/MLB/Ireland predictions in the ledger are consistent with high close rates + moderate thresholds. AFL looking “weak” at 72–74 is also consistent — the sport rarely produces tight finishes historically.

**ScoreFly implication:** Do not lower AFL threshold to “match” NRL yellowness. Different sports need different bars. Yellow:red parity is per-league, not cross-league.

---

## 8. ChatGPT ledger snapshot — re-read

Sample export (22 matches, all `p:1, a:0, fin:0`):

| League | Avg rating | Threshold | Above bar? |
|--------|----------:|----------:|:----------:|
| NRL | ~95.1 | 85 | All strongly |
| League of Ireland | ~94.6 | 90 | All strongly |
| MLB | ~95.8 | 85 | All strongly |
| WNBA | ~83.5 | 70 | All, some barely |
| AFL | ~77.1 | 72 | Several at 72.5–73.9 |

ChatGPT’s “top six” picks (≥95.9 rating) are the correct high-confidence surface for a “Top FlyTime” rail. That does not require threshold changes — it requires UI surfacing.

---

## 9. ScoreFly response to ChatGPT (agree / disagree / defer)

### Agree

- Yellow:red alignment is the right north star for threshold tuning.
- AFL needs a **higher** bar, not parity with NRL.
- Ledger duplicate WNBA rows are a data hygiene issue (ESPN double IDs).
- Live FlyTime detection must be verified before trusting false-alarm counts.
- Dual-model pre-launch audit (Opus code + GPT product) is worth the hour.

### Disagree or nuance

- **“Tune from this ledger export alone.”** Cannot — zero red confirmations (`a:0`, `fin:0` on all rows).
- **“NRL/MLB high ratings mean thresholds too low.”** Not necessarily — high scores with high close rates mean the model is doing its job; tune only if false alarms appear after live validation.
- **“~2 yellows per round for every league.”** Offline calibrator uses that as a default volume target; yellow:red parity may need a *different* target rate per league once red data exists.

### Defer until live data

- Soccer threshold micro-adjustments (most already match calibration).
- Legacy `FLYMATCH_THRESHOLD` 62/82 — only applies to non-v1 feeds.
- Round-level tuning (e.g. EPL Matchweek 12 vs 38) — need `fin:1` ledger rows tagged by round.

---

## 10. Recommended action plan

### Phase A — Apply now (low risk, research-backed)

Update `FLY_V1_REGISTRY` in `index.html`:

```javascript
'australian-football|afl':  threshold: 75   // was 72
'football|nfl':             threshold: 95   // was 93
'football|cfl':             threshold: 70   // was 85
'soccer|irl.1':             threshold: 80   // was 90
```

Sync `soccer-thresholds.json` IRL entry to 80.

### Phase B — Live validation (blocking for ratio tuning)

1. Open app during one close finish per sport (AFL Q4, NRL 2nd half, EPL 80'+, NBA Q4).
2. Confirm **green fly** appears live.
3. Confirm **red fly** on Results after FT.
4. Confirm ledger row gets `a:1` then `fin:1`, `rf:1`.

### Phase C — Ledger-driven tune (after ≥20 finished games per league)

For each league in FlyTime Lab:

```
if falseAlarm_rate > 0.4 × yellow_rate → threshold += 3
if missed_rate    > 0.3 × red_rate    → threshold -= 3
re-evaluate weekly
```

### Phase D — Deep research upgrade (best long-term yellow:red fit)

Extend `scripts/build_flytime_v1.py` to label historical games with **retroactive `isFlyTime()`** (period + clock + margin at each poll point), not just final margin. Set:

```
threshold(L) such that P(score ≥ thr) ≈ historical_flytime_rate(L)
```

This makes yellow:red alignment derivable from JSON alone.

---

## 11. Quick reference — ChatGPT vs ScoreFly final thresholds

| Tag | Production today | ChatGPT-style inference | **ScoreFly recommended** |
|-----|-----------------:|-------------------------|-------------------------:|
| AFL | 72 | Raise (weak picks) | **75** |
| NRL | 85 | Hold (high conviction OK) | **85** |
| MLB | 85 | Hold | **85** |
| IRL | 90 | Hold / slight lower | **80** |
| WNBA | 70 | Hold | **70** |
| CFL | 85 | Lower (under-flagging) | **70** |
| NFL | 93 | Slight raise | **95** |
| All other v1 | (see §5) | Hold | **unchanged** |
| Legacy | 62 / 82 | Hold until v1 tables exist | **62 / 82** |

---

## 12. Files to edit when applying Phase A

| File | Change |
|------|--------|
| `index.html` | `FLY_V1_REGISTRY` — AFL, NFL, CFL, IRL thresholds |
| `soccer-thresholds.json` | IRL `threshold`: 90 → 80 |
| `VERSION HISTORY.md` | Note threshold tune + reference this doc |
| `SCOREFLY.md` | Update threshold table if maintained there |

---

*Generated for ScoreFly / StatFly FlyTime calibration. Re-run offline calibration after rebuilding any `*-flytime-v1.json` with `python scripts/calibrate_flytime.py`.*
