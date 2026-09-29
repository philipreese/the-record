const CACHE = 'music-offline-v1';
const fallback = new URL('./offline.html', self.location.href).href;
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches
      .open(CACHE)
      .then((cache) => cache.add(fallback))
      .then(() => self.skipWaiting()),
  );
});
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter((key) => key.startsWith('music-offline-') && key !== CACHE)
            .map((key) => caches.delete(key)),
        ),
      )
      .then(() => self.clients.claim()),
  );
});
// Cache only the static unavailable screen. History and API responses stay live.
self.addEventListener('fetch', (event) => {
  if (
    event.request.mode === 'navigate' &&
    new URL(event.request.url).origin === self.location.origin
  ) {
    event.respondWith(
      fetch(event.request)
        .then((response) => (response.status >= 500 ? caches.match(fallback) : response))
        .catch(() => caches.match(fallback)),
    );
  }
});
