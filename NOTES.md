# ScoreFly Notes

Running log of decisions, dead ends, and things worth remembering.

## Hosting & deploy

- **Live URL:** <https://scorefly.app> (GitHub Pages: <https://hammertymm.github.io/scorefly>)
- **Repo:** <https://github.com/Hammertymm/scorefly>
- **Hosting:** GitHub Pages (Netlify abandoned – credits ran out)
- **Deploy:** edit files in GitHub via Safari, commit, wait ~30s, refresh phone
- **Cache:** bump `CACHE` constant in `sw.js` every deploy that touches HTML/CSS/JS/icons. Currently `scorefly-v115`.

## Current feeds (47 live)

**US/CA (10):** NBA, NFL, MLB, NHL, MLS, WNBA, NBL, NCAAM, NCAAF, CFL
**Soccer (31):** EPL, La Liga, Bundesliga, Serie A, Ligue 1, Championship, Eredivisie, Primeira Liga, Scottish Premiership, Super Lig, UCL, UEL, WSL, Brasileirao, Liga Profesional, Liga MX, Libertadores, J1 League, League One, League Two, Chinese Super League, Belgian Pro League, Swiss Super League, Greek Super League, Serie B, Saudi Pro League, Russian Premier League, A-League, League of Ireland, ISL, PSL
**Australian (2):** AFL, NRL
**Cricket (2):** IPL, International cricket
**Rugby union (2):** URC, Top 14

## Data sources

### ESPN unofficial API – confirmed working

US/CA:

- NBA: `basketball/nba`
- NFL: `football/nfl`
- MLB: `baseball/mlb`
- NHL: `hockey/nhl`
- MLS: `soccer/usa.1`
- WNBA: `basketball/wnba`
- NCAAM: `basketball/mens-college-basketball`
- NCAAF: `football/college-football`

Soccer Europe:

- Premier League: `soccer/eng.1`
- La Liga: `soccer/esp.1`
- Bundesliga: `soccer/ger.1`
- Serie A: `soccer/ita.1`
- Ligue 1: `soccer/fra.1`
- Championship: `soccer/eng.2`
- Eredivisie: `soccer/ned.1`
- Primeira Liga: `soccer/por.1`
- Scottish Premiership: `soccer/sco.1`
- Super Lig: `soccer/tur.1`
- UEFA Champions League: `soccer/uefa.champions`
- UEFA Europa League: `soccer/uefa.europa`
- WSL: `soccer/eng.w.1`

Soccer Americas:

- Brasileirao: `soccer/bra.1`
- Liga Profesional: `soccer/arg.1`
- Liga MX: `soccer/mex.1`
- Libertadores: `soccer/conmebol.libertadores`

Soccer other:

- A-League: `soccer/aus.1`
- League of Ireland: `soccer/irl.1`
- ISL: `soccer/ind.1`
- PSL: `soccer/rsa.1`

Australian / rugby:

- AFL: `australian-football/afl`
- NRL: `rugby-league/3`
- NBL: `basketball/nbl`
- URC: `rugby/270557`
- Top 14: `rugby/270559`
- CFL: `football/cfl`

Cricket:

- IPL: `cricket/8048`
- International cricket: `cricket/23694`

Soccer added Jun 2026 (13 leagues): `jpn.1`, `eng.3`, `eng.4`, `chn.1`, `bel.1`, `sui.1`, `gre.1`, `ita.2`, `ksa.1`, `rus.1` — each has a calibrated `*-flytime-v1.json` table.

### Slugs still worth spot-checking on match days

Higher risk: `ind.1` (ISL, Sept-April), `rsa.1` (PSL, Aug-May), `conmebol.libertadores` (longer slug). Newer Jun 2026 slugs (`chn.1`, `rus.1`, etc.) not yet verified on live match days.

To audit a slug: follow a known team in that league; if matches never appear in Feed/Results, the slug is dead.

### Cricket league IDs tested (May 2026)

- `cricket/8048` – IPL (live, in-season)
- `cricket/23694` – International tours (e.g. NZ tour of India)
- `cricket/8044` – Big Bash League (off-season May-Nov, live Dec-Jan)
- `cricket/8039` – Returns stale World Cup data (skip)
- `cricket/19429` – Returns random old matches (skip)
- `cricket/all` – empty
- `cricket/8047` – empty

### Soccer tested

