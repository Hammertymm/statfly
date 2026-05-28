# StatFly ⚡

**Scores Anywhere. Simple.**

A mobile-first sports scores web app. Live scores, upcoming fixtures, and recent results across 34 leagues — no login, no ads, no clutter.

**Live:** [hammertymm.github.io/statfly](https://hammertymm.github.io/statfly)

-----

## What it does

Follow your favourite teams and see everything in one feed.

|Tab         |What you see                                          |
|------------|------------------------------------------------------|
|**Feed**    |Live scores + upcoming fixtures (next 14 days)        |
|**Results** |Completed matches (last 4 days)                       |
|**Teams**   |Search and follow teams. Manage alerts.               |
|**Fly Mode**|Full-screen scores designed for glancing across a room|

Toggle between **My Teams** (just the teams you follow) and **All** on any tab.

-----

## Leagues covered

**US / Canada** — NFL, NBA, MLB, NHL, MLS, WNBA, NCAAM, NCAAF

**Soccer — Europe** — Premier League, La Liga, Bundesliga, Serie A, Ligue 1, Championship, Eredivisie, Primeira Liga, Scottish Premiership, Super Lig, UCL, UEL, WSL

**Soccer — Americas** — Brasileirao, Liga Profesional, Liga MX, Copa Libertadores

**Soccer — Other** — A-League, League of Ireland, ISL, PSL

**Other** — AFL, IPL cricket, International cricket, ATP tennis, WTA tennis

-----

## Install on your phone

StatFly is a **PWA** (Progressive Web App) — no App Store needed.

1. Open [hammertymm.github.io/statfly](https://hammertymm.github.io/statfly) in Safari (iOS) or Chrome (Android)
1. Tap **Share** → **Add to Home Screen**
1. Done — it works like a native app and loads instantly, even offline

-----

## How it works

- **Data:** ESPN’s unofficial public scoreboard API. No API key required.
- **CORS proxies:** Browser fetches rotate through `corsproxy.io`, `allorigins`, `codetabs`, and `thingproxy`. First successful response wins.
- **Polling:** Scores refresh every 60 seconds while the tab is visible.
- **Storage:** Followed teams and alert preferences are saved in `localStorage` — nothing leaves your device.
- **Offline:** The app shell is cached by the service worker so it loads instantly every time.

-----

## Fly Mode

Tap the logo button in the bottom nav to enter Fly Mode — a full-screen scoreboard showing only your followed teams’ live matches. Brightness slider at the bottom. Tap anywhere to exit.

Designed for putting your phone on the table and watching scores update from across the room.

-----

## Files

```
index.html      Main app (all HTML, CSS, and JS in one file)
sw.js           Service worker — offline caching
manifest.json   PWA manifest — makes it installable
icon192.png     App icon (192x192)
icon512.png     App icon (512x512)
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
