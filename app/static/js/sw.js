/* sw.js — Service Worker mínimo para PWA
   Permite que la app sea instalable y muestre /offline cuando no hay red. */

const CACHE_NAME = 'prode-v1';
const OFFLINE_URL = '/offline';

self.addEventListener('install', function (event) {
  event.waitUntil(
    caches.open(CACHE_NAME).then(function (cache) {
      return cache.add(OFFLINE_URL);
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', function (event) {
  event.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(
        keys.filter(function (k) { return k !== CACHE_NAME; })
            .map(function (k)   { return caches.delete(k); })
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', function (event) {
  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request).catch(function () {
        return caches.match(OFFLINE_URL);
      })
    );
  }
});
