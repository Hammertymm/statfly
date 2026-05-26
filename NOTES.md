# StatFly Notes

Running log of decisions, dead ends, and things worth remembering.

## Data sources

### ESPN unofficial API — confirmed working

- NBA: `basketball/nba`
- NFL: `football/nfl`
- MLB: `baseball/mlb`
- NHL: `hockey/nhl`
- MLS: `soccer/usa.1`
- AFL: `australian-football/afl`
- IPL: `cricket/8048`

### Cricket league IDs tested (May 2026)

- `cricket/8048` — IPL (live, in-season)
- `cricket/23694` — International tours (e.g. NZ tour of India)
- `cricket/8044` — Big Bash League (off-season May-Nov, live Dec-Jan)
- `cricket/8039` — Returns stale World Cup data (skip)
- `cricket/19429` — Returns random old matches (skip)
- `cricket/all` — empty
- `cricket/8047` — empty

### Endpoints tested and NOT viable

- **NRL** — tested `rugby/3`, `rugby/nrl`, `rugby-league/nrl`, `rugby/league/3`, `rugby/270557`.
  All proxies return either HTTP 403 or 0 events with no league metadata.
  ESPN’s website shows NRL but the public API does not expose it.
  Would need a paid API (API-Sports, SportsRadar) or alternative free source (TheSportsDB).