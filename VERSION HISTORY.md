# ScoreFly — Version History (V1 → V76)

**Sources:** reconstructed from SCOREFLY.md’s changelog, the v69–v75 session handover, and the v76 session.

**Honesty note:** The recorded changelog only begins at **v20**. Everything before that, plus several intermediate cache bumps and sessions whose notes were never captured, has **no surviving record** — those are marked as gaps below rather than invented. Some versions were only ever logged as ranges (e.g. v20–v25); they’re kept as ranges here for the same reason.

The app began life as **StatFly** and was rebranded to **ScoreFly** by v50. The GitHub repo and Pages URL were renamed to `scorefly` in 2026; custom domain is `scorefly.app`.

-----

## Pre-changelog era

**V1 – V19 — Not recorded.**
No changelog exists for these. What the later entries imply was already present by ~v19: the working app itself, Fly Mode, “score worms” and card expand/collapse (both removed at v20), and an initial set of soccer feeds. The specific per-version changes are unknown and are not reconstructed here.

-----

## v20 – v39 — Foundations, data reliability, FlyState begins

**v20 – v25** — Score worms removed; card expand/collapse removed; soccer league slugs added (feed count up to ~36).

**v26 – v27** — Fly Mode redesign; discovery cleanup (F1 and Golf Majors removed).

**v28 – v34 — Not individually recorded** (gap between v27 and v35).

**v35** — Data-freshness line added at top of Feed; dead stat-ticker removed; font loading moved into `<head>`.

**v36** — 7-day fetch window via `?dates=` range; upcoming filter narrowed 14 → 7 days.

**v37** — Logo fallback fix.

**v38** — AFL proper club names on cards + 3-letter TV codes in Fly Mode.

**v39** — Data-reliability pass: tiered self-rescheduling polling; 8s auto-retry after a failed cycle; smart proxy rotation; narrow fast-lane window; immediate refresh on returning to the app.

-----

## v40 – v49 — FlyState V2, windows, rebrand groundwork

**v40 – v42** — FlyState V2 group work: basketball possession-model FlyTime; AFL/soccer timing; NRL integration.

**v43 – v44** — FlyState V2: momentum threshold re-tune; independent drought-based Blue (gone cold) for basketball and AFL; comeback detection improvements.

**v45** — FlyTime Buzz alerts; adaptive polling dropping to 20s during FlyTime; rivalry skull marker in Fly Mode; AFL TV abbreviations.

**v46 — Intermediate cache bump** (details not captured).

**v47** — Team-name consistency pass (full official names across TEAMS + RIVALRIES); onboarding suggested teams restructured (3 same city / 3 same country different sport / 2 rivalry); “Suggested for you” hidden after onboarding; NHL Arizona Coyotes replaced with Utah Hockey Club.

**v48** — Two-tier date windows: All view = 14 days ahead / 7 back; My Teams view = 30 / 30, fetched deep only for leagues holding a followed team.

**v49 — Not recorded** (off-doc intermediate).

-----

## v50 – v60 — ScoreFly brand, onboarding, FlyTime ALL (formerly Buzz), Fly Mode redesign

**v50** — **ScoreFly rebrand** present in code: wordmark, storage keys (`scorefly_*`), cache key (`scorefly-v50`). (Detailed change list for this version not logged.)

**v51** — Onboarding redesigned around FlyTime and the **SupaFly** mascot: 4 screens (Welcome, Meet FlyTime, Pick teams, Notifications); SupaFly pose PNGs added and pre-cached.

**v52** — Pinned “Worth watching now” FlyTime section at the top of Feed; scrolling FlyTime marquee replaced with a static green badge (feed + Fly Mode).

**v53** — FlyTime Buzz notification redesign: new copy, debounced batching of simultaneous crossings, 3-per-15-minute cooldown, tap opens the FlyTime section.

**v54** — After-match Fly stamp: matches the app sees enter FlyTime are recorded and stamped on Results (35-day prune).

**v55** — Display-only short names on cards for four long AFL/NRL teams; rivalry skull gated to upcoming fixtures only (off on live + Fly Mode); NRL form boxes enabled.

**v56 – v57 — Not individually recorded** (cache reached v57 before v58).

**v58** — Fly Mode “Split Tiles” redesign: each match becomes two half-tiles meeting at a centre seam with a period/clock pill, each tile washed in its side’s FlyState colour.

