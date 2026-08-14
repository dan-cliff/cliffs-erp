/* Service worker for the Seeance kiosk PWA.
 * Caches the app shell (HTML/JS/CSS/icons) so the kiosk can still launch
 * and operate while offline. All data (reference data + the outbox of
 * queued sign in/out submissions) lives in IndexedDB, managed by app.js -
 * this worker only deals with static asset caching and shell availability. */

const CACHE_NAME = 'seeance-kiosk-v1';
const STATIC_ASSETS = [
  '/seeance/static/src/pwa/app.js',
  '/seeance/static/src/pwa/app.css',
  '/seeance/static/src/pwa/idb.js',
  '/seeance/static/src/pwa/icons/icon-192.png',
  '/seeance/static/src/pwa/icons/icon-512.png',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => cache.addAll(STATIC_ASSETS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(
        keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
      ))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Never intercept the JSON API: let app.js's own online/offline handling
  // and outbox queueing deal with failures there.
  if (url.pathname.startsWith('/seeance/kiosk/api/')) {
    return;
  }

  // Kiosk shell navigations and the per-Check Point manifest: try the
  // network first (so an online kiosk always sees live content), fall back
  // to the last cached copy when offline.
  if (request.mode === 'navigate' || url.pathname.endsWith('manifest.webmanifest')) {
    event.respondWith(
      fetch(request)
        .then((response) => {
          const copy = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
          return response;
        })
        .catch(() => caches.match(request))
    );
    return;
  }

  // Static assets: cache-first, refresh in the background when possible.
  if (url.pathname.startsWith('/seeance/static/src/pwa/')) {
    event.respondWith(
      caches.match(request).then((cached) => {
        const fetchPromise = fetch(request).then((response) => {
          const copy = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
          return response;
        }).catch(() => cached);
        return cached || fetchPromise;
      })
    );
  }
});
