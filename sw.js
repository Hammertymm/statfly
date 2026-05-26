// StatFly Service Worker
// Caches the app shell so it loads instantly and works offline
//
// IMPORTANT: bump CACHE on every deploy to force existing users to refresh.

const CACHE = 'statfly-v25';
const SHELL = [
  '/',
  '/index.html',
  '/manifest.json',
  '/icon192.png',
  '/icon512.png'
];

// Install: cache the app shell
self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE).then(c => c.addAll(SHELL))
  );
  self.skipWaiting();
});

// Activate: clean up old caches
self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// Fetch: serve from cache, fall back to network
// ESPN API calls always go to network (never cache live scores)
self.addEventListener('fetch', e => {
  const url = e.request.url;

  // Never cache API/proxy calls - always fresh
  if (url.includes('espn.com') ||
      url.includes('corsproxy') ||
      url.includes('allorigins') ||
      url.includes('codetabs') ||
      url.includes('thingproxy')) {
    return; // let browser handle normally
  }

  e.respondWith(
    caches.match(e.request).then(cached => {
      if (cached) return cached;
      return fetch(e.request).then(res => {
        // Cache successful GET responses for app shell
        if (e.request.method === 'GET' && res.status === 200) {
          const clone = res.clone();
          caches.open(CACHE).then(c => c.put(e.request, clone));
        }
        return res;
      }).catch(() => caches.match('/index.html'));
    })
  );
});
