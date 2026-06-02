# StatFly

Mobile-first sports scores app. Pure black UI, Apple-style typography, single self-contained HTML file. Works in any mobile browser, installable as a PWA.

**Tagline:** Scores Anywhere. Simple.
**Brand colour:** `#30d158` (Apple green)
**Current file:** `index.html` (cache `statfly-v39`)
**Live URL:** [hammertymm.github.io/statfly](https://hammertymm.github.io/statfly)
**Repo:** [github.com/Hammertymm/statfly](https://github.com/Hammertymm/statfly)

**This single document is the source of truth. It supersedes and replaces both the old `STATFLY.md` and the retired `SKILL.md` / `StatFly_skill.md`.** Delete those; keep only this.

-----

## How to work on this codebase

Biases toward caution over speed. For trivial edits, use judgment.

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

Follow favourite teams across 36 league feeds; see live scores, upcoming fixtures (next 7 days), and recent results (last 7 days) in one feed. No login, no ads.

|Tab    |Shows                                                                 |
|-------|----------------------------------------------------------------------|
|Feed   |Live matches + upcoming fixtures (next 7 days). My Teams / All toggle.|
|Results|Completed matches (last 7 days). My Teams / All toggle.               |
|Teams  |Follow/manage teams. Global search + Suggested for You.               |

A fourth bottom-nav button opens **Fly Mode**: full-screen live scores for followed teams, for glancing across a room.

-----

## FlyState engine (START HERE for FlyState work)

StatFly’s signature feature: live score cells (and Fly Mode scores) are **colour-filled** to show what’s happening at a glance. Colour is a solid fill (not a glow) so it stays readable when Fly Mode is dimmed. The colour-coded card BORDERS (green live / yellow upcoming / red result) are a SEPARATE system from FlyState score colours.

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

CSS classes `fs-warming / fs-onrun / fs-onfire / fs-cold / fs-comeback / fs-flytime` apply to `.sc` (feed) and `.flymode-score`. Fly Time green pulses (`flyPulse`).

### How it works (derived from score + clock only — no extra feeds)

Per-match: `flyState[id] = { h, a, hMom, aMom, hMaxDef, aMaxDef, hState, aState, match }`.

- **Momentum** 0-100 per side. Each poll: `mom = prev.mom*MOM_DECAY + min(scoreDelta/bigPlay, 1.6)*MOM_GAIN`, clamped. `MOM_DECAY = 0.6` is the anti-flicker (a hot streak cools gradually). `MOM_GAIN = 70`.
- **Per-sport tuning** `FLY_TUNING[sportKey] = { bigPlay, cbMin }`: basketball `{6,10}`, football `{7,11}`, hockey `{2,2}`, soccer `{1,2}`, baseball `{3,3}`, australian-football `{9,18}`.
- **Tiers** (`momTier`): >=68 on fire, >=42 on run, >=20 warming.
- **resolveSide priority:** comeback > onfire > onrun > warming > cold > neutral. Comeback = was down >= `cbMin`, clawed back >= half of max deficit, now within +/-`cbMin`, momentum >= 20. Cold = own momentum < 12 while opponent >= 42.
- **Fly Time** (`isFlyTime`): clock-based per sport (basketball/football: Q4, <=300s, margin <=8; hockey: P3, <=300s, margin <=1; baseball: inning >=8, margin <=2; AFL: Q4, <=360s, margin <=12; soccer: minute >=80, margin <=1). **Tennis and cricket excluded.**
- **Overtime** (`detectOT`): per sport; OT outranks Fly Time.

### Functions / where to look

`clockToSec`, `detectOT`, `isFlyTime`, `momTier`, `resolveSide`, `updateFlyState(m)`, `getFlyClass(matchId, side)` (Fly Time forces both green), `getMatchFly(matchId)`. Live match objects carry `period`, `clockSec`, `clockRaw`, `isOT`, `hInt`, `aInt`. `applyScoreFlashes(newLive)` flashes changed cells, calls `updateFlyState`, and prunes state for matches no longer live — it runs every poll (both lanes).

### Solid vs next

- **Solid:** the 8-state colour system, momentum/hysteresis, comeback + cold heuristics, Fly Time + Overtime, Fly Mode rendering.
- **Next (Bucket 1, from current data):** tune the per-sport thresholds against real live matches; refine Fly Time windows; richer Fly Mode visuals.
- **Bucket 2 (needs data the app does not pull):** true possession/xG momentum, win probability.
- **Bucket 3 (out of scope):** any server/back-end engine — incompatible with the single-file architecture.
- **Thresholds are reasoned defaults, not yet verified on live games.** Tuning is the main FlyState task.

-----

## Data layer (36 feeds, ESPN unofficial API)

No API key. Fetched direct from the browser via rotating CORS proxies. **ESPN-only doctrine. No mock data.** `ALL_LIVE`, `ALL_UPCOMING`, `ALL_RESULTS` start empty.

### Request window

Each feed is fetched with `?dates=YYYYMMDD-YYYYMMDD`. Full sweep uses **7 days back to 7 ahead**; the fast lane uses a narrow **1 back to 1 ahead** window. Without a dates range ESPN returns only ~today, which is why upcoming fixtures never used to stretch out.

### Smart proxy rotation (`espnFetch`, `tryProxy`, `bestProxyIdx`)

Proxies: `corsproxy.io`, `allorigins`, `codetabs`, `thingproxy`, plus a direct attempt. We no longer fire all five every time. `espnFetch` tries the **last-good proxy alone first** (one request, 4.5s timeout); only if that fails does it race the rest (8s) and adopt whichever wins as the new `bestProxyIdx`. Healthy state = one request per feed instead of five. `bestProxyIdx` is in-memory (re-converges within a cycle after a reload).

### Tiered polling (one self-rescheduling loop: `pollTick` / `scheduleNextPoll`)

Not two `setInterval`s — a single loop so a fast refresh and a full sweep can never overlap and fight over the arrays.

- **Games live:** `refreshLiveFeeds()` every `FAST_POLL` (12s) re-fetches ONLY feeds with a live game (narrow window), updates live scores + FlyState, moves just-finished games to results. Upcoming/results are left alone (they barely change), so static data is not re-downloaded every few seconds.
- **Every `FULL_EVERY` (15) fast cycles (~3 min) while live:** a full sweep anyway, to catch kickoffs, finishes, and refresh upcoming/results.
- **Nothing live:** full sweep every `SLOW_POLL` (60s) to catch games starting.
- **After a failed cycle:** quick retry after `RETRY_POLL` (8s) instead of waiting the full interval (`lastPollFailed` drives this).
- **Returning to the app:** a `visibilitychange` listener triggers an immediate poll (guarded by `isPolling`).
- `currentLiveFeeds()` derives the live feed set from `ALL_LIVE`.

### Freshness signal

A small “Updated just now / X mins ago” line at the top of the Feed (`renderFreshness`, `lastUpdateMs`, `lastPollFailed`; a 30s ticker keeps it current). On a failed cycle it turns amber and reads “… reconnecting”. The fixed red `conn-banner` still covers a total outage.

### Feeds

**US/Canada (8):** `basketball/nba`, `football/nfl`, `baseball/mlb`, `hockey/nhl`, `soccer/usa.1`, `basketball/wnba`, `basketball/mens-college-basketball`, `football/college-football`
**Soccer Europe (13):** `soccer/eng.1`, `esp.1`, `ger.1`, `ita.1`, `fra.1`, `eng.2`, `ned.1`, `por.1`, `sco.1`, `tur.1`, `uefa.champions`, `uefa.europa`, `eng.w.1`
**Soccer Americas (4):** `soccer/bra.1`, `arg.1`, `mex.1`, `conmebol.libertadores`
**Soccer other (4):** `soccer/aus.1`, `irl.1`, `ind.1`, `rsa.1`
**Australian (1):** `australian-football/afl`  **Cricket (2):** `cricket/8048` (IPL), `cricket/23694` (Intl)  **Tennis (2):** `tennis/atp`, `tennis/wta`

### Confirmed NOT viable (do not retry)

NRL (all rugby slugs 403/empty), NASCAR (`nascar-cup-series` dead, removed v22), cricket junk IDs `8039 / 19429 / all / 8047`. `soccer/all` works but groups everything — unused. BBL `cricket/8044` is Dec-Jan only.

-----

## AFL team names + Fly Mode codes

ESPN’s raw AFL names are inconsistent, so `AFL_TEAMS` + `aflTeam(name)` (just before `mapEspnEvent`, applied when `feed.league === 'afl'`) map each to a **proper club name** (cards) and a fixed **three-letter TV code** (Fly Mode, via `homeShort`/`awayShort`; Fly Mode uses `m.homeShort || abbrev(m.home)`). Matched by distinctive substring, most-specific-first.

|Proper name                  |Code||Proper name              |Code|
|-----------------------------|----||-------------------------|----|
|Adelaide Crows               |ADE ||Hawthorn Hawks           |HAW |
|Brisbane Lions               |BRI ||Melbourne Demons         |MEL |
|Carlton Blues                |CAR ||North Melbourne Kangaroos|NM  |
|Collingwood Magpies          |COL ||Port Adelaide Power      |PTA |
|Essendon Bombers             |ESS ||Richmond Tigers          |RIC |
|Fremantle Dockers            |FRE ||St Kilda Saints          |STK |
|Geelong Cats                 |GEE ||Sydney Swans             |SYD |
|Gold Coast Suns              |GCS ||West Coast Eagles        |WCE |
|Greater Western Sydney Giants|GWS ||Western Bulldogs         |WBD |

**Needs live verification** on an AFL match day (matching depends on ESPN’s exact strings, which can’t be checked offline). Favourites still match via partial-contains, so following by short name keeps working.

-----

## Design system

Pure black `#000000` everywhere. No dark grey, no gradients.

|Token                             |Value                   |Use                             |
|----------------------------------|------------------------|--------------------------------|
|`--bg`                            |`#000000`               |Background                      |
|`--card`                          |`#111114`               |Card fill                       |
|`--card2`                         |`#1c1c1e`               |Secondary surfaces              |
|`--live`                          |`#30d158`               |Live cards, brand green, FlyTime|
|`--upcoming`                      |`#ffd60a`               |Upcoming cards, warming         |
|`--result`                        |`#ff453a`               |Result cards, on fire           |
|`--onrun`                         |`#ff9f0a`               |FlyState on a run               |
|`--comeback`                      |`#bf5af2`               |FlyState comeback               |
|`--cold`                          |`#409cff`               |FlyState gone cold              |
|`--blue`                          |`#0a84ff`               |Dropdowns                       |
|`--text` / `--text-2` / `--text-3`|white / 80% / 40%       |Text tiers                      |
|`--sep`                           |`rgba(255,255,255,0.08)`|Dividers                        |

**Typography:** Inter (Google Fonts) + `-apple-system` fallback, loaded via `<link>` + `preconnect` in `<head>` (not CSS `@import`) for faster first paint.
**Wordmark:** “Stat” white + “Fly” green, 33px/700, with a 36px circular fly mark.
**Logo fallback:** logo-less teams show only the sport icon (`logoImg` derives `emoji.split(' ')[0]`), never the full league label.
**Principles:** do not genericise (no grey/gradients/soft forgettable cards); minimal CSS-only motion; intentionality test — does it help get a score in under 3 seconds?

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
1. **No mock data.** ESPN only. NRL/NASCAR not viable.
1. **Permanently removed:** score worms (v20), card expand/collapse (v20), UFC/PGA/F1 (v23), GAA (no API). Do not reintroduce.

-----

## Deployment (GitHub Pages, edit-on-phone)

Repo files: `index.html`, `sw.js`, `manifest.json`, `icon192.png`, `icon512.png`, `README.md`, `NOTES.md`, `.nojekyll`.

Steps: edit in GitHub web UI, commit, wait ~30s for Pages rebuild, refresh on phone. **Every deploy that touches HTML/CSS/JS/icons: bump `CACHE` in `sw.js` to a number HIGHER than what is currently live** (`statfly-vN`). Current: **`statfly-v39`**. For an installed PWA, removing + re-adding the Home Screen icon forces a stale manifest/cache to refresh.

-----

## Decisions log (recent in **bold**)

|Decision                     |Outcome                                                                                                                |
|-----------------------------|-----------------------------------------------------------------------------------------------------------------------|
|Background                   |Pure black everywhere                                                                                                  |
|Feed filter default          |All                                                                                                                    |
|Upcoming / results windows   |7 days each, via `?dates=` range                                                                                       |
|**Polling**                  |**Tiered self-rescheduling loop: 12s fast lane (live feeds only), full sweep every ~3 min while live or 60s when idle**|
|**Auto-retry**               |**8s quick retry after a failed cycle**                                                                                |
|**Proxy strategy**           |**Try last-good proxy first, fall back to racing; remember winner**                                                    |
|**Freshness line**           |**“Updated X ago / reconnecting” at top of Feed**                                                                      |
|FlyState                     |8-state colour-fill on live scores + Fly Mode                                                                          |
|Logo fallback                |Sport icon only when no crest                                                                                          |
|AFL names                    |Proper names on cards, 3-letter TV codes in Fly Mode                                                                   |
|Font load                    |`<link>` + preconnect in head                                                                                          |
|Score colours legend         |In Settings                                                                                                            |
|Times                        |User local timezone                                                                                                    |
|Team matching                |Partial contains                                                                                                       |
|Score worms / expand-collapse|REMOVED v20                                                                                                            |
|Hosting                      |GitHub Pages                                                                                                           |

-----

## Open items

**Verify on live match days**

- Tiered polling: confirm live scores refresh ~12s while a game is live, a kickoff moves a game into Live within ~3 min, a finish moves it to Results, and idle/cold load feel unchanged.
- Proxy rotation: confirm scores still load reliably and recover when a proxy dies.
- AFL: proper names + TV codes resolve correctly per club; AFL/cricket parsers; v25 soccer slugs (esp. `ind.1`, `rsa.1`, `conmebol.libertadores`).
- FlyState tuning thresholds per sport.

**Product**

- Onboarding flow (pick sports, teams, enable notifications) — required before any public launch.
- Placeholder/TBD fixtures (e.g. undecided playoff series shown as “Spurs/Thunder”): render cleanly now but have no real teams/form. Open question: hide them, or keep?
- Some teams show no form strip (form is fetched async after cards render; placeholder/edge teams have no record).
- iPad/tablet width unchecked. PWA install test on Android.

**Optional cleanup**

- `fetchTeamForm` still has its own near-duplicate fetch logic; could be folded into the shared `espnFetch`/`tryProxy` path.
- Persist `bestProxyIdx` to localStorage so the first cold load already prefers a good proxy.

-----

## Parallel track: native app (FlutterFlow)

Separate planned production build in FlutterFlow + Firebase. Reference: `SportsTimeline_FlutterFlow_Guide.docx`. Only relevant when the user explicitly asks about the native track. Android-first; iOS later via MacInCloud. Costs: Apple $99/yr, Google $25 one-time.

-----

## Version history (recent)

**v39** (current) – Data-reliability steps 3-5. Tiered polling (one self-rescheduling loop: 12s fast lane for live feeds only, periodic full sweep, 60s idle); 8s auto-retry after a failed cycle; smart proxy rotation (try last-good proxy first, fall back to racing, remember winner); narrow window for the fast lane; immediate refresh on returning to the app.
**v38** – AFL proper club names on cards + 3-letter TV codes in Fly Mode (`AFL_TEAMS` + `aflTeam`).
**v37** – Logo fallback fix (sport icon only when no crest; fixed the doubled-“NBA” card).
**v36 / step 2** – 7-day fetch window via `?dates=` range; upcoming filter 14->7 days.
**v35 / step 1** – Freshness line; removed dead stat-ticker; team logo `alt=""`; font load moved to head `<link>` + preconnect; FlyState colour legend in Settings.
**(v28-v34)** – Prior-session cache bumps incl. PWA config fixes (manifest orientation `any`, scope/start_url `.`, relative SHELL paths). Details not fully captured.
**v26-v27** – Fly Mode redesign; discovery cleanup (removed F1, Golf Majors).
**v20-v25** – Score worms + expand/collapse removed; soccer slugs added (to 36 feeds).