# StatFly Notes

Running log of decisions, dead ends, and things worth remembering.

## Hosting & deploy

- **Live URL:** <https://hammertymm.github.io/statfly>
- **Repo:** <https://github.com/Hammertymm/statfly>
- **Hosting:** GitHub Pages (Netlify abandoned – credits ran out)
- **Deploy:** edit files in GitHub via Safari, commit, wait ~30s, refresh phone
- **Cache:** bump `CACHE` constant in `sw.js` every deploy that touches HTML/CSS/JS/icons. Currently `statfly-v25`.

## Current feeds (34 live)

**US/CA (8):** NBA, NFL, MLB, NHL, MLS, WNBA, NCAAM, NCAAF
**Soccer Europe (12):** EPL, La Liga, Bundesliga, Serie A, Ligue 1, Championship, Eredivisie, Primeira Liga, Scottish Premiership, Super Lig, UCL, UEL, WSL
**Soccer Americas (4):** Brasileirao, Liga Profesional, Liga MX, Libertadores
**Soccer other (4):** A-League, League of Ireland, ISL, PSL
**Australian (1):** AFL
**Cricket (2):** IPL, International cricket
**Tennis (2):** ATP, WTA

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

Other:

- AFL: `australian-football/afl`
- IPL: `cricket/8048`
- International cricket: `cricket/23694`
- ATP: `tennis/atp`
- WTA: `tennis/wta`

### Slugs added v25 – not yet observed live

All 14 of: Championship, Eredivisie, Primeira Liga, Scottish Premiership, Super Lig, Brasileirao, Liga Profesional, Liga MX, A-League, League of Ireland, ISL, PSL, Libertadores, WSL. Based on ESPN’s `<country>.<tier>` convention or URLs confirmed via search results. None tested with live matches.

Higher risk: `ind.1` (ISL, Sept-April), `rsa.1` (PSL, Aug-May), `conmebol.libertadores` (longer slug, may need `.cup` suffix).

To audit a specific slug: search for a known team in that league (e.g. “Boca Juniors” for arg.1, “Bohemian” for irl.1). If you can follow it but never see matches, the slug is dead.

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

- **NRL** – tested `rugby/3`, `rugby/nrl`, `rugby-league/nrl`, `rugby/league/3`, `rugby/270557`. All proxies return either HTTP 403 or 0 events with no league metadata. ESPN’s website shows NRL but the public API does not expose it. Would need a paid API (API-Sports, SportsRadar) or alternative free source (TheSportsDB).
- **NASCAR** – `nascar-cup-series` tested in v21, 5/5 proxies dead. Removed in v22.

### Sports dropped by user (not technical failures)

- UFC, PGA, F1 (v23) – render risk on tournament-shaped data.
- GAA Football, GAA Hurling (v24) – excluded from Ireland suggestions; no API anyway.

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

## Recent bug fixes / changes

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

Files in repo: `index.html`, `sw.js`, `manifest.json`, `icon192.png`, `icon512.png`, `README.md`, `NOTES.md`, `.nojekyll`, `feed-research.html`

`.nojekyll` and `feed-research.html` were added in v25 for a research tester that didn’t end up being used (Safari caching issue). Both can be deleted when convenient – neither is needed for the app.

## Open items (full list)

### Verify on live match days

- AFL parser on next live match
- Cricket parser on live IPL match
- 14 v25 soccer slugs (highest priority next session)

### Pre-existing dead suggestions in search UI

Discovery lists still surface leagues with no feeds:

- ‘Global’ list: Formula 1, ICC Cricket (ODI), ICC Cricket (T20), Six Nations Rugby, Golf Majors
- Australia: NRL, Big Bash League, Super Rugby Pacific, NBL
- South Africa: SA T20 Cricket
- Pakistan: Pakistan Super League
- New Zealand: Super Rugby Pacific
- England: WSL is NOW backed by `eng.w.1` – verify it shows real matches

User has not asked for a cleanup sweep. Mention if it comes up.

### Repo cleanup

Delete `feed-research.html` and `.nojekyll` when convenient.

### More sports / leagues

- **Cheap ESPN adds** (same `ESPN_FEEDS` pattern): Bundesliga 2 (`ger.2`), Eredivisie 2 (`ned.2`), USL Championship, NWSL, more ESPN+ soccer.
- **NRL** – confirmed dead via ESPN, skip.
- **NASCAR** – confirmed dead, skip.
- **GAA** – no API, would require scraping (user excluded anyway).
- **BBL** – works on `cricket/8044` Dec-Jan only. Could add seasonally.

### Performance (only if cold load feels slow)

- Cold load is now 34 feeds x up to 4 proxies = up to 136 HTTP requests. Previously flagged 44 as a watch point.
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