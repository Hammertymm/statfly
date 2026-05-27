# StatFly

Mobile-first sports scores app. Pure black UI, Apple-style typography, single self-contained HTML file. Works in any mobile browser, installable as a PWA.

**Tagline:** Scores Anywhere. Simple.
**Brand colour:** `#30d158` (Apple green)
**Current file:** `index.html` (cache `statfly-v25`)
**Live URL:** [hammertymm.github.io/statfly](https://hammertymm.github.io/statfly)
**Repo:** [github.com/Hammertymm/statfly](https://github.com/Hammertymm/statfly)

This is the single source of truth. The older `StatFly_skill.md` is retired.

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

**Every deploy that touches HTML/CSS/JS/icons:** bump `CACHE` in `sw.js` to the next version (`statfly-vN`). Current: `statfly-v25`.

**localStorage** is tied to the domain. As long as the GitHub Pages URL doesn’t change, favourites persist across deploys.

-----

## File freshness rule

The `/mnt/project/` copy of `index.html` goes stale between Claude sessions. We lost a day’s logo edits once because Claude worked from the stale project file.

**First step every session:** ask user to upload the current `index.html` from GitHub, or fetch from `hammertymm.github.io/statfly` directly. Do NOT trust `/mnt/project/`.

-----

## Decisions log

|Decision             |Outcome                                                  |
|---------------------|---------------------------------------------------------|
|Background           |Pure black `#000000` everywhere                          |
|Tagline              |“Scores Anywhere. Simple.” – white + green               |
|Wordmark size        |33px weight 700, paired with 36px circular fly mark      |
|Top tabs             |Feed / Results / Teams (sentence case)                   |
|Bottom nav           |Feed / Results / Teams / Fly Mode (sentence case, 10px)  |
|Fly Mode layout      |1 col x 4 rows, one match per row                        |
|Fly Mode scores      |Both same size, white, no colour difference              |
|Fly Mode exit        |Tap anywhere except brightness slider                    |
|Feed filter default  |All (not My Teams)                                       |
|Upcoming window      |14 days max                                              |
|Results window       |4 days max                                               |
|Times                |User local timezone, `toLocaleTimeString([])`            |
|Team matching        |Partial contains match, not exact                        |
|Score worms          |REMOVED in v20. Never reintroduce.                       |
|Card expand/collapse |REMOVED in v20. All info visible inline.                 |
|Teams tab follow flow|Search-only + Suggested for You (cascade removed in v11) |
|Bell sound           |620Hz E5, 1.4s decay, two partials, amp 0.18             |
|Bell visual          |Emoji with green tint background when on                 |
|Push notifications   |`Notification.requestPermission()` on first bell tap     |
|Result cards         |Always fully open                                        |
|localStorage         |Favs + bell states persisted                             |
|Swipe gestures       |Left/right between tabs, 60px min, 350ms max             |
|PWA                  |`manifest.json` + `sw.js` + `icon192.png` + `icon512.png`|
|Mock data            |NONE – all arrays start empty, ESPN only                 |
|Hosting              |GitHub Pages (Netlify abandoned, credits ran out)        |
|UFC / PGA / F1       |Dropped in v23 (render risk on tournament-shaped data)   |
|NASCAR               |Dropped in v22 (dead slug)                               |
|GAA                  |Excluded from search suggestions in v24 (no API)         |

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

Items parked:

- Onboarding flow – required before any public launch (memory note set)

-----

## Open items

**Verify on live match days**

- AFL parser on next live match
- Cricket parser on live IPL match
- 14 new soccer slugs from v25 (Championship, Eredivisie, Primeira Liga, Scottish Premiership, Super Lig, Brasileirao, Liga Profesional, Liga MX, A-League, League of Ireland, ISL, PSL, Libertadores, WSL). Audit: open the app post-deploy and look for matches in each. Higher risk: `ind.1`, `rsa.1`, `conmebol.libertadores`.

**Pre-existing dead suggestions in search UI**

Discovery lists still surface leagues with no feeds:

- ‘Global’ list: Formula 1, ICC Cricket (ODI), ICC Cricket (T20), Six Nations Rugby, Golf Majors
- Australia: NRL, Big Bash League, Super Rugby Pacific, NBL
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

**v25** (current) – Added 14 new soccer slugs (Championship, Eredivisie, Primeira Liga, Scottish Premiership, Super Lig, Brasileirao, Liga Profesional, Liga MX, A-League, League of Ireland, ISL, PSL, Libertadores, WSL). Total feeds: 34.

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