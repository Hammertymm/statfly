# Phase 2 - Calculation & Formula Audit

Every scoring formula and threshold the app uses, critiqued. Scores are Impact / Effort / Risk (1-10).

---

## 2.1 The v1 composite (`flyV1Score`)

**Purpose:** rate an upcoming matchup 0-100 for "will be close/exciting" from offline tables.

**Current implementation** (`index.html:5440-5457`):

```js
closeRate*0.35 + formBalance*0.25 + marginBalance*0.25 + matchupRating*0.15
formBalance   = 100 - |formHome - formAway|
marginBalance = 100 - |marginHome - marginAway|
```

Returns `null` if any of the six lookups miss (`5451-5453`), so a missing matchup drops out entirely rather than scoring low.

**Cost:** trivial arithmetic, 6 hash lookups per match.

**Accuracy concerns:**
- `formBalance`/`marginBalance` reward *similarity*, not *closeness*. Two evenly-bad blowout teams score a high balance even though their games are blowouts. The only true closeness signal is `closeRate` (weight 0.35) and `matchup` (0.15) - together 50%. The other 50% is "how alike are these teams", a proxy that can mislead (two identical run-and-gun teams play high-variance, often non-close games).
- The weights are uniform across 45 leagues (only the *threshold* varies). A basketball blowout and a soccer 1-0 are scored by the same balance arithmetic.
- `matchupRating` is `avg_excitement` from the table - an opaque historical metric whose definition lives only in the build scripts.

**Risk of changing:** medium - the tables are calibrated to these exact weights; changing weights invalidates every threshold.

**Suggested improvement:** raise `closeRate` weight (it is the only direct closeness signal) and reduce the two balance terms, OR document explicitly that "balance" is an intentional excitement proxy. Either way, **the weights must live in exactly one place** (see 2.7).

**Impact 4 / Effort 5 / Risk 6.** Calibration-coupled; do not touch before Phase 3's validation gate is passed.

---

## 2.2 `form_strength` saturation (offline tables)

**Purpose:** a 0-100 team-strength scalar feeding `formBalance`.

**Current implementation:** built offline (`scripts/build_flytime_v1.py`), surfaced as `form_strengths[].strength`. The brief cites `form_strength = 40 + 40*win + 20*close`. That is a **saturating** function: a team that wins everything closely maxes at 100, a team that loses everything sits at 40 (not 0), so the usable spread is 40-100, compressing `formBalance` toward the top of its range.

**Accuracy:** the 40 floor narrows differences - `100 - |a-b|` rarely drops far, so `formBalance` is usually 80-100. This is the same compression bug that v80 fixed for competitiveness in the *legacy* model (`SCOREFLY.md`, FlyMatch history), but it still lives in the v1 form term.

**Suggested improvement:** if recalibrating, rescale strength to use the full 0-100 range before differencing. **Impact 3 / Effort 6 / Risk 6** (table rebuild).

---

## 2.3 Tight-margin denominator `close_margin*3` (`fmCloseProfile`)

**Current implementation** (`index.html:5326-5335`):

```js
tight = max(0, 1 - avg / (thr*3));   // ~0 once avg margin hits 3x the close mark
return 0.7*rate + 0.3*tight;
```

**Critique:** `thr*3` is arbitrary. For basketball `thr=8` so `tight` hits 0 at a 24-pt average margin; for soccer `thr=1` it hits 0 at a 3-goal average. The 3x choice is unexplained and differs in meaning per sport. `rate` (share of games within `thr`) is the sound part; `tight` is a soft secondary that mostly tracks `rate` anyway. **Impact 2 / Effort 2 / Risk 3** - either drop `tight` (simpler) or document the 3x.

---

## 2.4 Legacy `computeFlyMatch` weights + additive importance

**Current implementation** (`index.html:5277-5279`, `5563-5612`):

```js
FLYMATCH_WEIGHTS = { close:45, competitiveness:30, form:10 };  // sum 85, renormalised by skip-on-null
rating += (m.fmImp||0) * 10;   // additive, capped to 100
bar = haveBothClose ? 62 : 82; // FLYMATCH_THRESHOLD / _NODATA
```

**Strengths:** the v78/v80/v83 history is sound. Skip-on-null renormalisation (`den` accumulation) correctly avoids scoring thin data as 0. Additive importance fixes the v67 averaging bug. The data-aware two-tier threshold is a pragmatic answer to flaky margin data.

**Critique:**
- Weights sum to 85 not 100; harmless because of renormalisation, but means `rating` is "percent of available weighted signal", which interacts oddly with the additive `+10*fmImp` bonus (a final with thin data can clear 82 on importance alone). Worth a comment.
- `competitiveness` from `fmWinPct` uses early-season records that are noisy (a 2-0 vs 0-2 looks like a total mismatch in week 1).
- This whole model only runs for the **2 sports without a v1 table** (cricket has none; everything else uses v1). `runFlyMatchSweep` (`5551`) calls it only `if(!usesFlyV1Engine(m))`. So for 45/47 feeds it is dead weight that still executes the guard. The legacy model is effectively a cricket-only fallback - but **cricket has no `CLOSE_MARGIN` entry** (`5292-5295` lists 8 sports, none is cricket), so `fmCloseProfile` gets `thr=undefined` and returns `null`, and cricket yellow flies rely entirely on competitiveness/importance. Effectively the legacy model produces almost nothing useful for the only sport that reaches it.