**v59** — Fly Mode score sizing reworked so the number fills the cell in every formation.

**v60** — Branded-asset + icon pass: fly emoji replaced with the circular SupaFly logo where it was a visible glyph; search/onboarding rows route league icons through the sport-icon images; NRL form-fetch refactor.

-----

## v61 – v68 — FlyTime indicator lock, onboarding engine

**v61 – v65 — Not individually recorded** (cache advanced to v65 before v66; change details not captured).

**v66** — FlyTime indicator rebuilt as a single coloured fly icon (**locked spec**): green = live and in FlyTime, yellow = upcoming and predicted (via `computeFlyMatch`), red = finished and reached FlyTime. Retired the old green banner, results pill, and SupaFly “FlyMatch” corner badge.

**v67** — Onboarding recommendation engine made data-driven (added `METRO_TEAMS`) and upgraded to the 2-local / 2-same-country / 2-same-league spec; yellow-fly calibration fix (match importance changed from an averaged term to an additive bonus; threshold lowered 3.5 → 3.0).

**v68** — Single-hero onboarding (`onboard-hero.png`) → choose teams → notifications; `MAJOR_CLUBS` expanded with ~50 household names; local picks surfaced in authored prominence order.

-----

## v69 – v76 — Pixel-match, touch-ups, alignment

**v69 – v74 — Card UI pixel-match** *(logged as a phase, not per-version).* Feed/Results cards matched to reference screenshots by forensic measurement. Final metrics: card gap 9px, height ~105px, border 1px, radius 8px; team name 14px/600; score 18px/700; logo container 18px (img 15px); wordmark 27px; brand-mark 46px circle; tabs 14px; card background `#080808`. **Brand green changed `#30d158` → `#06f03c`** (all `rgba` literals swapped). Results tab inherits the shared card CSS.

**v75 — “Final Touch-Up,” 11 items:**

1. FlyTime ALL notification copy — title “FlyTime ALL”, body “X vs Y has entered FlyTime” / “N games have entered FlyTime”.
1. Fly Mode mixes in non-followed FlyTime games **only when FlyTime ALL is ON**.
1. Fly Mode pins FlyTime games to the top until the match completes.
1. Team-logo plate opacity .07 → .10.
1. Removed the Teams-screen subtitle.
1. Onboarding redesign — **held** (post-beta).
1. Poll tiers: 8s FlyTime / 12s live / 30s starting-soon / 60s idle.
1. Fly Mode nav icon +20% (40 → 48px) + static green drop-shadow.
1. Brightness slider hit area 36 → 50px tall (invisible; look unchanged).
1. WNBA made searchable/followable (added to USA group, 13 teams) — fixed the Atlanta Dream bug.
1. Red fly on Results for matches that hit FlyTime (confirmed already in place).

**v76 (current) — UI alignment & polish, 6 CSS/markup tweaks** *(no JavaScript changed):*

- **#1** Freshness band tightened (bottom padding 7 → 3px); still Feed-only.
- **#3** Upcoming team names aligned to live/results cards (logo gap 8 → 10); form dots aligned flush under the name (indent 30 → 28).
- **#4** League badge top-anchored (`.card-meta` align-items → flex-start) so its position is identical on Feed and Results regardless of the LIVE pill’s height.
- **#6** Section-spacing tokens `--sec-mt` / `--sec-mb` (12px / 7px) now drive every section header (Live Now, Coming Up, Results, TODAY/YESTERDAY).
- **#8** Countdown reduced 22 → 20px.
- **#10** Header baseline lockup “D”: fly mark stays centred on “ScoreFly”; tagline drops to share ScoreFly’s baseline.

*Items dispositioned but not built in v76: #2 (document card variants) and #7 (formalise freshness spec) are doc-only and pending the SCOREFLY.md sync; #5 (FlyTime placement) and #11 (status-badge width) were no-change; #9 (yellow border optical weight) was held.*

-----

## Gaps at a glance (not invented)

|Range    |Status                                          |
|---------|------------------------------------------------|
|V1 – V19 |No changelog — pre-documentation                |
|v28 – v34|Not individually recorded                       |
|v46      |Cache bump only — details not captured          |
|v49      |Off-doc intermediate                            |
|v56 – v57|Not individually recorded                       |
|v61 – v65|Not individually recorded                       |
|v69 – v74|Logged as one pixel-match phase, not per-version|