# Phase 7 - Scalability

The model: a static PWA on GitHub Pages, each client polling ESPN directly through free public CORS proxies, with notifications fired from page context. No backend. Evaluated at 10k / 100k / 1M users.

---

## 7.1 What scales for free

- **App shell + assets** are static files on GitHub Pages (`index.html`, `sw.js`, icons, 45 JSON tables, `team-halo-config.json`, ~812 logo PNGs per `sw.js:106`). Served from a CDN; once cached by the SW, near-zero repeat cost. GitHub Pages soft-limits ~100GB/month bandwidth and ~10 builds/hour, but **reads are cached client-side after first load**, so asset serving is not the first ceiling.
- **Compute** is entirely client-side; each user pays their own CPU. No server compute to scale.

So the static-hosting side is genuinely cheap. The ceilings are all in the **data path** and **notifications**.

---

## 7.2 The first bottleneck: free CORS proxies

**Current implementation:** `proxyUrls` (`index.html:1238`) routes every ESPN request through `corsproxy.io`, `allorigins`, `codetabs`, or `thingproxy` (plus a direct attempt). `espnFetch` (`1281`) sends ~48 feed requests per full sweep and N live-feed requests per fast lane, cache-busted (`_=Date.now()`).

**Load math (order of magnitude):**
- One active user with live games: fast lane every 4s (or 1s in Fly Mode) x live feeds, plus a full 48-feed sweep every ~60s. Call it ~10-50 proxied requests/min/active user.
- **10k concurrent actives:** ~0.1-0.8M proxied requests/min. The free proxies (especially `corsproxy.io`/`allorigins`) will rate-limit or block this volume from shared origins; reliability degrades.
- **100k:** the free proxies are not viable - they are shared community services, not infrastructure. Expect bans, 429s, and intermittent outages. The app's racing fallback (`1294-1326`) masks individual proxy failure but cannot survive all of them throttling.
- **1M:** impossible on free proxies.

**This is the first ceiling, and it bites well before 100k.** It is also outside the team's control (third-party free services). 

**Mitigations within the no-backend doctrine:**
- Persisting `bestProxyIdx` to localStorage (already done, `1276`/`1304`) reduces cold-start probing - good.
- Lengthen poll tiers (Phase 5.8) to cut request volume per user.
- But fundamentally, **a self-hosted CORS proxy / edge function (e.g. a Cloudflare Worker or the parked Oracle box) becomes necessary somewhere between 1k-10k actives.** That is the point the "future backend" stops being optional. This crosses the single-file *app* rule only at the infra layer (the proxy is not part of `index.html`), so it does not violate the PWA architecture.

**Impact 8 (existential at scale) / Effort 6 / Risk 5.**

---

## 7.3 Per-user direct-to-ESPN polling load

Even with a proxy solved, **every client independently fetches the same 48 public scoreboards.** 10k users watching the same NBA night each pull the same NBA feed every few seconds - 10k identical requests for one piece of data. ESPN's unofficial API has no contract and will throttle by IP/origin under that load.

**The efficient architecture at scale is fan-in:** one server fetches each feed once per tier and fans the result out to all clients (SSE/websocket or a cached JSON endpoint). That is a backend, explicitly Bucket 3 / out of scope today, but **this is the structural reason the app cannot scale on the current model** - it is O(users x feeds) requests against a free third-party API instead of O(feeds).

**Impact 9 / Effort 8 / Risk 6** (this is the native/back-end track).

---

## 7.4 Static-asset / CDN cost

- 45 JSON tables + `team-halo-config.json` (~19k lines, one object per ~730 teams) + ~812 logo PNGs are all in the SW precache list (`sw.js:32-78`) **except** the 812 PNGs, which are populated on first view (`sw.js:106` comment) - good call, keeps install fast.
- **`team-halo-config.json` is precached in full on install** (`sw.js:78`) - a ~19k-line JSON downloaded by every install. At 1M installs that is meaningful first-load bandwidth, but it is one-time per device and CDN-served. Not the first ceiling, but the largest single precached asset; consider trimming unused fields (it carries `dominantColor`/`secondaryColor`/`needsContrastClamp` etc. that may be redundant with the tier attributes).
- The 45 JSON tables are also fully precached (`sw.js:33-77`); fine in size.

**Impact 4 / Effort 4 / Risk 2** (trim halo config payload).

---

## 7.5 Notification limits

**Current implementation:** alerts use page-context `new Notification` / SW `showNotification` (`3874-3891`); there is **no push subscription** (`SCOREFLY.md` confirms; no `pushManager` anywhere in the code).

**Scaling implication:** this is actually *cheap* to scale (no server push infra) but *weak* in capability - notifications only fire while the app is open/backgrounded and polling. So:
- It scales to 1M users for free (no push server), but
- It does not deliver the core promise (alert me when I'm *not* watching). The same iOS-suspension problem that blocks FlyTime detection (Phase 3.2) blocks reliable alerts.

**At scale, real push needs a push server** (VAPID + a subscription store + a sender). That is backend infra and out of scope today, but it is the second place a backend becomes necessary - for *capability*, not load.

**Impact 7 / Effort 8 / Risk 5** (native track).

---

## 7.6 Where the offline engine / backend becomes necessary

| Trigger | Becomes necessary around | Why |
|---------|--------------------------|-----|
| Self-hosted CORS proxy | ~1k-10k concurrent actives | free proxies throttle/ban |
| Fan-in feed cache (1 fetch -> N clients) | ~10k+ | O(users x feeds) hammers ESPN |
| Push server (VAPID) | any scale, for capability | closed-app alerts impossible client-side |
| FlyTime *learning* / retroactive stamping | product decision | needs play-by-play history + storage |

The parked `flytime-engine` (Python) and `oracle-cloud` are the seeds of this. The offline engine today is a *calibration* tool, not a serving backend; turning it into a fan-in/serving layer is the natural scale path.

---

## 7.7 First bottleneck to hit (answer)

**The free CORS proxies (7.2), reinforced by O(users x feeds) direct polling (7.3).** Both bite in the low thousands of concurrent actives, far before static hosting, CPU, or notification limits. Everything else (CDN bandwidth, halo config size, notification volume) is comfortably further out.

**Order the ceilings appear:** proxy throttling -> ESPN per-IP throttling -> (notifications never deliver closed-app, independent of scale) -> CDN bandwidth -> client CPU.

---

## Phase 7 summary

| # | Finding | Impact | Effort | Risk |
|---|---------|:--:|:--:|:--:|
| 7.2/7.3 | Free proxies + per-user direct polling = first ceiling (~low thousands) | 9 | 8 | 6 |
| 7.5 | No push -> closed-app alerts impossible (capability ceiling at any scale) | 7 | 8 | 5 |
| 7.4 | `team-halo-config.json` fully precached; trim unused fields | 4 | 4 | 2 |
| 5.8 (ref) | Longer poll tiers cut per-user request volume | 6 | 2 | 3 |
