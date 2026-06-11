# ScoreFly

**Scores Anywhere. Simple.**

A mobile-first sports scores web app. Live scores, fixtures, and recent results from 47 league feeds — follow any of 746 teams across 20 countries and international competitions. No login, no ads, no clutter.

**Live:** [scorefly.app](https://scorefly.app) · [hammertymm.github.io/scorefly](https://hammertymm.github.io/scorefly)

-----

## What it does

Follow your favourite teams and see everything in one feed.

|Tab         |What you see                                          |
|------------|------------------------------------------------------|
|**Feed**    |Live scores + upcoming fixtures (All: next 14 days)   |
|**Results** |Completed matches (All: last 7 days)                  |
|**Teams**   |Search and follow teams. Manage alerts.               |
|**Fly Mode**|Full-screen scores designed for glancing across a room|

Toggle between **My Teams** and **All** on any tab. In My Teams, the window widens to 30 days back and forward so you never miss one of your teams' games.

When any game is live anywhere, a green **LIVE** pill appears in the header on every tab. Tap it to jump to the Feed.

-----

## FlyState — momentum at a glance

The score numbers change colour to show what's *happening* in a game, not just the score:

- **Green** — FlyTime: a close, late finish worth watching
- **Purple** — a comeback is underway
- **Red** — a team is on fire (a dominant scoring run)
- **Orange** — a team is on a run
- **Yellow** — momentum is building
- **Blue** — a team has gone cold
- **White** — even contest

Coloured **fly icons** on cards show FlyTime status: **yellow fly** = upcoming and predicted close, **green fly** = live in FlyTime, **red fly** = finished after reaching FlyTime.

Turn on a team's bell and ScoreFly sends you one alert the moment its match enters FlyTime. Switch on **FlyTime ALL** to get that alert for *any* close game, not just the teams you follow.

Tap the **+** beside any team on a card or in search to follow it without leaving the screen.

-----

## Leagues covered

ScoreFly pulls live data for **47 league feeds** across soccer, US/Canada major leagues, AFL, NRL, NBL, cricket, tennis, and more. The searchable follow list covers **746 teams and players**.

See `SCOREFLY.md` for the full league list.

-----

## Install on your phone

ScoreFly is a **PWA** (Progressive Web App) — no App Store needed.

1. Open [scorefly.app](https://scorefly.app) in Safari (iOS) or Chrome (Android)
1. Tap **Share** → **Add to Home Screen**
1. Done — it works like a native app and loads instantly from cache

-----

## How it works

- **Data:** ESPN's unofficial public scoreboard API. No API key required.
- **CORS proxies:** Browser fetches rotate through public proxies; the last working proxy is tried first.
- **Polling:** Scores refresh every **12 seconds while games are live**, with a full sweep every ~3 minutes. When nothing is live, it sweeps every 60 seconds.
- **Storage:** Followed teams and alert preferences stay in `localStorage` on your device.
- **Offline:** The app shell and FlyTime research tables are cached by the service worker.

-----

## Fly Mode

Tap the logo button in the bottom nav to enter Fly Mode — a full-screen scoreboard for your followed teams' live matches (plus FlyTime ALL games when that toggle is on). Brightness slider at the bottom. Tap anywhere to exit.

Designed for putting your phone on the table and watching scores update from across the room.

-----

## Files

```
index.html           Main app (all HTML, CSS, and JS in one file)
sw.js                Service worker — offline caching (currently scorefly-v96)
manifest.json        PWA manifest
*-flytime-v1.json    Offline FlyTime predictor tables (per sport/league)
icon192.png / icon512.png
README.md            This file
SCOREFLY.md          Full source-of-truth spec for developers
```

-----

## Tech

- Vanilla HTML, CSS, and JavaScript — no frameworks, no build tools
- Single self-contained app file
- Installable PWA with offline support
- Pure black UI, Inter typeface, brand colour `#06f03c`

-----

*Data from ESPN's public API — not affiliated with ESPN.*