**Suggested improvement:** decide whether legacy is still needed at all (Phase 3 recommends collapsing layers). If kept, add a cricket `CLOSE_MARGIN` or document that cricket never gets a yellow fly. **Impact 4 / Effort 3 / Risk 4.**

---

## 2.5 `FLYMATCH_COMP_GAP = 0.5` and momentum maths

- `FLYMATCH_COMP_GAP = 0.5` (`5282`): two teams whose win% differ by >= 0.5 score 0 competitiveness. Reasonable; v80's sharpening. No change.
- **Momentum gain/decay** (`flyGainAndConfidence` `2685`, `flyHalflife` `2633`, `MOM_*` `1766-1785`): audited in Phase 4. The math is internally consistent; the concern is *compute*, not correctness.

---

## 2.6 `isFlyTime` per-sport thresholds + `FLY_BLOWOUT_MARGIN`

**Current implementation** (`index.html:1934-1960`, `1964-1973`):

| Sport | FlyTime rule | Blowout unpin |
|-------|--------------|---------------|
| basketball/football | Q4, <=300s, margin <=8 | 16 |
| hockey | P3, <=300s, margin <=1 | 3 |
| baseball | inning >=8, margin <=2 | 5 |
| AFL | Q4 elapsed >=20:00, margin <=12 | 24 |
| NRL | H1/H2 elapsed >=35:00, margin <=12 | 24 |
| rugby union | H2, <=600s, margin <=12 | 24 |
| soccer | minute >=80, margin <=1 | 3 |

**Critique:**
- These mirror `flytime.py:is_flytime_live` (`152-194`) **and** `config.py:FLY_BLOWOUT_MARGIN` (`19-28`) - three copies that must stay in lockstep by hand. The JS and Python `is_flytime` agree today; nothing enforces that.
- Baseball uses no clock (`p >= 8 && margin <= 2`) - fine, but it means a 7th-inning tie never qualifies and a blowout-then-rally is caught only from the 8th.
- Soccer parses the minute from `clockRaw` (`1954`); `parseInt("90+3",10)=90` works, but stoppage-time drama past 90 is treated as exactly 90 - acceptable.

**Accuracy:** the rules are reasonable defaults but **never confirmed against a live close finish** (Phase 3). No change to thresholds recommended until detection is proven.

**Impact 3 / Effort 2 / Risk 5** (changing thresholds blind is risky).

---

## 2.7 Duplicate logic - the v1 formula in 10+ places

The same `close*0.35 + form_balance*0.25 + margin_balance*0.25 + matchup*0.15` (and its balance sub-formulas) is independently written in:

| File | Line |
|------|------|
| `scorefly/index.html` (`flyV1Score`) | 5456 |
| `flytime-engine/flytime_engine/flytime.py` | 120-128 |
| `flytime-engine/flytime_engine/config.py` (`FORMULA_VERSIONS`) | 196 |
| `scripts/build_flytime_v1.py` | 407, 456 |
| `scripts/build_soccer_flytime.py` | 249, 294 |
| `scripts/build_nfl_flytime.py` | 259 |
| `scripts/calibrate_flytime.py` | 35 |
| `scripts/calibrate_nfl_threshold.py` | 36 |
| `scripts/score_nfl_upcoming.py` | 33 |
| `scripts/score_upcoming.py` | 91 |
| `scripts/explain_fly.py` | 69 |

**Cost of the duplication:** any weight change must be made in 11 places; a missed one silently produces a table whose scores disagree with the runtime. The threshold candidates (`config.py:64`) and the live thresholds (`FLY_V1_REGISTRY`) are likewise independent.

**Risk:** the hard rule forbids a build step / npm for the *PWA*, but the **Python side is offline tooling** and has no such constraint. The duplication there is pure tech debt.

**Suggested improvement:** in the Python package, define the formula once (it already half-exists as `FORMULA_VERSIONS` in `config.py` and `FlyTimeEngine.score_matchup`); have every `scripts/*.py` import it instead of re-typing it. The JS copy must stay inline (single-file rule) but should carry a comment pointing at the canonical Python definition and the weights should be named constants, not magic numbers in one expression.

**Impact 5 / Effort 4 / Risk 2** (offline only, no PWA risk). High-value cleanup.

---

## 2.8 The twice-per-poll / double-pass sweeps

