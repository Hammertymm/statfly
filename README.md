# ScoreFly ⚡

**Scores Anywhere. Simple.**

A mobile-first sports scores web app. Live scores, fixtures, and recent results from 35 leagues — follow any of 619 teams across 19 countries and international competitions. No login, no ads, no clutter.

**Live:** [hammertymm.github.io/statfly](https://hammertymm.github.io/statfly)
*(custom domain `scorefly.app` coming soon)*

-----

## What it does

Follow your favourite teams and see everything in one feed.

|Tab         |What you see                                          |
|------------|------------------------------------------------------|
|**Feed**    |Live scores + upcoming fixtures (All: next 14 days)   |
|**Results** |Completed matches (All: last 7 days)                  |
|**Teams**   |Search and follow teams. Manage alerts.               |
|**Fly Mode**|Full-screen scores designed for glancing across a room|

Toggle between **My Teams** and **All** on any tab. In My Teams, the window widens to 30 days back and forward so you never miss one of your teams’ games.

-----

## FlyState — momentum at a glance

The score numbers change colour to show what’s *happening* in a game, not just the score:

- **Green** — FlyTime: a close, late finish worth watching
- **Purple** — a comeback is underway
- **Red** — a team is on fire (a dominant scoring run)
- **Orange** — a team is on a run
- **Yellow** — momentum is building
- **Blue** — a team has gone cold
- **White** — even contest

Turn on a team’s bell and ScoreFly sends you one alert the moment its match enters FlyTime, so you never miss a great finish. Switch on **FlyTime Buzz** to get that alert for *any* close game, not just the teams you follow.

-----

## Leagues covered

ScoreFly pulls live data for **35 league feeds**:

**US / Canada** — NFL, NBA, MLB, NHL, MLS, WNBA, NCAAM, NCAAF

**Soccer — Europe** — Premier League, La Liga, Bundesliga, Serie A, Ligue 1, Championship, Eredivisie, Primeira Liga, Scottish Premiership, Süper Lig, Champions League, Europa League, Women’s Super League

**Soccer — Americas** — Brasileirao, Liga Profesional, Liga MX, Copa Libertadores

**Soccer — Other** — A-League, League of Ireland, Indian Super League, PSL (South Africa)

**Other** — AFL, NRL, IPL cricket, international cricket, ATP tennis, WTA tennis

The searchable follow list goes wider still — **40 competitions, 619 teams and players in total** — adding the Big Bash League, NBL, Super Rugby Pacific, Six Nations, Copa do Brasil, the Pakistan Super League and more for following teams.

-----

## Install on your phone

ScoreFly is a **PWA** (Progressive Web App) — no App Store needed.

1. Open [hammertymm.github.io/statfly](https://hammertymm.github.io/statfly) in Safari (iOS) or Chrome (Android)
1. Tap **Share** → **Add to Home Screen**
1. Done — it works like a native app and loads instantly, even offline

-----

## How it works

- **Data:** ESPN’s unofficial public scoreboard API. No API key required.
- **CORS proxies:** Browser fetches rotate through `corsproxy.io`, `allorigins`, `codetabs`, and `thingproxy`. The last working proxy is tried first; if it fails, the rest race and the winner is remembered.
- **Polling:** Scores refresh every **12 seconds while games are live**, with a full sweep every ~3 minutes to catch kickoffs and finishes. When nothing is live, it sweeps every 60 seconds.
- **Storage:** Followed teams and alert preferences are saved in `localStorage` — nothing leaves your device.
- **Offline:** The app shell is cached by the service worker so it loads instantly every time.

-----

## Fly Mode

Tap the logo button in the bottom nav to enter Fly Mode — a full-screen scoreboard showing only your followed teams’ live matches. Brightness slider at the bottom. Tap anywhere to exit. (The rivalry skull marker appears on upcoming fixtures in the feed, not on live games or Fly Mode.)

Designed for putting your phone on the table and watching scores update from across the room.

-----

## Files

```
index.html      Main app (all HTML, CSS, and JS in one file)
sw.js           Service worker — offline caching
manifest.json   PWA manifest — makes it installable
icon192.png     App icon (192x192)
icon512.png     App icon (512x512)
icon-*.png      Per-sport fallback icons
README.md       This file
```

-----

## Tech

- Vanilla HTML, CSS, and JavaScript — no frameworks, no build tools, no dependencies
- Single self-contained file
- Installable PWA with offline support
- Pure black UI, Inter typeface, brand colour `#30d158`

-----

*Data from ESPN’s public API — not affiliated with ESPN.*