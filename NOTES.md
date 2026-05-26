# StatFly Notes

Running log of decisions, dead ends, and things worth remembering.

## Hosting & deploy

- **Live URL:** <https://hammertymm.github.io/statfly>
- **Repo:** <https://github.com/Hammertymm/statfly>
- **Hosting:** GitHub Pages (Netlify abandoned — credits ran out)
- **Deploy:** edit files in GitHub via Safari, commit, wait ~30s, refresh phone
- **Cache:** bump `CACHE` constant in `sw.js` every deploy that touches HTML/CSS/JS/icons. Currently `statfly-v19`.

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

## Recent bug fixes

### v19 — PWA icon completion (this session)

- Added `icon512.png` to repo (downscaled from 1254x1254 master via Lanczos).
- `manifest.json` icons array now includes both 192 and 512.
- `sw.js` SHELL includes `/icon512.png`; CACHE bumped to `statfly-v19`.

### Date sanity in `espnStatus` (v17)

Past matches were appearing in Coming Up because ESPN sometimes returns non-FINAL status for completed games. Fix: if status isn’t IN_PROGRESS/HALFTIME/FINAL but event date is in the past, classify as ‘finished’. Result: cleanly routed to Results bucket and filtered by 4-day window.

### Result card cleanup (v18)

Removed two sources of dead space:

- `wormType: 'none'` no longer renders a “SCORE CHART / Live chart coming soon” placeholder. Returns empty string instead.
- Duplicate `card-sum` line at bottom of result card removed (summary appeared twice per card).

### Logo (v18)

Both header logo (`.brand-mark`) and tab bar fly (`.nb-flymode > img`) replaced with the circular Superman-fly. Same base64 image used in both spots.

## Repo state (end of this session)

- Test files removed: `nrl-test.html`, `nrl-test2.html`, `soccer-test.html`, `cricket-test.html`
- Old docs retired: `StatFly_skill.md` superseded by consolidated `STATFLY.md`
- Files in repo: `index.html`, `sw.js`, `manifest.json`, `icon192.png`, `icon512.png`, `NOTES.md`, `README.md`

## Open items (full list)

### Verify on live match days

- AFL parser on next live match
- Cricket parser on live IPL match (runs/wickets/overs may render wrong)

### More sports / leagues

- **NRL** — confirmed dead via ESPN. Skip unless committing to a paid API or TheSportsDB.
- **Cheap ESPN adds** (same `ESPN_FEEDS` pattern): Bundesliga, Serie A, Ligue 1, Europa League, NCAA men’s basketball, NCAA football, WNBA, MMA, golf, tennis, F1, NASCAR.
- **GAA** — no API, would require scraping.
- **BBL** — works on `cricket/8044` Dec-Jan only. Could add seasonally.

### Performance

- Cold load: 11 feeds × up to 4 proxies = up to 44 HTTP requests. Parallelise or cache if it feels slow.

### Quality / polish

- iPad layout — app is mobile-first, hasn’t been checked at tablet width.
- Error states — verify empty state is friendly when all 4 proxies fail simultaneously.
- Stat ticker content — facts may still be NBA/NFL-centric placeholders for the 6 newer feeds (EPL, La Liga, UCL, AFL, IPL, Cricket).
- Test PWA install on Android now that icon512 is wired.

### Backlog from older planning docs

- Match detail view on card tap
- Onboarding flow for new users
- Notification settings page (manage alerts per team)
- Second-innings worm for cricket results
- Push notifications backend (FCM or Supabase)
- Favourites sync across devices (needs auth)

### Strategic / future

- App Store / Play Store launch (linked to FlutterFlow track)
- Analytics — zero visibility on usage. Plausible / GoatCounter are privacy-respecting options.
- README.md is one sentence — fine for now, expand if discoverability matters later.

## Important workflow rule

The `/mnt/project/` copy of `index.html` goes stale fast. At the start of every session, Claude should fetch the current `index.html` from GitHub (or have user upload it) before making edits. Otherwise we lose prior changes — happened once previously with the logos.