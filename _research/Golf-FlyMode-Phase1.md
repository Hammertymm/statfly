# Golf FlyMode — Phase 1 Feasibility (PGA / LIV)

**Status:** Spike complete (architecture only). Full FlyMode implementation deferred to Phase 2.

## Why golf was removed (v23/v27)

Tournament leaderboard data does not fit the team-vs-team card model. ESPN golf events expose a **field** of players, not head-to-head matches.

## ESPN data path

```
GET https://site.api.espn.com/apis/site/v2/sports/golf/pga/scoreboard
GET https://site.api.espn.com/apis/site/v2/sports/golf/liv/scoreboard
```

Typical live fields per competitor:

| Field | Use in ScoreFly |
|-------|-----------------|
| `athlete.displayName` | Follow target / card title |
| `score` | Total strokes |
| `linescores[]` | Round/hole progression |
| `status.displayValue` | "Thru 14", "F", "WD" |
| `statistics[]` | Score to par when available |
| Leaderboard position | vs leader margin |

## Proposed card (individual golfer follow)

- **Current hole:** parse `status.displayValue` (Thru N) or sum linescores
- **Score vs par:** from ESPN stats or derive from par table
- **vs leader:** leader total − player total

## FlyTime for golf (recommended)

| Fly | Trigger |
|-----|---------|
| Yellow | Historical close-finish rate for event/course (new `golf-*-flytime-v1.json`) |
| Green | Final round, back nine, within 2 strokes of leader |
| FlySense | Strokes gained per hole normalized by `thru` delta (separate `updateGolfFlyState`) |

Standings movement **should** drive golf FlySense (position delta per poll), not team-sport `updateFlyState`.

## Phase 2 scope (not in this sprint)

1. `ESPN_FEEDS` entries for PGA + LIV
2. Golfer search in Teams tab (athlete IDs)
3. Leaderboard FlyMode grid (1–8 followed players)
4. Golf-specific FlyTime + FlySense engines
5. FlyTime v1 JSON tables per tour

## Phase 1 validation performed

- Confirmed ESPN golf scoreboard endpoint shape (leaderboard, not match pairs)
- Documented field mapping and trigger methodology
- Decision: **defer implementation** until product approves tournament UI divergence

## Risks

- ESPN slug stability (`golf/liv` vs `golf.liv`)
- No game clock — momentum must use holes/thru only
- Multi-day events need day/round state in cards
