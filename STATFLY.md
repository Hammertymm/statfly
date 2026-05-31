# StatFly

Mobile-first sports scores app. Pure black UI, Apple-style typography, single self-contained HTML file. Works in any mobile browser, installable as a PWA.

**Tagline:** Scores Anywhere. Simple.
**Brand colour:** `#30d158` (Apple green)
**Current file:** `index.html` (cache `statfly-v40`)
**Live URL:** [hammertymm.github.io/statfly](https://hammertymm.github.io/statfly)
**Repo:** [github.com/Hammertymm/statfly](https://github.com/Hammertymm/statfly)

This is the single source of truth. The older `StatFly_skill.md` is retired.

-----

## How to work on this codebase

Biases toward caution over speed. For trivial edits, use judgment.

**Think before coding.** State assumptions explicitly. If multiple interpretations exist, present them rather than picking silently. If a simpler approach exists, say so. If something is unclear, stop and name what’s confusing before writing code. Track ambiguity (HTML prototype vs FlutterFlow) still applies — ask once.

**Simplicity first.** Smallest change that solves the problem. No features beyond what was asked, no abstractions for single-use code, no flexibility or configurability that wasn’t requested, no error handling for impossible cases. If a diff is 200 lines and could be 50, rewrite it.

**Surgical changes.** Touch only what the request requires. Don’t improve adjacent code, don’t refactor what isn’t broken, match existing style even if you’d write it differently. If an edit makes a variable or function unused, remove it. If pre-existing dead code is nearby, mention it but leave it. Every changed line should trace directly to the request.

**Verify before delivering.** Define a concrete check up front, not “make it work”. For multi-step edits, state a brief plan with a verification step per item. StatFly has no test suite — verification means running the unicode check, confirming the page-div order, confirming `results-cards` is inside `page-results`, and (when behavior changes) describing what to tap on the phone to confirm it works.

-----

## What it does

Lets you follow your favourite teams across 34 leagues and see live scores, upcoming fixtures, and recent results in one feed. No login. No ads. No clutter.

|Tab    |What it shows                                                           |
|-------|------------------------------------------------------------------------|
|Feed   |Live matches + upcoming fixtures (next 14 days). Toggle: My Teams / All.|
|Results|Completed matches (last 4 days). Toggle: My Teams / All.                |
|Teams  |Add and manage followed teams. Global search + Suggested for You list.  |

A fourth button in the bottom nav opens **Fly Mode**: a full-screen view showing only your followed teams’ scores, designed for glancing at across a room.

-----

## FlyState (momentum colours)

FlyState is the colour of the **score numbers** on a card (distinct from the card’s
left border, which shows match status: green live / yellow upcoming / red result).
It answers “what is happening right now”, not “what is the score”. One engine in the
`<script>` block (`updateFlyState`, `resolveSide`, `momTier`, `isFlyTime`) runs for every
live match each poll.

**Seven states**, by priority: Green FlyTime > Purple comeback > Red on fire >
Orange on run > Yellow warming > Blue gone cold > white neutral. At match level,
Overtime outranks FlyTime (an extra beyond the V2 spec; keep it).

**Momentum model.** No play-by-play exists in the feed, so momentum is *inferred from
score deltas between polls*: `mom = prev*MOM_DECAY + min(delta/bigPlay, 1.6)*MOM_GAIN`,
clamped 0–100. The decay (0.6) is the anti-flicker. Momentum is per-side (“am I hot”),
so both teams can be hot at once.

**Tuning lives in one block** near the top of the engine – adjust there, not inline:

|Constant     |Value|Meaning                                        |
|-------------|-----|-----------------------------------------------|
|`MOM_DECAY`  |0.6  |Fraction of last poll’s momentum kept          |
|`MOM_GAIN`   |50   |A single bigPlay burst lands in Orange, not Red|
|`MOM_WARM`   |16   |Yellow threshold                               |
|`MOM_ONRUN`  |40   |Orange threshold (the common state)            |
|`MOM_ONFIRE` |70   |Red threshold – AND must be sustained          |
|`RED_SUSTAIN`|2    |Polls a side must stay hot before Red shows    |
|`COLD_MOM`   |12   |Below this a side counts as stalled            |

These are **starting values pending live calibration** against the V2 frequency targets
(less White, Orange common, Red rare). Not yet validated on real matches.

**FlyTime** is clock+margin per sport (reliable feed data). Basketball uses a possession
model (`margin <= (clockSec/24)*1.5`, final 5 min). AFL last ~8 min, soccer from 75’,
baseball inning >=8. Tennis and cricket are deliberately excluded (data not in feed).

**FlyTime alert.** One buzz/notification on first entry into FlyTime, for followed teams
with the bell on only (deliberate deviation from spec’s “no filtering” to avoid spam).
On iPhone the buzz is the Notification itself – iOS has no web vibration.
Deduped via `flytimeAlerted` (localStorage `statfly_flytime`).

**Blue (drought).** Fires independently after a real scoring drought – basketball 4 min,
AFL 12 min (`coldMins` in `FLY_TUNING`, wall-clock based) – or the older relative rule
(stalled while opponent is hot). Other sports have no drought window (data not in feed).

**Rivalry marker.** Skull (`\u2620\uFE0F`) beside the league tag on live/upcoming cards
for known fixtures. Editable `RIVALRIES` list (starter set) + `isRivalry()`, contains-match
in either order. AFL Fly Mode labels use official TV codes via `AFL_TV` in `abbrev()`.

**Adaptive polling.** Default 60s; drops to `FLY_POLL` (20s) while any live match is in
FlyTime. Self-rescheduling (`runPoll`/`scheduleNextPoll`), not `setInterval`. 20s is the
floor because each poll refreshes every feed.

-----

## Data sources – 34 feeds (ESPN unofficial API)

**US / Canada (8):** NBA `basketball/nba`, NFL `football/nfl`, MLB `baseball/mlb`, NHL `hockey/nhl`, MLS `soccer/usa.1`, WNBA `basketball/wnba`, NCAAM `basketball/mens-college-basketball`, NCAAF `football/college-football`

**Soccer – Europe (12):** EPL `soccer/eng.1`, La Liga `soccer/esp.1`, Bundesliga `soccer/ger.1`, Serie A `soccer/ita.1`, Ligue 1 `soccer/fra.1`, Championship `soccer/eng.2`, Eredivisie `soccer/ned.1`, Primeira Liga `soccer/por.1`, Scottish Premiership `soccer/sco.1`, Super Lig `soccer/tur.1`, UCL `soccer/uefa.champions`, UEL `soccer/uefa.europa`, WSL `soccer/eng.w.1`

**Soccer – Americas (4):** Brasileirao `soccer/bra.1`, Liga Profesional `soccer/arg.1`, Liga MX `soccer/mex.1`, Libertadores `soccer/conmebol.libertadores`

**Soccer – other (4):** A-League `soccer/aus.1`, League of Ireland `soccer/irl.1`, ISL `soccer/ind.1`, PSL `soccer/rsa.1`

**Australian (1):** AFL `australian-football/afl`

**Cricket (2):** IPL `cricket/8048`, International cricket `cricket/23694`

**Tennis (2):** ATP `tennis/atp`, WTA `tennis/wta`

No API key required. Called direct from the browser via rotating CORS proxies (`corsproxy.io`, `allorigins`, `codetabs`, `thingproxy`).

**ESPN-only is the doctrine.** No mock data. The three match arrays (`ALL_LIVE`, `ALL_UPCOMING`, `ALL_RESULTS`) start empty.

### Endpoints confirmed NOT viable

- **NRL** – tested `rugby/3`, `rugby/nrl`, `rugby-league/nrl`, `rugby/league/3`, `rugby/270557`. All proxies return 403 or 0 events with no league metadata. ESPN’s website shows NRL but the public API does not expose it. Would need a paid API or an alternative free source. **Do not retry.**
- **NASCAR** – slug `nascar-cup-series` tested in v21, 5/5 proxies dead. Removed in v22.
- Cricket IDs that returned junk: `cricket/8039` (stale World Cup), `cricket/19429` (random old matches), `cricket/all`, `cricket/8047` (empty).
- `soccer/all` works but groups everything under one label in the UI. Not used.

### Off-season notes

- BBL (`cricket/8044`) is live Dec-Jan only. Off-season May-Nov returns nothing.

### Slugs added v25 but not yet observed live

All 14 are based on ESPN’s `<country>.<tier>` convention or URLs confirmed via search results, but none were tested with live matches:
Championship, Eredivisie, Primeira Liga, Scottish Premiership, Super Lig, Brasileirao, Liga Profesional, Liga MX, A-League, League of Ireland, ISL, PSL, Libertadores, WSL.
Higher risk slugs: `ind.1` (ISL, Sept-April season), `rsa.1` (PSL, Aug-May season), `conmebol.libertadores` (longer slug pattern, may need `.cup` suffix).

To audit a specific slug: search for a known team in that league (e.g. “Boca Juniors” for `arg.1`, “Bohemian” for `irl.1`). If you can follow it but never see matches, the slug is dead.

-----

## Design system

Pure black `#000000` everywhere – all pages, header, and bottom nav. No dark grey, no gradients.

|Token       |Value                   |Use                    |
|------------|------------------------|-----------------------|
|`--bg`      |`#000000`               |Background             |
|`--card`    |`#111114`               |Card fill              |
|`--card2`   |`#1c1c1e`               |Secondary surfaces     |
|`--live`    |`#30d158`               |Live cards, brand green|
|`--upcoming`|`#ffd60a`               |Upcoming cards         |
|`--result`  |`#ff453a`               |Result cards           |
|`--blue`    |`#0a84ff`               |Dropdowns              |
|`--text`    |`#ffffff`               |Primary text           |
|`--text-2`  |`rgba(235,235,245,0.8)` |Secondary text         |
|`--text-3`  |`rgba(235,235,245,0.4)` |Tertiary text          |
|`--sep`     |`rgba(255,255,255,0.08)`|Dividers               |

**Typography:** Inter (Google Fonts) with `-apple-system` fallback.
**Wordmark:** `StatFly` – “Stat” white, “Fly” green. 33px weight 700, paired with a 36px circular fly mark in the header.
**Card borders:** colour-coded by state. Green = live, yellow = upcoming, red = result.
**Logo:** circular Superman-fly. Same base64 image used in header (`.brand-mark`) and Fly Mode tab (`.nb-flymode > img`).

### Design principles

**Do not genericise.** StatFly has a deliberate aesthetic: pure black, Apple-green accent, tight typographic hierarchy. Never drift toward common AI-generated UI defaults (grey backgrounds, purple gradients, Inter swapped for a system font, cards softened into something forgettable). Every UI decision should feel like it belongs in the iOS App Store.

**Motion.** Animations should be purposeful and minimal. Prefer CSS-only transitions. One well-timed page load with staggered card reveals beats scattered micro-animations everywhere. Tap states should feel snappy, no sluggish easing.

**Spatial composition.** Controlled density over empty padding. Cards should feel information-rich but never cluttered. Consistent vertical rhythm. No decorative elements that do not serve the glance-and-go use case.

**Atmosphere over flatness.** Pure black `#000000` already creates depth, lean into it. Subtle card borders (`--sep`) and colour-coded left borders do more visual work than gradients or shadows. Keep it that way.

**Intentionality test.** Before adding any new UI element, ask: does this help a user get a score in under 3 seconds? If not, it does not belong.

-----

## Hard rules – do not violate

**iOS Safari Unicode crash.** Certain Unicode characters silently crash the iOS Safari JIT compiler when present inside `<script>`. Never use these in JS:

- Em dash U+2014
- En dash U+2013
- Box drawing U+2500 to U+257F
- Minus sign U+2212
- Plus-minus U+00B1

HTML and CSS are fine – only the `<script>` block is affected. Check before every release:

```js
const bad = [...script].filter(c =>
  [0x2014,0x2013,0x2550,0x2500,0x00b1,0x2212].includes(c.charCodeAt(0))
);
console.log('Dangerous unicode:', bad.length); // must be 0
```

**Page structure.** Three page divs in this order:

1. `<div id="page-home" ...>`
1. `<div id="page-results" ...>`
1. `<div id="page-settings" ...>`

`results-cards` must sit inside `page-results`. Verify:

```js
html.indexOf('id="results-cards"') > html.indexOf('id="page-results"')
```

**Init pattern.** Never call `document.createElement` in an IIFE at script root. Always defer:

```js
setTimeout(()=>{
  renderHome(); renderResults(); renderFavs();
  loadLiveData();
  setInterval(()=>{ if(!document.hidden) loadLiveData(); }, POLL_INTERVAL);
}, 0);
```

**Single file.** The prototype is one HTML file with all CSS and JS inline. No splits, no build steps, no npm.

**No mock data.** ESPN-only. NRL and NASCAR confirmed not viable – don’t suggest retrying.

**No score worms.** Removed in v20. Don’t propose reintroducing in any form.

**No card expand/collapse.** Removed in v20. All info renders inline.

-----

## Features built

**Navigation**

- Sticky frosted-glass header with circular fly mark, wordmark, tagline
- Top tabs: Feed / Results / Teams (sentence case, 3px active underline)
- Bottom nav: Feed / Results / Teams / Fly Mode (10px labels, sentence case)
- Swipe between tabs (60px min, 350ms max, ignored on dropdowns and sliders)
- Tab switch scrolls to top
- My Teams / All toggle on Feed and Results

**Cards**

- Stat ticker, 15s rotation, 400ms fade
- Match facts shown inline below summary on upcoming and result cards
- Results grouped by date
- Score flash on live update
- No expand/collapse – all info visible at glance

**Teams tab**

- Search-only follow flow (global search across all teams / leagues / countries)
- “Suggested for you” list with green-outline Follow pills
- Bell toggle per team: real push notifications via `Notification.requestPermission()`
- Bell sound: 620Hz E5 ding, 1.4s decay, two partials, amp 0.18
- Favourites and bell states persisted in `localStorage`
- Trash icon to unfollow

**Live data**

- 60s polling while the tab is visible
- 14-day upcoming window, 4-day results window
- Times rendered in user’s local timezone
- Past matches incorrectly marked non-FINAL are auto-classified as finished (date sanity in `espnStatus`)
- Connection banner shown when all proxies fail; auto-hides on next success

**Fly Mode**

- Full-screen 1 col x 4 rows, one match per row
- Both scores same size and colour (no winner highlight)
- Brightness slider at the bottom (CSS filter on the overlay)
- Tap anywhere except the slider to exit

**PWA**

- `manifest.json` + `sw.js` + `icon192.png` + `icon512.png`
- Installable via Safari -> Share -> Add to Home Screen
- Works offline once cached
- ESPN/proxy calls bypass cache (always fresh)

-----

## Deployment (GitHub Pages)

Edit-on-phone workflow. User is iPhone-only, edits via Safari on github.com.

**Files in repo:**

- `index.html`
- `sw.js`
- `manifest.json`
- `icon192.png`
- `icon512.png`
- `README.md`
- `NOTES.md`
- `.nojekyll` (added so test files in repo root are served; can be deleted if no longer needed)
- `feed-research.html` (research tester from v25 session; can be deleted)

**Deploy steps:**

1. Edit file in GitHub web UI or delete and re-upload
1. Commit
1. Wait ~30s for Pages rebuild
1. Refresh `hammertymm.github.io/statfly` on phone

**Every deploy that touches HTML/CSS/JS/icons:** bump `CACHE` in `sw.js` to the next version (`statfly-vN`). Current: `statfly-v40`.

**localStorage** is tied to the domain. As long as the GitHub Pages URL doesn’t change, favourites persist across deploys.

-----

## File freshness rule

The `/mnt/project/` copy of `index.html` goes stale between Claude sessions. We lost a day’s logo edits once because Claude worked from the stale project file.

**First step every session:** ask user to upload the current `index.html` from GitHub, or fetch from `hammertymm.github.io/statfly` directly. Do NOT trust `/mnt/project/`.

-----

## Decisions log

|Decision             |Outcome                                                                               |
|---------------------|--------------------------------------------------------------------------------------|
|Background           |Pure black `#000000` everywhere                                                       |
|Tagline              |“Scores Anywhere. Simple.” – white + green                                            |
|Wordmark size        |33px weight 700, paired with 36px circular fly mark                                   |
|Top tabs             |Feed / Results / Teams (sentence case)                                                |
|Bottom nav           |Feed / Results / Teams / Fly Mode (sentence case, 10px)                               |
|Fly Mode layout      |1 col x 4 rows, one match per row                                                     |
|Fly Mode scores      |Both same size, white, no colour difference                                           |
|Fly Mode exit        |Tap anywhere except brightness slider                                                 |
|Feed filter default  |All (not My Teams)                                                                    |
|Upcoming window      |14 days max                                                                           |
|Results window       |4 days max                                                                            |
|Times                |User local timezone, `toLocaleTimeString([])`                                         |
|Team matching        |Partial contains match, not exact                                                     |
|Score worms          |REMOVED in v20. Never reintroduce.                                                    |
|Card expand/collapse |REMOVED in v20. All info visible inline.                                              |
|Teams tab follow flow|Search-only + Suggested for You (cascade removed in v11)                              |
|Bell sound           |620Hz E5, 1.4s decay, two partials, amp 0.18                                          |
|Bell visual          |Emoji with green tint background when on                                              |
|Push notifications   |`Notification.requestPermission()` on first bell tap                                  |
|Result cards         |Always fully open                                                                     |
|localStorage         |Favs + bell states persisted                                                          |
|Swipe gestures       |Left/right between tabs, 60px min, 350ms max                                          |
|PWA                  |`manifest.json` + `sw.js` + `icon192.png` + `icon512.png`                             |
|Mock data            |NONE – all arrays start empty, ESPN only                                              |
|Hosting              |GitHub Pages (Netlify abandoned, credits ran out)                                     |
|UFC / PGA / F1       |Dropped in v23 (render risk on tournament-shaped data)                                |
|NASCAR               |Dropped in v22 (dead slug)                                                            |
|GAA                  |Excluded from search suggestions in v24 (no API)                                      |
|FlyState scope       |Score-number colour = momentum; card border = status                                  |
|Momentum model       |Inferred from poll score deltas (no play-by-play in feed)                             |
|Red qualification    |Sustained: `MOM_ONFIRE` for `RED_SUSTAIN` polls (v38)                                 |
|Yellow / Orange / Red|Thresholds 16 / 40 / 70 – starting values, need calibration                           |
|Drought Blue         |Independent: basketball 4 min, AFL 12 min (v38)                                       |
|FlyTime alert        |Followed+bell teams only (not every match); iOS = notification, no web vibration (v38)|
|Basketball FlyTime   |Possession model `margin <= (clockSec/24)*1.5` (v38)                                  |
|AFL / soccer FlyTime |AFL last ~8 min; soccer from 75’ (v38)                                                |
|Tennis / cricket     |Excluded from momentum + FlyTime (data not in feed)                                   |
|AFL Fly Mode labels  |Official TV codes via `AFL_TV` lookup (v39)                                           |
|Rivalry marker       |Skull on known fixtures; editable `RIVALRIES` list (v40)                              |
|Adaptive polling     |60s default, 20s while any match in FlyTime (v40)                                     |
|Must Watch           |PARKED – 80 threshold unreachable on available data                                   |

-----

## Backlog decisions (locked)

Items deliberately dropped, not to be reopened without good reason:

- Match detail view on card tap – undermines glance-and-go positioning
- Per-team notification settings page – over-engineering, bell is binary
- Push notifications backend (FCM / Supabase) – would turn static HTML into a backend product
- Favourites sync across devices – auth complexity not worth it
- Score worms in any form, including cricket second-innings worm
- Card expand/collapse
- NRL (no API), NASCAR (dead slug), GAA (no API)
- UFC, PGA, F1 (user dropped on render risk grounds)
- Formula 1, Golf Majors removed from discovery in v27 (motor racing and golf both shaped wrong for cards)

Items parked:

- Onboarding flow – required before any public launch (memory note set)
- Must Watch badge – parked. Spec’s 80-point threshold can’t be met from reliable
  feed data (rivalry alone is +40; finals/rankings not dependable). Revisit after
  Group 2 calibration, or after a live ESPN probe for a finals/championship signal.

-----

## Open items

**Verify on live match days**

- AFL parser on next live match
- Cricket parser on live IPL match
- 14 new soccer slugs from v25 (Championship, Eredivisie, Primeira Liga, Scottish Premiership, Super Lig, Brasileirao, Liga Profesional, Liga MX, A-League, League of Ireland, ISL, PSL, Libertadores, WSL). Audit: open the app post-deploy and look for matches in each. Higher risk: `ind.1`, `rsa.1`, `conmebol.libertadores`.

**FlyState V2 – pending live verification (all changes so far are static/simulated only)**

- **Group 2 calibration (highest priority).** Watch real games, compare colour mix to V2
  targets (Orange common, Red rare, less White). Adjust the tuning block. Until done,
  Groups 1-3 are not production-ready.
- FlyTime alert: confirm one notification fires on the installed iPhone PWA for a
  followed+bell team in a close late game (needs notification permission granted).
- Basketball possession FlyTime: may feel loose at the 5:00 mark (allows ~18 pts); tune
  if so.
- Drought Blue: confirm basketball 4 min / AFL 12 min behave on a live game; watch for
  false Blue after halftime / long stoppages (wall-clock based).
- Rivalry skull: confirm it shows on a rival fixture and not on neighbours; skull is a
  colour emoji (slightly off the pure-black aesthetic) – swap for a custom mark if wanted.
- Adaptive polling: confirm a FlyTime game refreshes faster while cold-load feels unchanged.
- AFL TV labels: confirm codes render on a live AFL match (relies on ESPN team names
  containing the matched words).

**Actively searching for a feed (kept in discovery, no live data yet)**

These leagues stay in discovery while alternative free sources are searched for (TheSportsDB, league-specific APIs). If a user follows a team in one of these, their card won’t show up in Feed/Results until a feed is wired.

- ‘Global’ list: Formula 1, ICC Cricket (ODI), ICC Cricket (T20), Six Nations Rugby, Golf Majors
- Australia: NRL (highest priority — user keeps asking), Big Bash League, Super Rugby Pacific, NBL
- South Africa: SA T20 Cricket
- Pakistan: Pakistan Super League
- New Zealand: Super Rugby Pacific
- England: WSL is NOW backed by `eng.w.1` – verify it shows real matches

Cleanup sweep not yet requested by user; mention if it comes up.

**Repo cleanup**

- Delete `feed-research.html` and `.nojekyll` when convenient. Neither is needed for the app.

**Performance (only if cold load feels slow)**

- Cold load is now 34 feeds x up to 4 proxies = up to 136 HTTP requests. NOTES previously flagged 44 as a watch point. Options if slow: parallelise + cancel on first success per feed, per-feed timeout (currently 10s), lazy-load feeds (only fetch when user follows a team in that league). Don’t optimise unless user reports it feels slow.

**More sports / leagues**

- Cheap ESPN adds same pattern: Bundesliga 2 (`ger.2`), Eredivisie 2 (`ned.2`), USL Championship, NWSL, more ESPN+ soccer.
- GAA – no API, would require scraping (user excluded).
- BBL – works on `cricket/8044` Dec-Jan only. Could add seasonally.

**Quality / polish**

- iPad layout never checked at tablet width.
- Error states when all proxies fail simultaneously.
- Stat ticker facts may be NBA/NFL-centric placeholders for newer feeds.
- PWA install test on Android (now that icon512 is wired).

**Strategic / future**

- App Store / Play Store launch (linked to FlutterFlow track)
- Analytics (Plausible / GoatCounter)
- Expanded README if discoverability becomes a goal

-----

## Parallel track: native app (FlutterFlow)

A separate production build is planned in FlutterFlow + Firebase. Reference doc: `SportsTimeline_FlutterFlow_Guide.docx`. Only relevant when the user explicitly asks about the native track.

**Strategy:**

- Android-first via FlutterFlow on Windows
- iOS later, MacInCloud (~$25/mo) for builds
- App Store costs: Apple $99/yr, Google $25 one-time

-----

## Version history

**v40** (current) – FlyState V2 Group 4+5. Rivalry marker: skull beside league tag on
live/upcoming cards for known fixtures (`RIVALRIES` starter list + `isRivalry()`).
Adaptive polling: 60s default, 20s while any live match is in FlyTime, self-rescheduling
(`runPoll`/`scheduleNextPoll`). Must Watch parked.

**v39** – Fly Mode AFL team labels use official TV abbreviations (ADE, BRI, CAR, COL, ESS,
FRE, GEE, GCS, GWS, HAW, MEL, NM, PTA, RIC, STK, SYD, WCE, WBD) via `AFL_TV` in `abbrev()`;
matched on a distinctive part of the name, ordered so Port Adelaide / North Melbourne / GWS
are not confused with Adelaide / Melbourne / Sydney. Other sports unchanged.

**v38** – FlyState V2 Group 1-3. Group 1: FlyTime alert (one buzz/notification on first
entry, followed+bell teams only); basketball possession-model FlyTime; AFL window to last
~8 min; soccer FlyTime from 75’. Group 2: momentum re-tune (`MOM_GAIN` 70->50, named
thresholds in one block, `RED_SUSTAIN` so Red needs a sustained run, earlier Yellow) ->
less White, Orange common, Red rare. Group 3: independent drought Blue (basketball 4 min,
AFL 12 min) via per-side last-score timestamps.

*Note: v28-v37 were not logged in this doc. The cache had already reached v37 before the
FlyState V2 work began; those interim changes are not captured here.*

**v27** – Discovery cleanup: removed Formula 1 and Golf Majors from `LEAGUES['Global']` and `TEAMS`. Header comment 40 -> 38 leagues. Other dead-feed leagues (NRL, NBL, BBL, Super Rugby, PSL Pakistan, SA T20, Copa do Brasil, Six Nations, ICC Cricket) kept in discovery as research targets.

**v26** – Fly Mode redesign: dynamic 1-4 row layout via `data-count`, centred status badge between scores, team labels above scores. Sort by start time, cap 4 with first-started-first-in. Empty state for 0 live. Live refresh hook so Fly Mode updates during polling. New circular fly logo swapped into header and tab bar. Splash asset saved separately.

**v25** – Added 14 new soccer slugs (Championship, Eredivisie, Primeira Liga, Scottish Premiership, Super Lig, Brasileirao, Liga Profesional, Liga MX, A-League, League of Ireland, ISL, PSL, Libertadores, WSL). Total feeds: 34.

**v24** – Removed GAA Football + GAA Hurling from Ireland suggestions and rosters.

**v23** – Removed UFC, PGA, F1 from feeds and search suggestions. Boxing removed from USA suggestions. Orphaned rosters (UFC, Boxing, PGA Tour) removed.

**v22** – Removed NASCAR (dead slug, 5/5 proxies dead).

**v21** – Added 13 new feeds: UEL, Bundesliga, Serie A, Ligue 1, WNBA, NCAAM, NCAAF, UFC, PGA, ATP, WTA, F1, NASCAR. Built `feed-test.html` standalone tester.

**v20** – Score worms removed entirely (CSS, function, data fields, render sites). Card expand/collapse removed. File shrunk by 242 lines. Upcoming card facts now render inline.

**v19** – `icon512.png` added; `manifest.json` icons array now lists both 192 and 512; `sw.js` SHELL includes both.

**v18** – Logo refresh on header and tab bar (circular fly). Result card cleanup: removed “SCORE CHART / Live chart coming soon” placeholder; removed duplicate summary line.

**v17** – Date sanity in `espnStatus`: past matches no longer leak into Coming Up.

**v12-v16** – Added 6 new feeds: EPL, La Liga, UCL, AFL, IPL, International cricket. Migrated from Netlify to GitHub Pages.

**v11** – Logo refresh (fly + wing mark). Teams tab redesigned: cascade replaced with search-only follow + Suggested for You list.

**v10** – Visual polish: sentence-case tabs, “Live Now” / “Coming Up” headers, 3px tab underline.

**v9** – Previous baseline.