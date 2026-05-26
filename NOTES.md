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

### Endpoints tested and NOT viable

- **NRL** — tested `rugby/3`, `rugby/nrl`, `rugby-league/nrl`, `rugby/league/3`, `rugby/270557`.
  All proxies return either HTTP 403 or 0 events with no league metadata.
  ESPN’s website shows NRL but the public API does not expose it.
  Would need a paid API (API-Sports, SportsRadar) or alternative free source (TheSportsDB).