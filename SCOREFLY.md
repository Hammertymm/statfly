# ScoreFly

Mobile-first sports scores app. Pure black UI, Apple-style typography, single self-contained HTML file. Works in any mobile browser, installable as a PWA.

**Tagline:** Scores Anywhere. Simple.
**Brand colour:** `#06f03c` (electric green; swapped from `#30d158` in the v69-v74 pixel-match pass)
**Current file:** `index.html` (cache `scorefly-v134`)
**Live URL:** [scorefly.app](https://scorefly.app) · [hammertymm.github.io/scorefly](https://hammertymm.github.io/scorefly)
**Repo:** [github.com/Hammertymm/scorefly](https://github.com/Hammertymm/scorefly)

> **Name:** the app rebranded **StatFly → ScoreFly** (by v50). Repo, Pages URL, and custom domain now use `scorefly`. In-app wordmark, storage keys (`scorefly_*`), and SW cache are all `scorefly`. Treat this doc as authoritative.

**This single document is the source of truth.**

-----

## How to work on this codebase

Bias toward caution over speed.

**Think before coding.** State assumptions explicitly. If multiple interpretations exist, present them rather than picking silently. If a simpler approach exists, say so. If something is unclear, stop and name it before writing code.

**Simplicity first.** Smallest change that solves the problem. No features beyond what was asked.

**Surgical changes.** Touch only what the request requires. Match existing style. Every changed line should trace to the request.

**Verify before delivering.** No test suite — verification means: unicode check (no forbidden chars in `<script>`), page-div order (`page-home` > `page-results` > `page-settings`), `results-cards` inside `page-results`, a JS syntax check, and (for behaviour changes) a description of what to tap on the phone to confirm.

**The user is a non-coder.** Explain in plain English, name new concepts the first time, narrate what code does, build in small steps, check in. Never claim something works without verifying it.

-----

## File freshness rule (read this FIRST, every session)

The `/mnt/project/` copy of `index.html` goes stale between sessions — the user deploys to GitHub between chats and the project copy does not auto-sync. We have lost work trusting the stale copy.

**First step every session:** ask the user to upload the current `index.html` from GitHub, or fetch from the live URL. Do NOT trust `/mnt/project/`.

-----

## What it does

Follow favourite teams across 48 league feeds / 25 countries (plus global competitions); see live scores, upcoming fixtures, and recent results in one feed (windows are view-dependent; see Request window). No login, no ads.

|Tab    |Shows                                                                                                                                                                                                 |
|-------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
|Feed   |“Worth watching now” FlyTime section pinned on top (shown only when a live game is in Fly Time), then live matches + upcoming fixtures (All: next 14 days / My Teams: next 30). My Teams / All toggle.|
|Results|Completed matches (All: last 7 days / My Teams: last 30). My Teams / All toggle.                                                                                                                      |
|Teams  |Follow/manage teams. Global search. **FlyTime ALL** toggle (global close-finish alerts; renamed from “FlyTime Buzz” in v77). **FlyTime Lab** dashboard (enable via `?flylab=1`, persists in localStorage).                                                 |

A fourth bottom-nav button opens **Fly Mode**: full-screen live scores for followed teams, for glancing across a room.

-----

## Onboarding

**Single-hero onboarding (BUILT v68).** Onboarding now opens on ONE hero screen: the rebuilt poster `onboard-hero.png` (“We’ll Tell You When It Matters”, sells FlyTime/FlyTime ALL visually, full-bleed) with a sticky “Choose My Teams” green button -> team selection (step 2) -> notifications (step 3). The old `onb-step-1` welcome content and the `onb-step-fly` “Meet FlyTime” screen are retired (the hero carries that message); `onb-step-fly` markup is left orphaned/unreachable. Flow is now Hero -> Pick teams -> Notifications. Notifications confirmed to come AFTER team selection: `onbAddTeam` and search-add both follow teams with `alert:false` (bell off), and `onbEnableNotifs` (step 3) sets `alert=true` on all followed teams only when permission is granted. The hero image is the bottom-cropped version of JRod’s render (the baked-in CTA pill removed so a real button can sit beneath), pre-cached in `sw.js`.

First-run flow triggered when `scorefly_onboarded` is not set in localStorage. Four screens, led by FlyTime and guided by the **SupaFly** mascot (introduced v51). Step navigation is `onbGoStep(n)`, which hides every `.onb-step` by class and shows the target by id, so it accepts both numeric ids and the string `'fly'`.

1. **Welcome** — SupaFly (welcome pose) + ScoreFly wordmark + tagline + the value hook (“Too much sport, not enough time. ScoreFly shows you which games are worth watching right now.”). Button -> `onbGoStep('fly')`.
1. **Meet FlyTime** (`onb-step-fly`) — SupaFly (pointing pose) + a pulsing green `FLYTIME` badge + a black-box explanation. Exists to make FlyTime memorable; no thresholds revealed.
1. **Pick your teams** — search for a team or tap **Quick Start with Global Starter Pack** (one tap, all five). Search path: after first pick, two same-country recommendations under “Because you follow [team]”, then the five Global Starter Pack teams as individual cards, then **Continue** to notifications. No mascot (kept uncluttered).
1. **Notifications** — SupaFly (here’s-the-score pose) + opt-in step; grants bell alert for all followed teams on approval.

SupaFly assets: `supafly-welcome.png`, `supafly-pointing.png`, `supafly-score.png`, `supafly-thumbsup.png` (thumbsup bundled, reserved for later). Transparent PNGs on pure black, pre-cached in `sw.js`.

On finish: sets `scorefly_onboarded = '1'`, drops user into their feed.

**Suggested for you** (Teams tab) is unused — suggestions live only in the onboarding overlay. `renderSuggested()` always hides the Teams-tab section.

Onboarding recommendation engine (`onbGetSuggestions`), two slots anchored on `favs[0]`:

1. Two same-country picks (one per league where possible; same-league marquees backfill single-league countries)
1. After those, the five Global Starter Pack teams always show as individual add cards
1. If `favs` becomes empty, step 2 resets to search + one-tap starter pack

-----

## FlyState engine (START HERE for FlyState work)

ScoreFly’s signature feature: live score cells (and Fly Mode scores) are **colour-filled** to show what’s happening at a glance. Colour is a solid fill (not a glow). The colour-coded card BORDERS (green live / yellow upcoming / red result) are a SEPARATE system from FlyState score colours.

### The eight states

|State     |Colour         |Token       |Meaning                                    |
|----------|---------------|------------|-------------------------------------------|
|Neutral   |White          |(no class)  |Steady / even                              |
|Warming up|Yellow         |`--upcoming`|Building momentum                          |
|On a run  |Orange         |`--onrun`   |Scoring streak                             |
|On fire   |Red            |`--result`  |Dominant run                               |
|Gone cold |Blue           |`--cold`    |Stalled while the opponent heats up        |
|Comeback  |Purple         |`--comeback`|Clawed back a real deficit, now ~level     |
|Fly Time  |Green          |`--live`    |Close + late: clutch (both scores go green)|
|Overtime  |Red clock/badge|—           |Game in OT (match-level, Fly Mode badge)   |

CSS classes `fs-warming / fs-onrun / fs-onfire / fs-cold / fs-comeback / fs-flytime` apply to `.sc` (feed) and `.flymode-score`. Fly Time green pulses (`flyPulse`). **FlySense 2.0:** the exact score colour is a CONTINUOUS gradient set inline per cell (`getFlyStyle` -> `flyHeatColour` / `flyColdColour` / `flyCbColour`); the classes remain as anchor fallbacks and semantic hooks. Extremes add `fs-xfire` (brightening pulse + warm glow, momentum >= 90) or `fs-xcold` (dim/desaturate + frost glow); both respect `prefers-reduced-motion`. Research basis: `_research/FlySense-2.0/`.

### How it works (derived from score + clock only — no extra feeds)

Per-match state: `flyState[id]` — see the comment block above its declaration in `index.html` (momentum, deficits, run persistence, ember/peak memories, drought timestamps, hysteretic tier, gradient colour, extreme flag, trailing `hist` window, cricket overs/run-rate/wickets).

- **Momentum** 0-100 per side. Each poll: wall-clock exponential decay then **clock-validated gain** — score bursts are spread over elapsed **game time** (or wall time when the clock is unavailable), not treated as a single instant spike after stale refreshes. `flyGainAndConfidence` compares `pollDt` vs `gameElapsed`; batched jumps with a stuck clock get `confidence` ~0.35 and blocked `fs-xfire`. See `_research/FlySense-2.0/14-refresh-anomaly-investigation.md`. `MOM_GAIN = 70`.
- **Dynamic decay** (`flyHalflife`): per-sport base half-life, stretched up to 1.8x by run persistence (maxes at 5 min) and nudged by held state (onfire 1.3x slower, warming 0.8x faster).
- **Per-sport tuning** `FLY_TUNING[sportKey] = { bigPlay, cbMin, halflife, droughtNorm }`: basketball `{6,10,40,90}`, football `{7,11,50,300}`, hockey `{2,2,70,480}`, soccer `{1,2,90,900}`, baseball `{3,3,75,720}`, australian-football `{9,18,55,300}`, rugby-league/rugby `{6,12,55,360}`, cricket (run-rate engine, below).
- **Tiers** (`momTier`): soft hysteretic bands — enter onfire 70 / exit 64, enter onrun 45 / exit 40, enter warming 20 / exit 16. Labels never chatter at a boundary; the COLOUR is continuous so 67 vs 68 look near-identical while 43 vs 67 visibly differ.
- **resolveSide priority:** comeback > onfire > onrun > warming > cold > neutral. Comeback = was down >= `cbMin`, clawed back >= half of max deficit, now within +/-`cbMin`, momentum >= 20 (14 to EXIT once held). Comeback purple is intensity-scaled by magnitude (deficit size 1x->4x `cbMin`, recovery fraction, recovery speed, level-or-ahead bonus). Cold = own momentum < 12 while opponent >= 42 (exit 16/36), OR an absolute drought (> 2.5x `droughtNorm` scoreless while behind with the opponent ticking over). Cold blue is severity-scaled (stall depth, opponent dominance x scoring share, drought, collapse from a recent peak); Extreme Cold (`fs-xcold`) needs frozen momentum + real drought + dominance together.
- **Cricket (run-rate engine, `updateCricketFly`):** batting side momentum tracks recent run rate (EWMA over ~2 overs, overs from linescores with a ~4 min/over wall-clock fallback) against the format's on-fire bar — **T20 10+/over, ODI (50-over) 6+/over maps to momentum 70 (on-fire entry)**; a wicket falling knocks the rate back 40%. Bowling side gains `CRICKET_WICKET_GAIN` (38) per wicket taken — two quick wickets = on fire. Cold/comeback are disabled for cricket (innings scores make deficit logic meaningless).
- **Fly Time** (`isFlyTime`): basketball/football: Q4, <=300s remaining, margin <=8; hockey: P3, <=300s, margin <=1; baseball: inning >=8, margin <=2; AFL: Q4 elapsed >=20:00, margin <=12; **NRL: each half clock counts up, elapsed >=35:00 in H1/H2 (or OT close), margin <=12**; rugby union: H2, <=600s remaining, margin <=12; soccer: minute >=80, margin <=1. Tennis and cricket excluded.
- **Overtime** (`detectOT`): per sport; OT outranks Fly Time.

### FlyTime indicator - the coloured fly (v66, LOCKED SPEC)

Separate, self-contained system. It does NOT touch FlySense score colours or the status borders - those are two other independent systems (three total: score-colour fill, status borders, fly icon).

A single coloured fly icon sits in the FIXED top-right slot of every card (and Fly Mode), across every sport/league/screen. Traffic light:

- **Green** (`fly-green.png`) - live AND currently in Fly Time (`getMatchFly(id)==='flytime'`). Solid.
- **Green, flashing** (same `fly-green.png` + `ft-likely`) - live AND the predictive FlyTime 2.0 engine says **Likely** but the proven Confirmed gate has not fired yet. Same icon, pulsing opacity; appears EARLIER than the solid green, then either firms into solid green (Confirmed) or turns off if the match drops back out of the Likely band. See "FlyTime 2.0" below.
- **Yellow** (`fly-yellow.png`) - upcoming AND predicted to reach Fly Time (`m.isFlyMatch`).
- **Red** (`fly-red.png`) - finished AND reached Fly Time while live (`matchHadFlyTime(id)`).
- **Blue** (diagnostic only, FlyTime Lab) - yellow predicted, then reached FlyTime live (Y→G hit). Not shown on user-facing cards.

One fly per card max; none shown if no FlyTime state. Resolved by `flyTimeIcon(m, status)` where status is `'live'|'upcoming'|'result'`. Icons are external PNGs (cropped from the brand SupaFly mark, circular, transparent) pre-cached in `sw.js` - not inline base64.

This REPLACED and retired: the green `FLYTIME` bottom banner (`flyTimeBannerHTML`/`.flytime-banner`), the green `FlyTime` results pill (`.fly-stamp`), and the old SupaFly “FlyMatch” corner badge (`fm-stamp`, was driven by `isFlyMatch`). `buildMarkers` is now rivalry-skull-only. Per the locked spec, FlyTime on a card is communicated by the fly icon ONLY - no text labels, banners, ribbons, pills, extra badges, or extra borders.

### FlyTime Engine v1 (primary yellow-fly predictor, Jun 2026)

For **45 of 48 feeds**, the yellow fly is driven by offline research tables (`*-flytime-v1.json`), keyed in `FLY_V1_REGISTRY`. Each league has a calibrated threshold (typically 65-98). Formula: `close*0.35 + form_balance*0.25 + margin_balance*0.25 + matchup*0.15`. Tables built from ESPN historical scoreboards via `scripts/build_flytime_v1.py` / `scripts/calibrate_flytime.py`. Cricket feeds use live `isFlyTime` rules only.

Tune per-league thresholds using **FlyTime Lab** (`?flylab=1` once; persists as `scorefly_fly_lab`). The lab shows yellow/green/red/blue counts per league and suggests threshold adjustments.

### FlyTime 2.0 - predictive "Likely" layer (the flashing green fly, v131)

An EARLIER, probabilistic green signal that sits in front of the proven Confirmed gate. **Confirmed FlyTime is unchanged** (`isFlyTime`/pinned -> solid green fly, greens the card, red fly on Results, alerts). FlyTime 2.0 adds a 0-100 **FlyTime Index** per live match from four parts: lead-safety deficit (lead vs time left), FlySense momentum pressure (trailing side surging / leader collapsing), margin closing-rate, and the pre-match yellow rating. The index is EMA-smoothed (`FLY2_ALPHA`) and gated with hysteresis + a sustain so it never flickers.

**Decision (this is the locked behaviour):** when a match crosses INTO the **Likely** band it shows the **flashing green fly**; if it drops back below the exit band the fly turns off again. So: enter Likely -> flash on; leave Likely -> flash off; reach Confirmed -> firms to solid green.

- Per-sport bands in `FLY2[sportKey]` (`enter`/`exit` with hysteresis, plus `fp`/`dsec`/`unit`/`exp` window params; soccer/baseball/AFL/NRL have their own clock handling).
- **Asymmetric sustain (v134):** `FLY2_SUSTAIN_ON_MS` (4s) - index must hold above `enter` this long before Likely turns **ON** (fast, so the fly appears soon after a match enters Likely). `FLY2_SUSTAIN_OFF_MS` (16s) - index must then hold below `exit` this long before Likely turns **OFF** (slow, so the fly does not flicker away on a brief dip). Tracked via `ft2AboveSince` / `ft2BelowSince`. (Earlier a single 16s `FLY2_SUSTAIN_MS` gated ON only and OFF was immediate at the `exit` band.)
- Functions: `fly2Window` / `fly2RawIndex` / `updateFlyTime2(m)` (called every poll right after `updateFlyState`, so it reads fresh FlySense), `flyTimeLikely(m)` (true when `ft2Likely` and not yet Confirmed -> drives the flashing fly in `flyTimeIcon`). State on `flyState[id]`: `ft2Index`, `ft2Likely`, `ft2AboveSince`, `ft2Stage` (`none`/`potential`/`likely`/`confirmed`).
- A "Potential" band (`FLY2_POTENTIAL`) is computed for shadow logging only - parked, never user-facing.
- Lab: `ledgerLikely` stamps the first time a match reaches Likely (`l2`/`l2t`) so lead-time vs the Confirmed gate is measurable; `fly2DebugHTML` shows "FT2 <index> <Stage>" on live cards when `DEBUG_FLY`/`?flylab=1`. Likely/flashing-green alone does NOT count as a confirmed green in ledger stats.
- Full spec: `_research/FlyTime-2.0/`.

### Legacy FlyMatch predictor (`computeFlyMatch`) - cricket fallback

Rebuilt in **v78** as a **close-game-led** model; the old popularity / team-quality / rivalry model was scrapped. A yellow fly now means “this upcoming game is likely to be CLOSE”, NOT “these teams are famous”. Runs every sweep on `ALL_UPCOMING` (+ `ALL_LIVE`), reads only fields already on the match (no extra network), sets `m.flyMatchRating` (0-100) and `m.isFlyMatch`.

**Factors** (weighted base; skip-on-null renormalises, so thin data is not scored as 0):

- **close (45)** - the dominant signal. Each side’s close-game profile from its recent final margins (`fmCloseProfile` = `0.7*closeRate + 0.3*tight`, needs >=3 margins or returns null), blended `0.5*avg + 0.5*min` (lean on the lower side: if one team blows everyone out, the game probably will not be close).
- **competitiveness (30)** - `max(0, 1 - |homeWin% - awayWin%| / FLYMATCH_COMP_GAP)` (gap = 0.5), or a rank-gap fallback. v80 sharpened this from the old `1 - gap`, which compressed every game into 0.6-1.0 and could never pull a rating down (the cause of the original over-flagging).
- **form (10)** - `fmFormScore`, minor.
- **importance** - ADDED on top, never averaged: `+ m.fmImp * FLYMATCH_IMPORTANCE_BONUS` (10). (Averaging a mostly-0 importance term was the v67 bug that capped every regular game.)

**Margins are the unlock (v78):** `parseTeamForm` already fetched each team’s season schedule for the W/D/L form dots; it now keeps the final-score margins too (last 10) at zero extra network. NRL margins come via `loadRugbyLeagueForm`. Form cache schema is `scorefly_form_cache_v5` (`{t, f, m:margins}`); it self-heals on first load post-deploy.

**Data-aware threshold (v80 hard gate -> v83 two-tier).** A “likely close” claim needs margin history, so the bar depends on whether we have it:

- **Both teams have margins** -> bar = `FLYMATCH_THRESHOLD` (62). Full close-led confidence.
- **Margins missing** -> bar = `FLYMATCH_THRESHOLD_NODATA` (82). Can only lean on competitiveness (weak), so the bar is much higher: only very-even matchups (and finals, via the importance bonus) flag. A conservative trickle - never the old flood, never a hard zero.

History of this dial (so we do not repeat it): pre-v78 the model was popularity-led and flagged almost everything. v80 added a HARD gate (no margins on both teams = never flag) plus sharper competitiveness. That over-corrected to **zero** yellow flies, because per-team margin data turned out not to load reliably (see KNOWN ISSUE). v83 replaced the hard gate with the two-tier threshold above so the feed is never empty regardless of data state.

**Tuning dials:** `FLYMATCH_THRESHOLD` (62; lower = more flies when margin data is present), `FLYMATCH_THRESHOLD_NODATA` (82), `FLYMATCH_COMP_GAP` (0.5; lower = punishes mismatches harder).

**KNOWN OPEN ISSUE - margin data may not be loading.** The whole model leans on `m.homeMargins`/`m.awayMargins`, set by the async per-team schedule fetch (`loadTeamForm` -> `fetchTeamForm` -> `parseTeamForm`). This has NEVER been confirmed to work on a live day. v83 added a **“Margin data ready for X of Y upcoming games”** readout to the FlyTime accuracy ledger (Teams tab): if X is low, few/no yellow flies is a DATA problem (schedules not loading), not a threshold one. That number is the first thing to read on a match day before any further tuning.

### FlyTime ALL (notifications)

Two opt-ins share one dedupe set (`flytimeAlerted`, persisted to `scorefly_flytime`) so a match alerts at most once when it first crosses INTO Fly Time:

- **Team alert** — a followed team with the bell on. Copy: “🪰 FlyTime” / “Your team is in a close finish” + score line.
- **FlyTime ALL** — global toggle on the Teams tab (`scorefly_flytime_all`, default off; migrates legacy `scorefly_flytime_buzz`), fires for ANY live match. Copy: title “FlyTime ALL”, body “X vs Y has entered FlyTime” / “N games have entered FlyTime”.

Score lines use Fly Mode 3-letter codes (`abbrev`). Sending is **debounced**: `fireFlyTimeAlert` queues; `flushFlyTimeAlerts` sends ~1.2s later (v53).

- **Batching** — several matches crossing in one poll collapse into one summary alert: “🪰 FlyTime / N games worth watching / Open ScoreFly”.
- **Cooldown** — after 3 alerts in 15 minutes (`flyAlertTimes`), everything batches into summaries until the window clears.
- **No exit alert** — fires only on entry, never when Fly Time ends.
- **Tap** — `flyTimeNotifClick` focuses the app and switches to Feed; service worker `notificationclick` handles taps when the app was in the background or closed.

Delivery uses page-context `new Notification` (reliable while the app is open or backgrounded). True closed-app background push needs a service-worker push subscription — not built; native-track item.

### “Worth watching now” feed section (v52)

When any live game is in Fly Time, `renderHome` lifts those matches out of the live list into a pinned green-headed section (`#flytime-section` / `#flytime-cards`) at the top of the Feed. Hidden entirely when nothing is in Fly Time. Also the FlyTime ALL tap destination. The section is feed *organisation* and is kept; its cards are built by `buildLiveCard`, so each now carries the green fly icon in the corner (v66) - the old per-card `🪰 FLYTIME` badge (`flyTimeBannerHTML`) was retired.

### After-match Fly stamp (v54)

Every match the app observes entering Fly Time is recorded id->timestamp in `flyTimeMatches` (`scorefly_flytime_matches`), pruned past 35 days. When such a match appears on Results, `buildResultCard` shows the **red fly icon** in the corner (`flyTimeIcon(m,'result')`, v66 - replaced the green `.fly-stamp` text pill). The match id is the ESPN event id, stable from live to final. Limitation: only stamps matches the app actually watched go live (not retroactive, per-device) - full historical stamping is the parked FlyTime learning system (native track).

### FlyTime Lab (v97+, production via `?flylab=1`)

The Teams tab carries a **FlyTime Lab** dashboard (`renderFlyDashboard`, store `scorefly_fly_ledger_v1`). **`DEBUG_FLY = true` during pre-release testing** (lab always on + internal flyscore readout on every card); set `DEBUG_FLY = false` only when explicitly clearing testing UI for public release. When debug is off, enable the lab via `?flylab=1` once (persists as `scorefly_fly_lab`). Per match it records whether it was PREDICTED FlyTime-worthy (yellow, via `ledgerPredict` in `computeFlyMatch`) and whether it actually REACHED FlyTime live (via `ledgerAchieved`, called from `updateFlyState` when `isFlyTime` fires). `flyLedgerStats()` returns `{predicted, achieved, hit, total, falseAlarm, missed}`; reset via `resetFlyLedger()`. v83 added a **“Margin data ready for X of Y upcoming games”** line to this panel (predictor-input health - see FlyMatch KNOWN ISSUE).

**Fly naming:** yellow = upcoming prediction, green = live FlyTime, red = finished after FlyTime, blue = diagnostic Y→G hit (lab only). Per-league stats via `flyDashboardPerLeague()`; tune thresholds in `FLY_V1_REGISTRY`.

**Live verification (ongoing):** watch close finishes with the app open. Prior ledger runs read **predicted=many / reached=0**; and zero red flies have ever appeared. Red flies, the ledger “reached” count and FlyTime ALL all fire from one place - `isFlyTime(m)` returning true during a live poll - and that has apparently never happened. The code path is wired correctly and the fields it needs (`period`, `clockSec`, `hInt`, `aInt`) are populated, so the most likely cause is that detection only fires while the app is **open and actively polling during a game’s final minutes** (iOS suspends backgrounded web apps). It has never been confirmed against a real live close finish. **Until detection is confirmed working, the ledger cannot validate the yellow predictor (every prediction looks like a false alarm), so threshold tuning is blind.** Top priority is to watch one close finish with the app open and confirm a green fly appears live and a red fly on Results after.

### Functions / where to look

`clockToSec`, `detectOT`, `isFlyTime`, `momTier`, `resolveSide`, `updateFlyState(m)`, `getFlyClass(matchId, side)`, `getMatchFly(matchId)`. FlyTime icon: `flyTimeIcon(m, status)` (the coloured fly), `computeFlyMatch(m)` (close-led predictor; sets `flyMatchRating`/`isFlyMatch`, drives yellow; calls `ledgerPredict`). Predictor inputs: `fmCloseProfile`, `fmWinPct`, `fmFormScore`, `fmImportanceScore`; margins from `parseTeamForm` / `loadTeamForm` / `loadRugbyLeagueForm`. Status classification: `espnStatus(comp)` (uses ESPN `status.type.state` = pre/in/post; v82) and `pruneResultsOfLive()` (no match in both live + results). Ledger: `ledgerPredict` / `ledgerAchieved` / `flyLedgerStats` / `renderFlyLedger` / `resetFlyLedger`. Notifications: `fireFlyTimeAlert` (queues), `flushFlyTimeAlerts` (batches + sends), `flyTimeNotifClick` (tap target). After-match stamp: `markFlyTimeMatch` / `matchHadFlyTime`. (`buildMarkers` was removed in v78 with the rivalry system; `markerHTML` kept for the fly icons.) Live match objects carry `period`, `clockSec`, `clockRaw`, `isOT`, `hInt`, `aInt`. `applyScoreFlashes(newLive)` flashes changed cells, calls `updateFlyState`, and prunes state for matches no longer live - runs every poll.

### Status

- **Solid:** 8-state colour system, momentum/hysteresis, comeback + cold, Fly Time + Overtime, FlyTime alerts (batching + cooldown + tap-to-section, v53; toggle renamed FlyTime ALL v77), pinned “Worth watching now” feed section (v52), after-match recording (v54), FlyTime coloured-fly indicator (green/yellow/red, fixed corner, own system, v66), `computeFlyMatch` close-led predictor (v78, data-aware threshold v83), Fly Mode rendering (Split Tiles layout with per-side state washes, v58), NRL support.
- **Needs live testing (top priority):** FlyState momentum thresholds are reasoned defaults. More urgently, the FlyTime fly-icon + detection system has never been seen against a real live close finish - green has never appeared live and the ledger “reached” / red-fly count sits at zero (see ledger section). Confirm green appears live, red on Results, and read the v83 “Margin data ready for X of Y” line to learn whether yellow-fly data is even loading. Yellow frequency dials: `FLYMATCH_THRESHOLD` (62), `FLYMATCH_THRESHOLD_NODATA` (82), `FLYMATCH_COMP_GAP` (0.5).
- **Predictor (close-led since v78):** `computeFlyMatch` predicts “likely to be close” from recent margins + competitiveness + form, with a data-aware threshold (v83). It can only be validated once live detection is confirmed working. Still parked for the native/back-end track: a true play-by-play FlyTime *learning* system and retroactive historical stamping.
- **Permanently blocked by ESPN data:** Must Watch (80-point threshold unreachable), Gold Glow.
- **Bucket 2 (needs data not pulled):** true possession/xG momentum, win probability.
- **Bucket 3 (out of scope):** any server/back-end engine — incompatible with single-file architecture.

-----

## Rivalries (REMOVED v78)

The hand-curated rivalry system was deleted entirely in v78 (JRod: “rare, just there for the sake of it”). Gone: `RIVALRIES_RAW`, `RIVALRIES`, `RIVAL_PAIRS`, `isRivalryMatch`, `rivalNamesOf`, `m.isRivalry`, the FlyMatch rivalry bonus, the rivalry **skull marker** (`buildMarkers` removed; `markerHTML` kept for the FlyTime fly icons), the onboarding rivals-first slot (now “biggest names in the same league”), and the dead `.fm-skull` CSS. `normTeamName` / `nameTouches` were kept (used by `isMajorClub`). `rivalry_skull.png` was never in the repo. Do not reintroduce rivalries without a fresh decision.

-----

## Data layer (48 feeds, ESPN unofficial API)

No API key. Fetched direct from the browser via rotating CORS proxies. **ESPN-only doctrine. No mock data.** `ALL_LIVE`, `ALL_UPCOMING`, `ALL_RESULTS` start empty.

### Request window

Each feed fetched with `?dates=YYYYMMDD-YYYYMMDD` (ESPN returns the whole range in one request, so window size affects payload size, not request count).

**Two-tier windows (v48).** The full sweep fetches a *deep* window (`WIN_MINE_BACK`/`WIN_MINE_FWD` = 30/30 days) only for feeds that contain a followed team, and a *lean* window (`WIN_ALL_BACK`/`WIN_ALL_FWD` = 7 back / 14 ahead) for every other feed. Which feeds are “deep” is recomputed each sweep by `followedFeedSlugs()`, which maps each followed team’s full league name to its feed code via `FEED_LEAGUE_NAME` (a followed team stores its league as e.g. “Premier League”; the feed code is “EPL”). Matching is accent/space-insensitive (`leagueNorm`) so e.g. “Super Lig” still resolves.

The store caps (`MAX_UPCOMING_MS`/`MAX_RESULTS_MS`) hold up to the deep 30-day window; the **display layer** trims to the view: All shows 14 days upcoming / 7 days results, My Teams shows 30/30 (`renderHome`/`renderResults`). Fast lane: narrow 1 back to 1 ahead, live feeds only.

### Smart proxy rotation (`espnFetch`, `tryProxy`, `bestProxyIdx`)

Proxies: `corsproxy.io`, `allorigins`, `codetabs`, `thingproxy`, plus direct. `espnFetch` tries the last-good proxy alone first (4.5s timeout); only if that fails does it race the rest (8s) and adopt whichever wins. Healthy state = one request per feed. `bestProxyIdx` is in-memory.

### Tiered polling (`pollTick` / `scheduleNextPoll`)

Single self-rescheduling loop — no overlapping intervals. `scheduleNextPoll` picks the delay by priority (first match wins):

- `RETRY_POLL` = 8s — after a failed cycle (highest priority)
- `FLYMODE_POLL` = 1.5s — Fly Mode is open (fastest live refresh)
- `FLYTIME_POLL` = 2s — a live match is currently in Fly Time
- `FAST_POLL` = 2.5s — any game is live (live feeds only)
- `SOON_POLL` = 15s — nothing live yet but a match starts soon
- `SLOW_POLL` = 60s — nothing live: full sweep to catch kickoffs
- `FULL_EVERY` = 8 fast cycles (~20s) — full sweep even while live, to catch kickoffs/finishes

`visibilitychange` triggers immediate poll on returning to app. (`config.py` mirrors these names for the offline scripts only and may drift from the JS — the JS values above are authoritative.)

### Freshness signal

“Updated just now / X mins ago” line at top of Feed (`renderFreshness`, `lastUpdateMs`). Turns amber with “reconnecting” on failed cycle. Fixed red `conn-banner` for total outage.

### Live / finished classification (`espnStatus`, v82)

`espnStatus(comp)` decides live / finished / upcoming. **v82 rewrote it to trust ESPN’s authoritative `status.type.state` (`pre` / `in` / `post`)** instead of matching a short allowlist of status NAMES and falling back to “start time has passed = finished”. The old logic caused two bugs: NRL games went straight to “finished” the moment they kicked off (their `STATUS_FIRST_HALF` / `STATUS_SECOND_HALF` names were not on the allowlist), and a game at tip-off briefly showed as both live and finished (a scheduled game whose start time had just passed was mis-stamped finished at 0-0). The name/time logic remains only as a fallback when `state` is missing. v82 also added `pruneResultsOfLive()` (called in both the full sweep and fast lane) so a match can never sit in `ALL_LIVE` and `ALL_RESULTS` at once.

### Leagues (48 ESPN feeds, 25 countries + global)

`ESPN_FEEDS` in `index.html` is authoritative; this list mirrors it. By country:

**England (5):** Premier League, Championship, League One, League Two, Women’s Super League
**Spain (1):** La Liga
**Germany (1):** Bundesliga
**Italy (2):** Serie A, Serie B
**France (2):** Ligue 1, Top 14 (rugby union)
**Netherlands (1):** Eredivisie
**Portugal (1):** Primeira Liga
**Scotland (1):** Scottish Premiership
**Turkey (1):** Süper Lig
**Belgium (1):** Belgian Pro League
**Switzerland (1):** Swiss Super League
**Greece (1):** Greek Super League
**Russia (1):** Russian Premier League
**Saudi Arabia (1):** Saudi Pro League
**China (1):** Chinese Super League
**Japan (1):** J1 League
**Brazil (1):** Brasileirao
**Argentina (1):** Liga Profesional
**Mexico (1):** Liga MX
**Ireland (1):** League of Ireland
**India (2):** ISL Football, Indian Premier League (cricket)
**South Africa (1):** PSL Football
**Australia (5):** AFL, NRL, NBL, Big Bash League (cricket), A-League
**USA (8):** NFL, NBA, MLB, NHL, MLS, WNBA, NCAAM (men’s college basketball), NCAAF (college football)
**Canada (1):** CFL
**Global / multi-nation (5):** UEFA Champions League, UEFA Europa League, Copa Libertadores, ICC Cricket (feed `23694`), United Rugby Championship

**By sport:** soccer 32, basketball 4 (NBA, WNBA, NBL, NCAAM), American football 3 (NFL, NCAAF, CFL), cricket 3 (BBL, IPL, ICC), baseball 1 (MLB), hockey 1 (NHL), Australian football 1 (AFL), rugby union 2 (URC, Top 14), rugby league 1 (NRL) = **48**.

The searchable follow list holds the teams/players for these feeds. See `ESPN_FEEDS` in `index.html` for the authoritative 48-feed list. (Tennis, Six Nations, Super Rugby Pacific, Copa do Brasil, Pakistan Super League and SA T20 appeared in earlier discovery notes but are NOT in the current feed set.)

### Confirmed NOT viable (do not retry)

NASCAR (`nascar-cup-series` dead, removed v22). Cricket junk IDs `8039 / 19429 / all / 8047`. `soccer/all` works but groups everything — unused. BBL `cricket/8044` is Dec-Jan only.

-----

## AFL team names + Fly Mode codes

`AFL_TEAMS` + `aflTeam(name)` maps ESPN’s inconsistent raw names to proper club names (cards) and 3-letter TV codes (Fly Mode). Matched by distinctive substring, most-specific-first. Needs live verification on an AFL match day.

## NRL team names + Fly Mode codes

`NRL_TEAMS` — same pattern as AFL. 3-letter codes for Fly Mode.

-----

## Team name consistency rule

All team names in `TEAMS` (the search/follow list) must use **full official names** (e.g. “Manchester United” not “Man United”, “Wolverhampton Wanderers” not “Wolves”, “Melbourne Demons” not “Melbourne”). (The rivalry system that also depended on exact name matches was removed in v78.)

**Display-only short names (v55):** a few long AFL/NRL names are shortened *on cards only* via `displayTeamName(name)` (Nth Melbourne Kangaroos, NQ Cowboys, GWS Giants, St George Ill Dragons). The canonical `m.home`/`m.away` stay full, so `teamMatch` (which substring-matches), rivalry detection, Fly Mode codes, and saved favourites are unaffected. Never shorten the canonical name — `teamMatch` would stop matching saved favourites.

-----

## Design system

Pure black `#000000` everywhere. No dark grey, no gradients.

|Token                             |Value                   |Use                             |
|----------------------------------|------------------------|--------------------------------|
|`--bg`                            |`#000000`               |Background                      |
|`--card`                          |`#111114`               |Card fill                       |
|`--card2`                         |`#1c1c1e`               |Secondary surfaces              |
|`--live`                          |`#06f03c`               |Live cards, brand green, FlyTime|
|`--upcoming`                      |`#ffd60a`               |Upcoming cards, warming         |
|`--result`                        |`#ff453a`               |Result cards, on fire           |
|`--onrun`                         |`#ff9f0a`               |FlyState on a run               |
|`--comeback`                      |`#bf5af2`               |FlyState comeback               |
|`--cold`                          |`#409cff`               |FlyState gone cold              |
|`--blue`                          |`#0a84ff`               |Dropdowns                       |
|`--text` / `--text-2` / `--text-3`|white / 80% / 40%       |Text tiers                      |
|`--sep`                           |`rgba(255,255,255,0.08)`|Dividers                        |

**Typography:** Inter (Google Fonts) + `-apple-system` fallback, loaded via `<link>` + `preconnect` in `<head>`. **Fly Mode text uses Overpass** (free, Interstate-style highway font from Google Fonts, loaded in the same `<link>`) at weights 800-900 for across-the-room legibility (v79); chain is `'Overpass', 'Inter', monospace`, so it falls back to Inter offline.
**Wordmark:** “Score” white + “Fly” green, with a circular fly mark (sizes were tightened in the v69-v74 / v76 pixel-match pass).
**Logo fallback:** sport icon only when no crest (`logoImg` derives `emoji.split(' ')[0]`).
**Orientation (v81):** the tab pages are **portrait-only** - a `.rotate-lock` overlay (“Rotate to portrait”) covers Feed/Results/Teams in landscape on phone-sized screens (`@media (orientation: landscape) and (max-height: 500px)`), sitting BELOW the Fly Mode overlay (z-index 150 < 200) so Fly Mode stays the one landscape view. iOS cannot be force-rotated, so this is block-and-prompt.
**Live timers (v81):** period labels use proper terminology per sport (Q1-Q4, H1/H2 for college basketball + NRL, P1-P3 hockey, innings for baseball, OT) via `espnTimer`’s `pLabel` map with a sport-based fallback; both timer boxes (feed LIVE pill, Fly Mode pill) are `text-transform: uppercase` so e.g. “Btm 3” renders “BTM 3”.
**Fly Mode match separators (v81):** between-match dividers use `--fly-sep` (`rgba(255,255,255,0.25)`), deliberately stronger than the within-match seam (`0.12`), so side-by-side games read as separate boards.
**Principles:** no grey/gradients; minimal CSS-only motion; intentionality test — does it help get a score in under 3 seconds?

-----

## Hard rules — do not violate

1. **iOS Safari Unicode crash.** ASCII-only inside `<script>`. Never use em dash U+2014, en dash U+2013, box drawing U+2500-U+257F, minus U+2212, plus-minus U+00B1. HTML/CSS fine; emoji in JS strings fine. Check every release:
   
   ```js
   const bad = [...script].filter(c => [0x2014,0x2013,0x2550,0x2500,0x00b1,0x2212].includes(c.charCodeAt(0)));
   console.log('Dangerous unicode:', bad.length); // must be 0
   ```
1. **Page order:** `page-home` > `page-results` > `page-settings`; `results-cards` inside `page-results`.
1. **Init:** never `document.createElement` in a root IIFE; defer inside `setTimeout(...,0)`.
1. **Single file:** all CSS/JS inline. No splits, build steps, or npm.
1. **No mock data.** ESPN only.
1. **Permanently removed:** score worms (v20), card expand/collapse (v20), UFC/PGA/F1 (v23), GAA (no API), stat ticker/form strip (dropped permanently). Do not reintroduce.
1. **FlyTime indicator is the coloured fly only (locked spec, v66).** FlyTime status on a card is shown ONLY by the green/yellow/red fly icon in the fixed top-right slot. No FlyTime text labels, banners, ribbons, pills, extra badges, or extra borders. The fly icon is the entire FlyTime card language. FlySense score colours and the status borders are SEPARATE systems - do not merge or touch them when working on the fly icon.

-----

## Deployment (GitHub Pages, edit-on-phone)

Repo files: `index.html`, `sw.js`, `manifest.json`, `icon192.png`, `icon512.png`, `icon-*.png` (per-sport fallback icons), `fly-green.png`, `fly-yellow.png`, `fly-red.png`, `knob.png` (brightness slider), `onboard-hero.png`, `onboard-notif.png`, `supafly-*.png`, `team-halo-config.json`, `*-flytime-v1.json` (45 league tables), `scripts/` (FlyTime build/calibration tools), `README.md`, `NOTES.md`, `SCOREFLY.md`, `VERSION HISTORY.md`, `CNAME`, `.nojekyll`.

Steps: edit in GitHub web UI, commit, wait ~30s for Pages rebuild, refresh on phone. **Every deploy that touches HTML/CSS/JS/icons: bump `CACHE` in `sw.js` to a higher number.** Current: **`scorefly-v134`**. For an installed PWA, removing + re-adding the Home Screen icon forces a stale cache to clear.

-----

## Open items

**Backlog (JRod’s full item list - all 17 dispositioned)**

*Numbering note:* these are JRod’s working item numbers, not unique IDs - “1” is reused (live-first ordering AND the sticky FlyTime pin) and the rejected set ran long. Treat the description as the key and the number as a loose label. (Code comments such as “Item 16” point back to this list.)

*Built (v96):*

- **(4) Auto-clear search box after add** - built: clears search after add; results list stays for multi-add.
- **(7) Tab memory** - built: `scorefly_last_tab` restores last tab for returning users.
- **(5) Six suggested teams** - built v67 (`onbGetSuggestions`); rivals-first slot dropped v78.
- **(15) Pull-to-refresh** - built on Feed and Results.
- **(16) Clean global LIVE indicator** - built v96: `#global-live` header pill on all tabs when any game is live; tap jumps to Feed.
- **(17) Last-scores cache** - built: `saveSnapshot` / `hydrateSnapshot` instant boot paint (6h / 15 min TTLs).
- **(1) Sticky FlyTime pin** - built with blowout buffer v96 (`FLY_BLOWOUT_MARGIN` unpins blowouts; after-match stamp kept).
- **(14) Per-team quick-add** - built v96: circular `+` on cards, search, onboarding picks, suggested teams.
- **(2) Onboarding polish** - built v96: progress dots, hero caption, notifications headline.

*Keep / verify only, no build (6):*

- **(1) Live-first ordering**, **(3) FlyTime as supporting intelligence** (not the headline), **(8) Results screen** as-is, **(9) upcoming-in-feed sort**, **(10) current FlyTime visuals** (now the coloured fly, v66), **(11) current FlyTime ALL**. All confirmed good; just verify on a live day.

*Rejected (do not revisit):*

- 2-screen onboarding (keep 4 screens), inline “Added” tick, separate Upcoming screen, FlyTime visual teardown, confidence tiers, activations counter, 5-tab nav (nav stays locked: Feed / Results / My Teams + the Fly Mode button).

*Design-first tasks:* All built in v96.

*Settled sub-points:*

- **Blowout buffer (1) - SETTLED v96.** Unpin when margin exceeds `FLY_BLOWOUT_MARGIN`; stamp retained.
- **“State” data location (5) - SETTLED.** Lives in `METRO_TEAMS` (a side-car name->metro map), not on the `TEAMS` strings. `teamState(item)` reads `item.state` then `TEAM_METRO[item.name]` (exact-name, city granularity). Only multi-sport metros are tagged; everything else falls back to country.

**Verify on live match days**

- **FlyTime detection (TOP PRIORITY, never confirmed live):** watch one close finish with the app open - confirm a green fly appears live and a red fly on Results after. The ledger “reached” / red-fly count has only ever been 0; until this works the yellow predictor cannot be validated.
- **Margin-data coverage:** open the Teams tab on a match day and read the “Margin data ready for X of Y upcoming games” line. Low X = the per-team schedule fetch is not loading (a data bug); high X = it loads and yellow tuning is a threshold job. This decides what to fix next.
- Yellow-fly frequency: tune `FLYMATCH_THRESHOLD` (62), `FLYMATCH_THRESHOLD_NODATA` (82), `FLYMATCH_COMP_GAP` (0.5) once the above two are understood.
- Tiered polling: live scores refresh ~12s, kickoff appears within ~3 min, finish moves to Results, idle load unchanged.
- Proxy rotation: scores load reliably, recover when a proxy dies.
- AFL: proper names + TV codes resolve correctly; NRL same.
- Soccer feeds: `ind.1`, `rsa.1`, `conmebol.libertadores` confirm data returns.
- FlyState momentum thresholds per sport — tuning is the main remaining task.

**Product**

- Placeholder/TBD fixtures (e.g. “Spurs/Thunder” before a playoff series): render cleanly but have no real teams. Open question: hide or keep?
- iPad/tablet layout unchecked. PWA install on Android untested.
- Men's **NBL** (Australia) is live (`basketball/nbl`). **WNBL** (Australian women’s basketball) is not in the app at all - no entry in `LEAGUES`/`TEAMS`/feeds, so it is not searchable. Adding it is a new-league task (needs a working ESPN endpoint - ESPN coverage of WNBL is unconfirmed - plus a team list), not a search-index fix.

**Optional code cleanup (low priority)**

- `fetchTeamForm` has its own near-duplicate fetch logic; could be unified with `espnFetch`/`tryProxy`.
- Persist `bestProxyIdx` to localStorage so cold loads start with a known-good proxy.

-----

## Decisions log

|Decision                       |Outcome                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
|-------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
|Onboarding recommendations     |Anchor team -> 6 picks: 2 Local (same metro, different league), 2 Same country (different sport, household names), 2 Same league (biggest names; rivals-first dropped v78); 4 country / 2 league fallback when no metro. Pure client function over the in-memory team list - no backend, no DB, no caching (746 teams = instant).                                                                                                                                                                                                                 |
|Team geo data                  |Stored in a `METRO_TEAMS` side-car (name->metro), NOT on the `TEAMS` strings. Only multi-sport metros tagged (US/CA/AU/NZ); Positions 1-2 are effectively a US+AU feature, elsewhere falls back to country. Metro/city granularity, not state (state too broad).                                                                                                                                                                                                                                                                                  |
|Onboarding screen              |Single hero/splash (`onboard-hero.png`) -> “Choose My Teams” -> team picker -> notifications. CODED v68. Supersedes the 4-screen flow (welcome + Meet FlyTime retired). Teams followed bell-off; notifications step turns alerts on for all followed teams when granted.                                                                                                                                                                                                                                                                          |
|FlyMatch predictor (yellow fly)|Close-game-led since v78 (popularity/quality/rivalry model scrapped): close-margin profile (45) + competitiveness (30) + form (10), importance added on top. v80 added a hard “both teams need margins” gate + sharper competitiveness; that over-corrected to ZERO flies because margin data does not reliably load, so v83 replaced it with a two-tier threshold (62 when both teams have margins, 82 when missing) - never a flood, never a hard zero. Dials: `FLYMATCH_THRESHOLD` 62, `FLYMATCH_THRESHOLD_NODATA` 82, `FLYMATCH_COMP_GAP` 0.5.|
|FlyTime accuracy ledger        |Teams-tab panel (v77) logs predicted vs reached FlyTime; v83 added a “margin data ready for X of Y” input-health line. Cannot validate the predictor until live detection is confirmed (reached/red flies stuck at 0).                                                                                                                                                                                                                                                                                                                            |
|Live/finished classification   |`espnStatus` trusts ESPN `status.type.state` (pre/in/post) since v82, not status names + start-time guessing. Fixed NRL-instantly-finished and the live+finished dual-listing. `pruneResultsOfLive` guarantees no match in both lists.                                                                                                                                                                                                                                                                                                            |
|Fly Mode font                  |Overpass (free Interstate-style highway font, Google Fonts), weights 800-900, for across-the-room legibility (v79). Chain falls back to Inter offline.                                                                                                                                                                                                                                                                                                                                                                                            |
|Live timer terminology         |Proper per-sport period labels (Q/H/P/innings/OT) with a sport-based fallback; both timer boxes uppercased via CSS (v81).                                                                                                                                                                                                                                                                                                                                                                                                                         |
|Orientation                    |Tab pages portrait-only; `.rotate-lock` prompt in phone landscape; Fly Mode is the only landscape view (v81).                                                                                                                                                                                                                                                                                                                                                                                                                                     |
|Fly Mode match separators      |`--fly-sep` (0.25) dividers between matches, stronger than the 0.12 within-match seam (v81).                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
|Background                     |Pure black everywhere                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
|Feed filter default            |All                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
|Upcoming / results windows     |Two-tier (v48): All = 14 ahead / 7 back; My Teams = 30/30, fetched deep only for followed-team leagues                                                                                                                                                                                                                                                                                                                                                                                                                                            |
|Polling                        |Tiered self-rescheduling loop (priority order): 8s after a fail, 1.5s Fly Mode open, 2s a live match in Fly Time, 2.5s any game live, 15s starting soon, 60s idle; full sweep every ~8 fast cycles (~20s) while live                                                                                                                                                                                                                                                                                                                              |
|Auto-retry                     |8s quick retry after a failed cycle                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
|Proxy strategy                 |Try last-good proxy first, fall back to racing; remember winner                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
|Freshness line                 |“Updated X ago / reconnecting” at top of Feed                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
|FlyState                       |8-state colour-fill on live scores + Fly Mode (untouched by v66)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
|FlyTime indicator              |Single coloured fly icon in a fixed top-right slot: green=live in FlyTime, yellow=upcoming predicted (`computeFlyMatch`), red=finished reached FlyTime. Own system; no banners/pills/text/extra borders. Locked spec (v66)                                                                                                                                                                                                                                                                                                                        |
|FlyTime ALL                    |Teams-tab toggle (global) + followed-team alerts; one alert per match on FlyTime entry; debounced batching + 3-per-15-min cooldown; tap opens FlyTime section (v53; renamed from FlyTime Buzz v77)                                                                                                                                                                                                                                                                                                                                               |
|Worth watching now             |Pinned FlyTime section at top of Feed kept; per-card badge replaced by the green fly icon (v66)                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
|After-match indicator          |Result cards show the red fly icon if the app saw the match enter FlyTime; per-device, 35-day prune, not retroactive (v54, icon v66)                                                                                                                                                                                                                                                                                                                                                                                                              |
|Rivalries                      |REMOVED entirely in v78 (data, helpers, skull marker, onboarding slot, FlyMatch bonus). Do not reintroduce without a fresh decision.                                                                                                                                                                                                                                                                                                                                                                                                              |
|Onboarding                     |4-screen FlyTime-led flow with SupaFly: welcome, Meet FlyTime, pick teams, notifications. Complete for V1. (v51)                                                                                                                                                                                                                                                                                                                                                                                                                                  |
|SupaFly mascot                 |Premium concierge guide in onboarding; voice + poses, not childish. PWA uses sheet-cropped poses (v51)                                                                                                                                                                                                                                                                                                                                                                                                                                            |
|Monetisation                   |PWA stays free (no Pro/paywall); monetise on the native track instead (Phase 0 decision)                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
|Suggested for you              |Onboarding-only; hidden permanently after onboarding complete                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
|Team names                     |Full official names throughout the `TEAMS` list (display-only short names on cards via `displayTeamName`, v55)                                                                                                                                                                                                                                                                                                                                                                                                                                    |
|AFL / NRL names                |Proper names on cards, 3-letter TV codes in Fly Mode                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
|Logo fallback                  |Sport icon only when no crest                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
|Font load                      |`<link>` + preconnect in head                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
|Score colours legend           |In Settings                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
|Times                          |User local timezone                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
|Team matching                  |Partial contains                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
|Score worms / expand-collapse  |REMOVED v20                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
|Stat ticker / form strip       |DROPPED permanently                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
|Hosting                        |GitHub Pages                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
|Must Watch / Gold Glow         |BLOCKED permanently — ESPN feed data insufficient                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |

-----

## Version history

**v134** (current) - FlyTime 2.0 "Likely" fly given asymmetric timing: split the single 16s sustain into `FLY2_SUSTAIN_ON_MS` (4s, lowered) so the flashing green fly appears soon after a match enters the Likely band, and `FLY2_SUSTAIN_OFF_MS` (16s) so it must hold below the `exit` band that long before turning off (no flicker). Added `ft2BelowSince` tracking in `updateFlyTime2`. `sw.js` -> v134.
**v133** - Logo library re-encoded to tiny WebP for instant crests. Doc pass: reconciled `SCOREFLY.md` to code (cache v133, feed count 47 -> **48**, real poll tiers, leagues list matched to `ESPN_FEEDS`) and **documented FlyTime 2.0 "Likely"** as the locked behaviour - the flashing green fly turns ON when a live match enters the predictive Likely band and OFF if it drops back out (engine shipped v131; no code change this pass, so cache stayed at the WebP bump). `sw.js` -> v133.
**v132** - Runtime audit quick wins (research basis: `_research/ScoreFly-Audit/`). (1) `FLYMODE_POLL` 1s -> 2s (still reads live, ~half Fly Mode poll cost). (2) `saveSnapshot` throttled to at most once per 20s (`SNAPSHOT_MIN_INTERVAL_MS`) so the live poll loop no longer blocks on a full JSON stringify every tick. (3) Logo contrast probe (`probeTeamLogoContrast` / `sampleLogoStats`) cached by image src for the session - canvas readback runs once per logo, not every card rebuild. (4) Fly Mode favourite filter uses `teamMatch` like the Feed (substring match), so followed teams with ESPN display-name drift still appear on the big screen. **`DEBUG_FLY` stays `true` for ongoing FlyTime/predictor testing** (lab + per-card flyscore overlay); flip to `false` only when explicitly stripping testing UI for release. `sw.js` -> v132. *(Several follow-up commits shipped under the same v132 cache without a bump: stale-refresh false-positive fix + FlyMode ordering + live-refresh reliability, single-match Fly Mode layout tuning for score visibility, double-portrait solo timer, green FlyTime scores in solo, a raised WNBA FlyTime threshold, and a pass keeping FlySense colours and the FlyTime fly visually independent.)*
**v131** - FlyTime 2.0 predictive "Likely" engine + feed density. Added the `FLY2` engine: a 0-100 FlyTime Index (lead safety + FlySense momentum + margin closing-rate + pre-match rating), EMA-smoothed with hysteresis + 16s sustain, surfacing an EARLIER **flashing green fly** when a live match is *Likely* to reach Fly Time (firms to solid green on Confirmed, off if it drops out). `updateFlyTime2`/`fly2RawIndex`/`flyTimeLikely`; lab readout `fly2DebugHTML` + `ledgerLikely`. Also: fixed a blank feed caused by NRL/AFL clock constants being read before definition; polished team/league labels, search UX and Fly Mode chrome; logo data-quality fixes. `sw.js` -> v131. (Behaviour documented in v133.)
**v129** - FlySense 2.0 engine (research basis: `_research/FlySense-2.0/`). (1) Continuous gradient score colours: momentum now maps to a smooth heat ramp (white->yellow->orange->red->ember) set inline per cell via `getFlyStyle`; cold (severity-scaled blue) and comeback (magnitude-scaled purple) get their own intensity ramps; the old `fs-*` classes remain as anchors/semantic hooks and the 67-vs-68 threshold cliff is gone. (2) Soft hysteretic tier bands (onfire 70/64, onrun 45/40, warming 20/16) so labels never chatter. (3) Dynamic decay: per-sport base half-life in `FLY_TUNING` (NBA 40s ... soccer 90s) stretched up to 1.8x by run persistence, onfire cools 1.3x slower / warming 0.8x faster; sub-5 momentum sweeps to 0. (4) Richer scalar: acceleration boost (180s window, recent vs prior half) + slow-decaying recovery "ember" + drought/peak/suppression tracking. (5) Cold gains an absolute-drought trigger (`droughtNorm` per sport) and severity; comeback gains magnitude (deficit scale / recovery fraction / speed / level bonus) with exit hysteresis. (6) Extreme states: `fs-xfire` (mom >= 90, brightening pulse + warm glow) and `fs-xcold` (frozen + drought + dominance: dim/desaturate + frost glow); `prefers-reduced-motion` respected. (7) Cricket momentum is now RUN-RATE based (`updateCricketFly`): batting side on fire at 10+/over (T20) or 6+/over (ODI 50-over) = momentum 70; wicket knocks the rate back 40%; bowling side gains 38/wicket; cold/comeback disabled for cricket; `cricketChaseFields` now also exposes `cricketMaxOvers`/`cricketBatting`/`cricketOvers`. `flyCrossfade` extended to crossfade inline colours. Sanity sim: `scripts/sim_flysense2.py`; JS balance check: `scripts/check_js_balance.py`. `sw.js` -> v129.
**v115** - NBL live feed (`basketball/nbl`) + `nbl-flytime-v1.json`; FlyTime Lab via `?flylab=1`; fly terminology (yellow/green/red/blue); `DEBUG_FLY = false`. `sw.js` -> v115.
**v112** - 13 new ESPN leagues (J1, League One/Two, CSL, Belgian, Swiss, Greek, Serie B, Saudi, Russian, CFL, URC, Top 14) with FlyTime v1 tables.
**v97-v111** - FlyTime v1 engines for all major sports/soccer; tennis removed; StatFly->ScoreFly docs; onboarding redesign; FlyMode up to 8 games; team halos; notification defaults; global LIVE pill; quick-add `+`.
**v96** - Backlog batch: global LIVE pill, quick-add `+`, onboarding polish, FlyTime blowout buffer, `DEBUG_FLYSCORES` off. `sw.js` -> v96.
**v83** — FlyMatch two-tier threshold + margin-data visibility. The v80 hard gate had over-corrected to ZERO yellow flies (per-team margin data does not reliably load), so the gate was replaced with a data-aware two-tier threshold: bar 62 when both teams have margin history (close-led), bar 82 (`FLYMATCH_THRESHOLD_NODATA`) when missing - so very-even matchups and finals still flag (never zero) but average games do not (never the old flood). Added a “Margin data ready for X of Y upcoming games” readout to the FlyTime accuracy ledger and wired it to refresh after each form load, to reveal whether the predictor’s input data is actually loading. `sw.js` -> v83.
**v82** — Live/finished classification fix. `espnStatus` rewritten to trust ESPN `status.type.state` (pre/in/post) instead of a status-name allowlist + start-time guess. Fixed (a) NRL games flipping straight to “finished” at kickoff (their half-based status names were not on the allowlist) and (b) games showing as live AND finished at once around tip-off. Added `pruneResultsOfLive()` so a match is never in both lists. `sw.js` -> v82.
**v81** — Period terminology + uppercase timers + Fly Mode separators + portrait lock. (1) `espnTimer` period labels fixed: WNBA/NCAAF -> Q1-Q4, NCAAM -> H1/H2 (college halves), plus a sport-based fallback so no league shows a bare number; both timer boxes set `text-transform: uppercase` (Btm->BTM, Inn->INN). (2) Fly Mode gains a stronger between-match divider (`--fly-sep` 0.25 vs the 0.12 seam). (3) Tab pages locked to portrait via a `.rotate-lock` overlay on phone-sized landscape; Fly Mode stays the one landscape view. `sw.js` -> v81.
**v80** — FlyMatch gate + sharper competitiveness. Added a hard gate requiring BOTH teams to have recent margin history before flagging (so competitiveness alone could not float every game over the line), and steepened competitiveness via `FLYMATCH_COMP_GAP` (0.5) so real mismatches reach 0. Correct in principle but later proved too strict given flaky margin data (see v83). `sw.js` -> v80.
**v79** — Fly Mode font swapped to Overpass (free Interstate-style highway font, Google Fonts) at weights 800-900 for across-the-room legibility; chain `'Overpass','Inter',monospace`. Fly Mode text only. `sw.js` -> v79.
**v78** — New FlyTime predictor + rivalry removal + onboarding poster swap. (1) `computeFlyMatch` rebuilt as a close-game-led 0-100 model (close-margin profile 45 + competitiveness 30 + form 10, importance additive; popularity/quality/rivalry dropped); margins now captured in `parseTeamForm` + NRL path, form cache `v4 -> v5`. (2) Rivalry system deleted entirely (data, helpers, skull marker, onboarding slot, bonus). (3) Onboarding welcome + notifications screens swapped to new full-bleed posters (`onboard-hero.png` / `onboard-notif.png`). `sw.js` -> v78.
**v77** — FlyTime accuracy ledger (Teams tab, predicted vs reached) and the global toggle renamed “FlyTime Buzz” -> “FlyTime ALL”.
**v75-v76** — UI polish. v75 “Final Touch-Up” (11 items): FlyTime ALL notification copy, Fly Mode mixes in non-followed FlyTime games only when the toggle is on + pins FlyTime games to top, poll tiers 8s FlyTime / 12s live / 30s soon / 60s idle, Fly Mode nav icon +20%, WNBA made searchable (added to USA group). v76: 6 CSS/markup alignment tweaks (freshness band, upcoming-name alignment, league-badge anchor, section-spacing tokens, countdown size, header baseline).
**v69-v74** — Card UI pixel-match phase (logged as one phase): Feed/Results cards matched to reference screenshots by forensic measurement (card gap, height, border, radius, team-name/score/logo/wordmark sizes). **Brand green changed `#30d158` -> `#06f03c`** (all rgba literals swapped).
**v68** — Single-hero onboarding + household-list expansion + local-pick prominence.
**v67** — Onboarding recommendation engine made data-driven + upgraded; yellow-fly calibration fix. (1) Added `METRO_TEAMS` (name->metro side-car for ~45 US/Canada/Australia/NZ multi-sport cities) and `TEAM_METRO` inverted lookup; `teamState` now reads it (exact name, city granularity), so onboarding Positions 1-2 finally fire. (2) Rewrote `onbGetSuggestions` to spec quality: 2 Local (same metro, DIFFERENT league than anchor, distinct leagues, household names first via `isMajorClub`), 2 Same country (different sport, biggest names), 2 Same league (rivals first via `rivalNamesOf`/`RIVAL_PAIRS`), with cascade backfill to always return 6 and a 4-country/2-league fallback when the anchor has no metro. Verified against example anchors (Knicks->Yankees+Rangers, Adelaide Crows->Strikers+United, Lakers->Dodgers+Chargers, Liverpool->Man Utd+Arsenal). (3) Yellow fix: importance was an averaged term scored 0 for every regular-season game, capping marquee matchups below the old 3.5 cutoff -> almost no yellow flies. Importance is now an additive bonus (`FLYMATCH_IMPORTANCE_BONUS = 1.2`), removed from `FLYMATCH_WEIGHTS`; `FLYMATCH_THRESHOLD` lowered 3.5 -> 3.0. No new assets; `sw.js` bumped. Static checks pass (unicode, page order, JS syntax); yellow frequency still wants a live-day glance. NOTE: the single-hero onboarding screen is a design, not yet in code; the engine it feeds is built.
**v66** — FlyTime indicator rebuilt as a single coloured fly icon (LOCKED SPEC). One fly in the fixed top-right corner of every card and Fly Mode: green = live and in Fly Time, yellow = upcoming and predicted (`isFlyMatch` via `computeFlyMatch`), red = finished and reached Fly Time. New resolver `flyTimeIcon(m, status)`; three external PNGs (`fly-green/yellow/red.png`, cropped from the SupaFly mark, transparent, pre-cached in `sw.js`). Retired: the green `FLYTIME` bottom banner (`flyTimeBannerHTML`/`.flytime-banner`), the green results pill (`.fly-stamp`), and the SupaFly “FlyMatch” corner badge (`fm-stamp`); `buildMarkers` is now rivalry-skull-only; the dead banner/pill/`.fly-logo` CSS was removed. FlySense score colours (incl. score-goes-green in Fly Time), the status borders, and the “Worth watching now” section are all UNTOUCHED. Corrected a long-standing doc error: a quality predictor (`computeFlyMatch`) was already live and is what drives yellow. Passes static checks (unicode, page order, JS syntax); wants a live-match-day glance.
**v61-v65** — (off-doc; cache advanced to `scorefly-v65` in code before the v66 session, change details not captured in this log).
**v60** — Branded-asset + icon pass. (1) The fly emoji (stored `\uD83E\uDEB0`) replaced everywhere it was a visible glyph with the circular SupaFly logo (`icon192.png`, new `.fly-logo` class): the FlyTime banner and the after-match Results stamp. The two FlyTime notification titles dropped the emoji (a notification’s text can’t hold an image; the logo already shows as the notification `icon`). (2) Search + onboarding result rows now route the league emoji through `sportImg()` (`buildSearchIndex` meta + both league-row badges), so AFL shows `icon-afl.png` instead of the raw red-circle emoji, and every other sport shows its `icon-*.png`. (3) Two `toggleAlert` notifications and the empty-feed welcome glyph switched from a lightning `\u26A1` to the SupaFly logo. (4) NRL form boxes: `fetchTeamForm` refactored so rugby-league tries the configured league id then the `nrl` slug (other sports unchanged); whether ESPN actually serves an NRL team schedule is still unconfirmed from static testing. Known gaps left as-is (no branded asset exists): `flymatch_stamp.png` and `rivalry_skull.png` are still missing and fall back to text/emoji via `markerHTML` onerror; the bell `\U0001F514` and buzz `\U0001F525` toggle glyphs are functional UI emoji. WNBL is NOT in the data (no league/teams) - see Open items. Static checks pass. (Note: the banner + Results stamp described here were retired in v66.)
**v59** — Fly Mode score sizing reworked to fill the cell in every formation. Each number now grows to a per-formation height budget and only shrinks when its actual digit count (`--len`, set per match in `buildFlyModeGrid`) would overrun that side’s width; `--half-vw` + `--h-budget` are set per orientation and match-count. Fixes the v58 bug where one conservative width cap was applied to all landscape layouts, leaving single-match landscape numbers tiny with large dead space (e.g. a 1-digit score went from ~tiny to ~240px). Fly Mode CSS + `buildFlyModeGrid` only; nothing else touched. Passes static checks; exact sizes are calculated and still want a real-device glance.
**v58** — Fly Mode graphics redesigned as “Split Tiles”. Each match is now two equal half-tiles meeting at a centre seam, with the period/clock floating in a pill on the seam (replacing the old centred-badge-between-scores layout). Each tile fills with a DARK wash of that side’s FlyState colour, driven by the same `getFlyClass()` class as the score number, so wash and number colour always agree; neutral games stay pure black. Scores use tabular figures (no sideways jitter as they tick). A single match in portrait stacks the two tiles top/bottom at full width for a hero-sized number. The old vertical `::before` seam divider (which poked past the badge) was removed. Touch points: `buildFlyModeGrid` (markup) + `.flymode-card` / `.flymode-half` / `.flymode-score` / `.flymode-status` CSS. Fly Mode only; nothing else touched. Passes static checks (unicode, page order, JS syntax); score sizing is a calculated value and still needs a glance on a real device.
**v56-v57** — (off-doc; cache reached `scorefly-v57` in code before the v58 session, change details not captured in this log).
**v55** — Display-only short names on cards for four long AFL/NRL teams (`displayTeamName`); rivalry skull gated to upcoming fixtures only (off on live + Fly Mode, via `buildMarkers(m, {skull:false})`); NRL form boxes enabled by adding `rugby-league` to `FORM_TEAM_SPORTS` (needs live NRL-day verification of the ESPN rugby-league schedule endpoint). Docs corrected (README + this file) re: skull placement.
**v54** — After-match Fly stamp: matches the app sees enter Fly Time are recorded (`scorefly_flytime_matches`, 35-day prune) and stamped on Results via `buildResultCard`.
**v53** — FlyTime Buzz notification redesign: new copy (“🪰 FlyTime” + score line + “Worth watching now” / “Your team is in a close finish”), debounced batching of simultaneous crossings, 3-per-15-min cooldown, tap opens the FlyTime section. Queue/flush split (`fireFlyTimeAlert`/`flushFlyTimeAlerts`).
**v52** — Pinned “Worth watching now” FlyTime section at top of Feed (`renderHome` lifts live Fly Time games out of the live list); scrolling “FLYTIME IN PROGRESS” marquee replaced with a static green `🪰 FLYTIME` badge (feed + Fly Mode).
**v51** — Onboarding redesigned around FlyTime and the SupaFly mascot: 4 screens (Welcome, Meet FlyTime, Pick teams, Notifications); `onbGoStep` hides steps by class and accepts `'fly'`; SupaFly pose PNGs added + pre-cached.
**v50** — ScoreFly rebrand present in code (wordmark, storage keys `scorefly_*`, cache `scorefly-v50`). Details not logged in this doc; predates the v51-v54 session.
**v49** — Intermediate (off-doc; details not captured between the v48 doc update and the v50 code snapshot).
**v48** — Two-tier date windows. All view: 14-day upcoming / 7-day results. My Teams view: 30-day upcoming + results, fetched deep only for the leagues holding a followed team (`followedFeedSlugs`/`FEED_LEAGUE_NAME`/`leagueNorm`). Store caps raised to 30 days; display layer trims per view. Request count unchanged.
**v47** — Team name consistency pass (full official names throughout TEAMS + RIVALRIES). Onboarding suggested teams restructured (3 same city / 3 same country diff sport / 2 rivalry). Suggested for you hidden after onboarding. NHL Arizona Coyotes replaced with Utah Hockey Club.
**v46** — (intermediate cache bump)
**v45** — FlyTime Buzz alerts; adaptive polling dropping to 20s during FlyTime; rivalry skull marker in Fly Mode; AFL TV abbreviations.
**v44/v43** — FlyState V2: momentum threshold re-tune; independent drought-based Blue for basketball and AFL; comeback detection improvements.
**v40–v42** — FlyState V2 group work: basketball possession-model FlyTime; AFL/soccer timing; NRL integration.
**v39** — Data-reliability steps 3–5. Tiered polling; 8s auto-retry; smart proxy rotation; narrow fast-lane window; immediate refresh on returning to app.
**v38** — AFL proper club names on cards + 3-letter TV codes in Fly Mode.
**v37** — Logo fallback fix.
**v36** — 7-day fetch window via `?dates=` range; upcoming filter 14->7 days.
**v35** — Freshness line; removed dead stat-ticker; font load moved to head.
**v26–v27** — Fly Mode redesign; discovery cleanup (removed F1, Golf Majors).
**v20–v25** — Score worms + expand/collapse removed; soccer slugs added (to 36 feeds).

-----

## Parallel track: native app (FlutterFlow)

Separate planned production build in FlutterFlow + Firebase. Reference: `SportsTimeline_FlutterFlow_Guide.docx`. Only relevant when explicitly asked about the native track. Android-first; iOS later via MacInCloud. Costs: Apple $99/yr, Google $25 one-time.