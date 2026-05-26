# StatFly Notes

Running log of decisions, dead ends, and things worth remembering.

## Hosting & deploy

- **Live URL:** <https://hammertymm.github.io/statfly>
- **Repo:** <https://github.com/Hammertymm/statfly>
- **Hosting:** GitHub Pages (Netlify abandoned — credits ran out)
- **Deploy:** edit files in GitHub via Safari, commit, wait ~30s, refresh phone
- **Cache:** bump `CACHE` constant in `sw.js` every deploy that touches HTML/CSS/JS/icons. Currently `statfly-v20`.

## Current feeds (11 live)

NBA, NFL, MLB, NHL, MLS, EPL, La Liga, UCL, AFL, IPL, Cricket (international tours).

## Data sources

### ESPN unofficial API — confirmed working

- NBA: `basketball/nba`
- NFL: `football/nfl`
- MLB: `baseball/mlb`
- NHL: `hockey/nhl`
- MLS: `soccer/usa.1`
- Premier League: `soccer/eng.1`
- La Liga: `soccer/esp.1`
- UEFA Champions League: `soccer/uefa.champions`
- AFL: `australian-football/afl`
- IPL: `cricket/8048`
- International cricket: `cricket/23694`

### Cricket league IDs tested (May 2026)

- `cricket/8048` — IPL (live, in-season)
- `cricket/23694` — International tours (e.g. NZ tour of India)
- `cricket/8044` — Big Bash League (off-season May-Nov, live Dec-Jan)
- `cricket/8039` — Returns stale World Cup data (skip)
- `cricket/19429` — Returns random old matches (skip)
- `cricket/all` — empty
- `cricket/8047` — empty

### Soccer tested

- `soccer/all` — works, returns ~23 events globally, but groups everything under one label in the UI. Not used.
- Individual league slugs (`eng.1`, `esp.1`, `uefa.champions`, `ger.1`) all work via codetabs proxy.

### Endpoints tested and NOT viable

- **NRL** — tested `rugby/3`, `rugby/nrl`, `rugby-league/nrl`, `rugby/league/3`, `rugby/270557`.
  All proxies return either HTTP 403 or 0 events with no league metadata.
  ESPN’s website shows NRL but the public API does not expose it.
  Would need a paid API (API-Sports, SportsRadar) or alternative free source (TheSportsDB).

## Backlog decisions (locked)

Items deliberately dropped, not to be reopened without good reason:

- **Match detail view** — undermines glance-and-go positioning. Cards stay simple.
- **Notification settings (per-team granularity)** — over-engineering. Bell is binary.
- **Push notifications backend** — would turn the app into a real backend product. Not before there are users who care.
- **Favourites sync across devices** — auth complexity not worth it for a phone-first scores app.
- **Score worms (all sports, all match states)** — never using any kind of worm. Stripped from code in v20.
- **Cricket second-innings worm** — covered by above.

Items parked, with triggers:

- **Onboarding flow** — required before any public launch. Memory note set; Claude will raise this when launch comes up.

## Recent bug fixes / changes

### v20 — Worm removal + expand removal (this session)

- Deleted entire `buildWorm` function (~180 lines) and worm CSS block.
- Stripped `worm` and `wormOpts` fields from match base factory.
- Removed `toggleExpand` / `closeAllExpanded` and the tap-elsewhere overlay.
- Cards no longer expand. Live cards end at the summary line. Upcoming cards render facts inline below summary when present. Result cards unchanged in shape, just no worm section.
- `.card.expanded` guard removed from swipe gesture handler.
- File shrunk from 1784 to 1542 lines.
- Unicode safety and page structure checks both clean.

### v19 — PWA icon completion

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

Files in repo: `index.html`, `sw.js`, `manifest.json`, `icon192.png`, `icon512.png`, `README.md`, `NOTES.md`

## Open items (full list)

### Verify on live match days

- AFL parser on next live match
- Cricket parser on live IPL match

### More sports / leagues

- **Cheap ESPN adds** (same `ESPN_FEEDS` pattern): Bundesliga, Serie A, Ligue 1, Europa League, NCAA men’s basketball, NCAA football, WNBA, MMA, golf, tennis, F1, NASCAR.
- **NRL** — confirmed dead via ESPN, skip.
- **GAA** — no API, would require scraping.
- **BBL** — works on `cricket/8044` Dec-Jan only. Could add seasonally.

### Performance (only if cold load feels slow)

- 11 feeds × up to 4 proxies = up to 44 HTTP requests on cold load.

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

The `/mnt/project/` copy of `index.html` goes stale fast. At the start of every session, Claude should fetch the current `index.html` from GitHub (or have user upload it) before making edits. Otherwise we lose prior changes — happened once previously with the logos.