**Current implementation:**
- `loadLiveData` calls `runFlyMatchSweep()` (`3200`); so does `refreshLiveFeeds` (`3266`); so does `hydrateSnapshot` (`3128`) and `loadFlyV1Engines` (`5543`). Expected.
- **Inside one sweep**, `runFlyMatchSweep` (`5551-5559`) iterates `ALL_LIVE` then `ALL_UPCOMING` calling `computeFlyMatch` (for non-v1), then calls `applyAllFlyTimeV1` (`5499`) which iterates `ALL_UPCOMING` **again**. So `ALL_UPCOMING` is walked twice every sweep.
- `computeFlyMatch` also calls `ledgerPredict` (`5610`) which, on the first prediction for a match, calls `renderFlyDashboard()` (`2076`) - so a sweep can trigger a full dashboard rebuild mid-sweep.

**Cost:** O(2 x |UPCOMING|) per sweep plus possible dashboard rebuilds. With a busy board (hundreds of upcoming across 48 feeds in the 30-day window) this is the dominant CPU cost after rendering.

**Suggested improvement:** single pass - branch per match (`usesFlyV1Engine ? v1 : legacy`) inside one loop over UPCOMING (and one over LIVE), and never call render from inside `ledgerPredict` (debounce/flag instead). **Impact 5 / Effort 3 / Risk 3.**

---

## 2.9 Repeated `favMatchNames` / `teamMatch` passes

**Current implementation:** `renderHome` (`4624`), `renderResults` (`4660`), and `buildFlyModeGrid` (`4835`) each call `favMatchNames()` afresh, and `teamMatch` (`4612`) does up to 6 substring tests per match per call. All three render functions run every poll. `favMatchNames` itself loops `favs` and a halo-index lookup each time (`4598-4609`).

**Cost:** O(favs) rebuild of the name list 3x/poll + O(matches x favNames x 6) matching. Small for a few favourites, but it is recomputed from scratch every poll though `favs` changes only on user action.

**Suggested improvement:** compute `favMatchNames()` once per favourites-change into a cached lowercase Set/array, reuse across all three renderers. **Impact 3 / Effort 2 / Risk 2.**

---

## 2.10 Cricket run-rate engine

**Current implementation** (`updateCricketFly` `2930`, constants `1787-1790`): batting momentum = `(rr/fireRR)*70` clamped 0-100, `fireRR` = 10 (T20) or 6 (ODI); wicket knocks rr back 40% (`*0.6`, `2984`); bowling side gains `38`/wicket; cold/comeback disabled.

**Critique:**
- Sound and well-commented. `cricketOversToBalls` (`2925`) correctly treats overs as base-6 (e.g. 12.3 = 12 overs 3 balls).
- The wall-clock fallback `CRICKET_SEC_PER_OVER = 240` (`2976`) is generous (4 min/over); in a fast T20 over this under-counts overs and inflates run rate. Minor.
- ODI bar uses `cricketMaxOvers > 20` (`2936`); a 50-over game without `maxOvers` data defaults to the T20 bar (10/over), making 50-over momentum too hard to earn. Edge case tied to data availability.

**Impact 2 / Effort 3 / Risk 3.** Leave unless cricket becomes a priority.

---

## 2.11 Hidden coupling (thresholds drift)

Manually-synced pairs with no automated guard:

- `FLY_V1_REGISTRY` thresholds (`index.html:5353`) <-> `config.py:LEAGUES[].threshold` (`config.py:136-191`). Spot-check shows they currently agree (NBA 88, NFL 95, NRL 85, etc.), but nothing enforces it.
- `isFlyTime` (JS `1934`) <-> `is_flytime_live` (`flytime.py:152`) <-> `FLY_BLOWOUT_MARGIN` (JS `1964` / `config.py:19`).
- `CLOSE_MARGIN` (JS `5292`) <-> per-league `close_margin` (`config.py` per `LeagueConfig`).
- The v1 weights (2.7).

**Suggested improvement:** a tiny offline `scripts/check_sync.py` that parses the registry block out of `index.html` and asserts equality with `config.py`, run manually before deploy. Does not touch the PWA. **Impact 4 / Effort 3 / Risk 1.**

---

## Phase 2 summary

| # | Finding | Impact | Effort | Risk |
|---|---------|:--:|:--:|:--:|
| 2.7 | v1 formula duplicated 11x; centralise in Python | 5 | 4 | 2 |
| 2.8 | Double-pass sweep + render-from-ledger | 5 | 3 | 3 |
| 2.11 | Threshold drift, add a sync check | 4 | 3 | 1 |
| 2.4 | Legacy model is cricket-only yet cricket has no CLOSE_MARGIN | 4 | 3 | 4 |
| 2.9 | favMatchNames/teamMatch recomputed 3x/poll | 3 | 2 | 2 |
| 2.1 | v1 balance terms reward similarity not closeness | 4 | 5 | 6 |
| 2.6 | isFlyTime thresholds unvalidated (see Phase 3) | 3 | 2 | 5 |
| 2.3 | `close_margin*3` magic denominator | 2 | 2 | 3 |
| 2.2 | form_strength 40-floor compresses balance | 3 | 6 | 6 |
| 2.10 | cricket wall-clock over fallback | 2 | 3 | 3 |
