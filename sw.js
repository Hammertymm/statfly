// StatFly Service Worker
// Caches static assets (icons, manifest) for offline shell.
// index.html is NOT cached - always fetched fresh so UI updates
// are instant without needing a cache version bump.

const CACHE = 'statfly-v36';
const SHELL = [
  '/manifest.json',
  '/icon192.png',
  '/icon512.png'
];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE).then(c => c.addAll(SHELL))
  );
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', e => {
  const url = e.request.url;

  // Never cache API/proxy calls - always fresh
  if (url.includes('espn.com') ||
      url.includes('corsproxy') ||
      url.includes('allorigins') ||
      url.includes('codetabs') ||
      url.includes('thingproxy')) {
    return;
  }

  // Never cache index.html - always fetch fresh from network
  if (url.endsWith('/') || url.includes('index.html')) {
    e.respondWith(fetch(e.request).catch(() => caches.match('/index.html')));
    return;
  }

  // Static assets: cache first
  e.respondWith(
    caches.match(e.request).then(cached => {
      if (cached) return cached;
      return fetch(e.request).then(res => {
        if (e.request.method === 'GET' && res.status === 200) {
          const clone = res.clone();
          caches.open(CACHE).then(c => c.put(e.request, clone));
        }
        return res;
      });
    })
  );
});
