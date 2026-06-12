#!/usr/bin/env python3
"""Automated validation of is_flytime_live() rules — mirrors index.html isFlyTime().

Run: cd scorefly/flytime-engine && python validate_flytime_rules.py
"""
from __future__ import annotations

from flytime_engine.espn import ParsedMatch
from flytime_engine.flytime import is_flytime_live

AFL_Q4_ELAPSED = 20 * 60


def m(sport: str, period: int = 0, clock_sec: int = 0, clock_raw: str = "",
      home: int = 0, away: int = 0, **kw) -> ParsedMatch:
    return ParsedMatch(
        espn_event_id="test",
        sport=sport,
        league_code="test",
        home_team="Home",
        away_team="Away",
        home_team_id="1",
        away_team_id="2",
        status="live",
        scheduled_at="",
        home_score=home,
        away_score=away,
        period=period,
        clock_raw=clock_raw or str(clock_sec),
        clock_sec=clock_sec,
        cricket_runs_req=kw.get("cricket_runs_req"),
        cricket_overs_left=kw.get("cricket_overs_left"),
    )


TESTS = [
    # Basketball
    ("basketball Q4 4:00 margin 6", m("basketball", 4, 240, home=100, away=94), True),
    ("basketball Q4 4:00 margin 10", m("basketball", 4, 240, home=100, away=90), False),
    ("basketball Q4 0:00 margin 4", m("basketball", 4, 0, home=100, away=96), False),
    ("basketball Q3 4:00 margin 4", m("basketball", 3, 240, home=80, away=76), False),
    # Football
    ("football Q4 2:00 margin 7", m("football", 4, 120, home=21, away=14), True),
    ("football Q4 2:00 margin 12", m("football", 4, 120, home=21, away=9), False),
    # Hockey
    ("hockey P3 4:00 margin 1", m("hockey", 3, 240, home=2, away=1), True),
    ("hockey P3 4:00 margin 2", m("hockey", 3, 240, home=3, away=1), False),
    # Baseball
    ("baseball inn 9 margin 1", m("baseball", 9, 0, home=4, away=3), True),
    ("baseball inn 7 margin 1", m("baseball", 7, 0, home=4, away=3), False),
    # AFL
    ("AFL Q4 20:00 elapsed margin 10", m("australian-football", 4, AFL_Q4_ELAPSED, home=80, away=70), True),
    ("AFL Q4 19:59 elapsed", m("australian-football", 4, AFL_Q4_ELAPSED - 1, home=80, away=70), False),
    ("AFL OT close", m("australian-football", 5, 0, home=90, away=88), True),
    ("AFL OT blowout", m("australian-football", 5, 0, home=100, away=80), False),
    # Rugby
    ("NRL H2 8:00 margin 6", m("rugby-league", 2, 480, home=18, away=12), True),
    ("NRL H2 12:00 margin 6", m("rugby-league", 2, 720, home=18, away=12), False),
    # Soccer
    ("soccer 85' margin 0", m("soccer", 2, 0, clock_raw="85", home=1, away=1), True),
    ("soccer 79' margin 0", m("soccer", 2, 0, clock_raw="79", home=1, away=1), False),
    ("soccer 85' margin 2", m("soccer", 2, 0, clock_raw="85", home=2, away=0), False),
    # Cricket
    ("cricket chase 15 off 1.5", m("cricket", 0, 0, home=150, away=135,
        cricket_runs_req=15, cricket_overs_left=1.5), True),
    ("cricket chase 25 off 2", m("cricket", 0, 0, home=150, away=125,
        cricket_runs_req=25, cricket_overs_left=2.0), False),
    # Tennis excluded
    ("tennis excluded", m("tennis", 3, 0, home=1, away=0), False),
]


def main() -> None:
    passed = failed = 0
    failures = []
    for name, match, expected in TESTS:
        got = is_flytime_live(match)
        if got == expected:
            passed += 1
        else:
            failed += 1
            failures.append(f"  FAIL {name}: expected={expected} got={got}")

    print(f"FlyTime rule validation: {passed} passed, {failed} failed")
    for f in failures:
        print(f)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    import sys
    main()
