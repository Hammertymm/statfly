// ScoreFly service worker
// Bump CACHE on every deploy so devices pick up the new files.
const CACHE = 'scorefly-v121';

// App shell + icons. Relative paths so it works under the /scorefly/ GitHub Pages path.
const SHELL = [
  './',
  './index.html',
  './manifest.json',
  './icon192.png',
  './icon512.png',
  './icon-soccer.png',
  './icon-basketball.png',
  './icon-football.png',
  './icon-afl.png',
  './icon-baseball.png',
  './icon-hockey.png',
  './icon-cricket.png',
  './icon-tennis.png',
  './icon-rugby.png',
  './icon-cup.png',
  './knob.png',
  './supafly-welcome.png',
  './supafly-pointing.png',
  './supafly-score.png',
  './supafly-thumbsup.png',
  './fly-green.png',
  './fly-yellow.png',
  './fly-red.png',
  './onboard-hero.png',
  './onboard-notif.png',
  './afl-flytime-v1.json',
  './nfl-flytime-v1.json',
  './nba-flytime-v1.json',
  './wnba-flytime-v1.json',
  './nbl-flytime-v1.json',
  './ncaam-flytime-v1.json',
  './mlb-flytime-v1.json',
  './nhl-flytime-v1.json',
  './ncaaf-flytime-v1.json',
  './cfl-flytime-v1.json',
  './nrl-flytime-v1.json',
  './soccer-usa-1-flytime-v1.json',
  './soccer-eng-1-flytime-v1.json',
  './soccer-esp-1-flytime-v1.json',
  './soccer-ger-1-flytime-v1.json',
  './soccer-ita-1-flytime-v1.json',
  './soccer-fra-1-flytime-v1.json',
  './soccer-eng-2-flytime-v1.json',
  './soccer-ned-1-flytime-v1.json',
  './soccer-por-1-flytime-v1.json',
  './soccer-sco-1-flytime-v1.json',
  './soccer-tur-1-flytime-v1.json',
  './soccer-bra-1-flytime-v1.json',
  './soccer-arg-1-flytime-v1.json',
  './soccer-mex-1-flytime-v1.json',
  './soccer-aus-1-flytime-v1.json',
  './soccer-irl-1-flytime-v1.json',
  './soccer-ind-1-flytime-v1.json',
  './soccer-rsa-1-flytime-v1.json',
  './soccer-eng-w-1-flytime-v1.json',
  './soccer-uefa-champions-flytime-v1.json',
  './soccer-uefa-europa-flytime-v1.json',
  './soccer-conmebol-libertadores-flytime-v1.json',
  './soccer-jpn-1-flytime-v1.json',
  './soccer-eng-3-flytime-v1.json',
  './soccer-eng-4-flytime-v1.json',
  './soccer-chn-1-flytime-v1.json',
  './soccer-bel-1-flytime-v1.json',
  './soccer-sui-1-flytime-v1.json',
  './soccer-gre-1-flytime-v1.json',
  './soccer-ita-2-flytime-v1.json',
  './soccer-ksa-1-flytime-v1.json',
  './soccer-rus-1-flytime-v1.json',
  './rugby-urc-flytime-v1.json',
  './rugby-top14-flytime-v1.json',
  './team-halo-config.json'
];

// Install: pre-cache the shell, then activate immediately.
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE)
      .then(c => c.addAll(SHELL))
      .catch(() => {})            // a missing optional file must not block install
      .then(() => self.skipWaiting())
  );
});

// Activate: delete any old caches that are not the current version.
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(
        keys.filter(k => k !== CACHE).map(k => caches.delete(k))
      ))
      .then(() => self.clients.claim())
  );
});

// Fetch strategy:
//   - ESPN / proxy / font requests: always go to the network (live data, never cache).
//   - app shell + same-origin GETs: cache-first, fall back to network, then cache the result.
self.addEventListener('fetch', event => {
  const req = event.request;
  if (req.method !== 'GET') return;

  const url = new URL(req.url);
  const isData =
    url.hostname.includes('espn.com') ||
    url.hostname.includes('corsproxy') ||
    url.hostname.includes('allorigins') ||
    url.hostname.includes('codetabs') ||
    url.hostname.includes('thingproxy') ||
    url.hostname.includes('fonts.googleapis') ||
    url.hostname.includes('fonts.gstatic');

  if (isData) {
    // Network-only for live data and fonts; never serve a stale score.
    event.respondWith(fetch(req).catch(() => new Response('', { status: 504 })));
    return;
  }

  // Cache-first for the app shell and other same-origin assets.
  event.respondWith(
    caches.match(req).then(cached => {
      if (cached) return cached;
      return fetch(req).then(res => {
        // Only cache valid, same-origin, basic responses.
        if (res && res.status === 200 && res.type === 'basic') {
          const copy = res.clone();
          caches.open(CACHE).then(c => c.put(req, copy)).catch(() => {});
        }
        return res;
      }).catch(() => caches.match('./index.html'));
    })
  );
});

// FlyTime notification tap: focus an open ScoreFly window on the Feed tab, or launch one.
self.addEventListener('notificationclick', event => {
  const nav = event.notification.data && event.notification.data.nav;
  event.notification.close();
  if (nav !== 'feed') return;

  const feedUrl = new URL('./index.html#feed', self.location.href).href;

  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then(clients => {
      for (const client of clients) {
        if ('focus' in client) {
          client.postMessage({ type: 'scorefly-nav-feed' });
          return client.focus();
        }
      }
      if (self.clients.openWindow) return self.clients.openWindow(feedUrl);
    })
  );
});