- `soccer/all` – works, returns ~23 events globally, but groups everything under one label in the UI. Not used.
- Individual league slugs all work via codetabs proxy.

### Endpoints tested and NOT viable

- **NASCAR** – `nascar-cup-series` tested in v21, 5/5 proxies dead. Removed in v22.
- **Tennis** – ATP/WTA removed from feeds (tournament-shaped data; removed Jun 2026).
- **Old NRL slugs** – `rugby/3`, `rugby/nrl`, etc. were dead; live feed is `rugby-league/3` (wired with FlyTime v1 table).

### Sports dropped by user (not technical failures)

- UFC, PGA, F1 (v23) – render risk on tournament-shaped data.
- GAA Football, GAA Hurling (v24) – excluded from Ireland suggestions; no API anyway.
- Formula 1, Golf Majors (v27) – removed from discovery. Motor racing and golf both shaped wrong for the card model.

### Actively searching for a feed (kept in discovery, no live data yet)

These leagues stay in the Teams tab discovery list even though no feed currently backs them. Searching for an alternative free source (TheSportsDB, league-specific APIs, etc). If a user follows a team in one of these, their card just won’t show up in Feed/Results until a feed is wired.

- **Big Bash League** (Australia) – ESPN `cricket/8044` works Dec-Jan only. Consider seasonal toggle.
- **Super Rugby Pacific** (Australia + New Zealand) – shared list. No source yet (URC and Top 14 are live separately).
- **WNBL** (Australia women's basketball) – no ESPN endpoint; distinct from men's **NBL** which is live.
- **Pakistan Super League** (Pakistan cricket) – no source yet.
- **SA T20 Cricket** (South Africa) – no source yet.
- **Copa do Brasil** (Brazil) – no source yet (Brasileirao is live).
- **Six Nations Rugby** (Global) – no source yet.
- **ICC Cricket ODI / T20** (Global) – international tours are partly covered by `cricket/23694`. World Cup-style events not reliable.

## FlyState (momentum colours) – added v38-v40

The colour of the **score numbers** on a card = momentum (separate from the card’s
left border, which is match status: green live / yellow upcoming / red result). Engine
in `<script>`: `updateFlyState`, `resolveSide`, `momTier`, `isFlyTime`. Seven states by
priority: Green FlyTime > Purple comeback > Red onfire > Orange onrun > Yellow warming >
Blue cold > white. Overtime outranks FlyTime at match level (kept; not in the V2 spec).

- **Momentum is inferred from poll score deltas** – there is no play-by-play in the feed.
  `mom = prev*MOM_DECAY + min(delta/bigPlay,1.6)*MOM_GAIN`, clamped 0-100. Decay 0.6 is
  the anti-flicker. Per-side, so both teams can be hot at once.
- **All tuning lives in one named-constants block** near the top of the engine. Current
  starting values (NOT yet calibrated on live matches): `MOM_GAIN 50`, `MOM_WARM 16`,
  `MOM_ONRUN 40`, `MOM_ONFIRE 70`, `RED_SUSTAIN 2`, `COLD_MOM 12`, `MOM_DECAY 0.6`.
- **FlyTime** = clock+margin per sport. Basketball possession model
  `margin <= (clockSec/24)*1.5` (final 5 min); AFL last ~8 min; soccer 75’; baseball
  inning >=8. Tennis + cricket deliberately excluded (data not in feed).
- **FlyTime alert**: one notification on first entry, followed+bell teams only (deliberate
  deviation from spec’s “no filtering” to avoid match-day spam). iOS has no web vibration,
  so the notification IS the buzz. Dedupe set `flytimeAlerted` (localStorage `scorefly_flytime`).
- **Drought Blue**: fires independently after basketball 4 min / AFL 12 min with no score
  (`coldMins` in `FLY_TUNING`, wall-clock based), or the older relative rule.
- **Rivalry marker**: skull beside the league tag on live/upcoming cards. Editable
  `RIVALRIES` starter list + `isRivalry()` (contains-match, either order).
- **AFL Fly Mode labels**: official TV codes via `AFL_TV` lookup in `abbrev()`.
- **Adaptive polling**: 60s default, drops to `FLY_POLL` (20s) while any match is in
  FlyTime. Self-rescheduling `runPoll`/`scheduleNextPoll` (replaced the fixed setInterval).
  20s is the floor because each poll refreshes every feed.
- **Must Watch**: PARKED. The spec’s 80-point threshold can’t be met from reliable feed
  data (rivalry alone is +40; finals/rankings not dependable). See parked items below.

## Backlog decisions (locked)

Items deliberately dropped, not to be reopened without good reason:

- Match detail view – undermines glance-and-go positioning. Cards stay simple.
- Notification settings (per-team granularity) – over-engineering. Bell is binary.
- Push notifications backend – would turn the app into a real backend product. Not before there are users who care.
- Favourites sync across devices – auth complexity not worth it for a phone-first scores app.
- Score worms (all sports, all match states) – never using any kind of worm. Stripped from code in v20.
- Cricket second-innings worm – covered by above.
- Card expand/collapse – removed v20. All info renders inline.

Items parked, with triggers:

- **Onboarding flow** – required before any public launch. Memory note set; Claude will raise this when launch comes up.
- **Must Watch badge** (FlyState V2) – parked. The spec’s 80-point threshold can’t be met from reliable feed data: rivalry alone is +40, and finals/rankings/form-parity aren’t dependable from the ESPN scoreboard feed offline. Revisit after Group 2 calibration, or after a live ESPN probe confirms a finals/championship signal in the feed.

## Recent bug fixes / changes

> Note: v28-v37 were not logged in this file. The service worker cache had already reached
> v37 before the FlyState V2 work began; those interim changes are not captured here.

### v40 – FlyState V2 Group 4 + 5

- **Rivalry marker:** skull (`\u2620\uFE0F`) beside the league tag on live + upcoming
  cards for known fixtures. New editable `RIVALRIES` list (starter set: El Clasico, North
  London, Manchester, Merseyside, Superclasico, AFL Showdown, Western Derby, Q-Clash,
  Collingwood-Carlton, Anzac Day, Lakers-Celtics) + `isRivalry()` (contains-match, either
  order). Verified statically that “Adelaide” inside “Port Adelaide” does not cause false
  rivalries.
- **Adaptive polling:** 60s default, 20s (`FLY_POLL`) while any live match is in FlyTime.
  Replaced the fixed `setInterval(loadLiveData)` with a self-rescheduling
  `runPoll`/`scheduleNextPoll` loop that always reschedules (even on error / hidden tab).
- **Must Watch parked** (see parked items).

### v39 – AFL Fly Mode TV abbreviations

Fly Mode AFL team labels now use official TV codes (ADE, BRI, CAR, COL, ESS, FRE, GEE,
GCS, GWS, HAW, MEL, NM, PTA, RIC, STK, SYD, WCE, WBD) via an `AFL_TV` lookup in `abbrev()`.
Matched on a distinctive part of the name, ordered so Port Adelaide / North Melbourne /
Greater Western Sydney can’t be confused with Adelaide / Melbourne / Sydney. Other sports
keep the generic abbreviation. All 18 verified statically.

### v38 – FlyState V2 Group 1-3

- **Group 1 (FlyTime):** new FlyTime alert – one buzz/notification on first entry into
  FlyTime, followed+bell teams only. Basketball switched to a possession model. AFL window
  widened to last ~8 min; soccer FlyTime starts at 75’ (was 80’).
- **Group 2 (momentum re-tune):** `MOM_GAIN` 70 -> 50 so one big score lands in Orange not
  Red; named threshold constants moved into one block; `RED_SUSTAIN` added so Red needs a
  sustained run; Yellow triggers earlier. Goal: less White, Orange common, Red rare.
- **Group 3 (drought Blue):** Blue can now fire independently after a real scoring drought
  (basketball 4 min, AFL 12 min) via per-side last-score timestamps, not only when the
  opponent is hot.
- All static/simulated checks pass (Unicode, page order, syntax, momentum simulation).
  NOT yet verified on live ESPN data or device – see Open items.

### v27 – Discovery cleanup (F1 + Golf), research log added

Removed Formula 1 and Golf Majors from the Teams tab discovery (`LEAGUES['Global']`) and dropped the corresponding `TEAMS` rosters. Header count comment 40 -> 38 leagues. Other “kept but dead” leagues (NRL, BBL, Super Rugby, PSL Pakistan, SA T20, Copa do Brasil, Six Nations, ICC Cricket, WNBL) intentionally left in discovery – user is still searching for feeds for these (see “Actively searching for a feed” above).

### v26 – Fly Mode dynamic layout + new logo

- Fly Mode now scales with live My Teams match count: 1 / 2 / 3 / 4 rows (`data-count` attribute drives `grid-template-rows`). Score type scales via `--rows` CSS var.
- Card layout switched to: team labels above scores, centred Q/clock pill badge between the two scores, hairline vertical divider.
- Sort: live matches ordered by start time ascending. Cap 4; if a 5th goes live, it waits until one of the 4 ends (first-started-first-in).
- Empty state (“No live matches”) rendered via dedicated `.flymode-empty` class instead of inline styling.
- `loadLiveData()` now refreshes Fly Mode grid if the overlay is open, so scores update during 60s polling without re-entering.
- Added `startMs` field to live match objects (computed from `event.date`) to support time-based sort.
- Logo refresh: new circular Superman-fly base64 swapped in both `.brand-mark` (header) and `.nb-flymode > img` (tab bar). Old base64 fully removed.

### v25 – 14 new soccer slugs

Added Championship, Eredivisie, Primeira Liga, Scottish Premiership, Super Lig, Brasileirao, Liga Profesional, Liga MX, A-League, League of Ireland, ISL, PSL, Libertadores, WSL. Total feeds now 34. None tested live yet – audit on next match days.

### v24 – GAA removed from search

Removed GAA Football + GAA Hurling from Ireland suggestions and rosters. No API exists for either; were appearing as dead suggestions.

### v23 – UFC, PGA, F1 removed

Removed from feeds and search suggestions. Also stripped Boxing from USA suggestions. Orphaned rosters (UFC, Boxing, PGA Tour) removed. User decision based on render risk: tournament-shaped data doesn’t map cleanly to the match-card model.

### v22 – NASCAR removed

Tested `nascar-cup-series` in v21; 5/5 proxies dead. Slug confirmed not viable.

### v21 – 13 new feeds + feed tester

Added: UEL, Bundesliga, Serie A, Ligue 1, WNBA, NCAAM, NCAAF, UFC, PGA, ATP, WTA, F1, NASCAR. Built `feed-test.html` as a standalone tester (same proxy rotation as app). Test results: 23/24 worked, NASCAR failed.

### v20 – Worm removal + expand removal

- Deleted entire `buildWorm` function (~180 lines) and worm CSS block.
- Stripped `worm` and `wormOpts` fields from match base factory.
- Removed `toggleExpand` / `closeAllExpanded` and the tap-elsewhere overlay.
- Cards no longer expand. Live cards end at the summary line. Upcoming cards render facts inline below summary when present. Result cards unchanged in shape, just no worm section.
- `.card.expanded` guard removed from swipe gesture handler.
- File shrunk from 1784 to 1542 lines.
- Unicode safety and page structure checks both clean.

### v19 – PWA icon completion

- Added `icon512.png` to repo (downscaled from 1254x1254 master via Lanczos).
- `manifest.json` icons array now includes both 192 and 512.
- `sw.js` SHELL includes `/icon512.png`.

### Date sanity in `espnStatus` (v17)

Past matches were appearing in Coming Up because ESPN sometimes returns non-FINAL status for completed games. Fix: if status isn’t IN_PROGRESS/HALFTIME/FINAL but event date is in the past, classify as ‘finished’. Result: cleanly routed to Results bucket and filtered by 4-day window.

### Result card cleanup (v18)

- Removed “SCORE CHART / Live chart coming soon” placeholder.
- Removed duplicate `card-sum` line at bottom of result card.

### Logo (v18)

Both header logo (`.brand-mark`) and tab bar fly (`.nb-flymode > img`) replaced with the circular Superman-fly. Same base64 image used in both spots.

## Repo state (current)

Core app: `index.html`, `sw.js`, `manifest.json`, `icon192.png`, `icon512.png`, `team-halo-config.json`, `CNAME`, `.nojekyll`

FlyTime v1 tables: 45 `*-flytime-v1.json` files (one per league in `FLY_V1_REGISTRY`; cricket feeds use live rules only).

Build scripts: `scripts/build_flytime_v1.py`, `scripts/build_soccer_flytime.py`, `scripts/calibrate_flytime.py`, `scripts/report_new_league_thresholds.py`, and related research tools.

Docs: `README.md`, `NOTES.md`, `SCOREFLY.md`, `VERSION HISTORY.md`

`.nojekyll` and `feed-research.html` were added in v25 for a research tester that didn’t end up being used (Safari caching issue). (if present) can be deleted when convenient.

## v97–v115 (Jun 2026)

- **v97** — FlyTime Lab dashboard on Teams tab; ledger stores rating, engine type, threshold.
- **v98–v111** — FlyTime v1 engines rolled out for all major sports and soccer leagues; tennis removed from feeds; StatFly→ScoreFly rebrand in docs; onboarding redesign; FlyMode up to 8 games; team halos; notification defaults.
- **v112** — 13 new ESPN leagues (J1, League One/Two, CSL, Belgian, Swiss, Greek, Serie B, Saudi, Russian, CFL, URC, Top 14) with FlyTime v1 tables.
- **v115** — Australian NBL live feed (`basketball/nbl`) + `nbl-flytime-v1.json`; FlyTime Lab enabled in production via `?flylab=1` (persists in localStorage); `DEBUG_FLY = false`; fly terminology aligned (yellow/green/red/blue).

## v96 - backlog completion (Jun 2026)

- Global LIVE pill in header (`#global-live`) on all tabs when `ALL_LIVE.length > 0`.
- Per-team `+` quick-add on live/upcoming cards, search results, onboarding picks, suggested teams.
- Onboarding polish: 3-step progress dots, hero caption, notifications headline.
- FlyTime blowout buffer: `FLY_BLOWOUT_MARGIN` releases pin/green lock; after-match stamp kept.
- `DEBUG_FLYSCORES` set to false for production.

## Open items (remaining)

### Verify on live match days (highest priority)

- **FlyTime yellow/green/red flies** — watch close finishes with the app open; confirm yellow on upcoming, green live, red on Results. Use FlyTime Lab (`?flylab=1` → Teams tab) to tune per-league thresholds in `FLY_V1_REGISTRY`.
- **NBL** — first live season test of new `basketball/nbl` feed + threshold 70.
- **13 Jun 2026 soccer/rugby/CFL slugs** — spot-check on match days.
- AFL parser, cricket parser, FlyTime notifications on iPhone PWA.

### FlyState momentum – pending live verification

- Watch real games; compare colour mix to targets (Orange common, Red rare, less White); adjust `MOM_*` tuning block if needed.
- Drought Blue: confirm basketball 4 min / AFL 12 min behave live; watch for false Blue after halftime.
- AFL TV labels on live AFL match.

### Pre-existing dead suggestions in search UI

Discovery lists still surface leagues with no feeds:

- ‘Global’ list: Formula 1, ICC Cricket (ODI), ICC Cricket (T20), Six Nations Rugby, Golf Majors
- Australia: Big Bash League, Super Rugby Pacific (NRL and NBL are now live)
- South Africa: SA T20 Cricket
- Pakistan: Pakistan Super League
- New Zealand: Super Rugby Pacific

User has not asked for a cleanup sweep. Mention if it comes up.

### Repo cleanup

Delete `feed-research.html` and `.nojekyll` when convenient.

### More sports / leagues

- **Cheap ESPN adds** (same `ESPN_FEEDS` pattern): Bundesliga 2 (`ger.2`), Eredivisie 2 (`ned.2`), USL Championship, NWSL, more ESPN+ soccer.
- **NASCAR** – confirmed dead, skip.
- **GAA** – no API, would require scraping (user excluded anyway).
- **BBL** – works on `cricket/8044` Dec-Jan only. Could add seasonally.

### Performance (only if cold load feels slow)

- Cold load is now 47 feeds x up to 4 proxies = up to 188 HTTP requests.
- Tiered polling: 12s fast lane while live, full sweep every ~3 min or 60s idle.
- Options if slow: parallelise smarter (fan-out + cancel on first success per feed), per-feed timeout (currently 10s), lazy-load some feeds (only fetch when user follows a team in that league).
- Don’t optimise unless user reports it feels slow.

### Quality / polish

- iPad layout never checked at tablet width.
- Error states when all 4 proxies fail simultaneously.
- Stat ticker facts for newer feeds (likely still NBA/NFL-centric placeholders).
- PWA install test on Android (now that icon512 is wired).

### Strategic / future

- App Store / Play Store launch (linked to FlutterFlow track)
- Analytics (Plausible / GoatCounter)
- Expanded README if discoverability becomes a goal

## Important workflow rule

The `/mnt/project/` copy of `index.html` goes stale fast. At the start of every session, Claude should fetch the current `index.html` from GitHub (or have user upload it) before making edits. Otherwise we lose prior changes – happened once previously with the logos.