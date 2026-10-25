// Service Worker oficial do Agillex Agenda
const CACHE_NAME = 'agillex-agenda-v1';
const STATIC_ASSETS = [
  '/',
  '/static/css/style.css',
  '/static/images/icon-192.png',
  '/static/images/icon-512.png',
  '/manifest.json'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS).catch((err) => {
        console.warn('Falha parcial ao pré-armazenar assets:', err);
      });
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            return caches.delete(key);
          }
        })
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  // Apenas métodos GET são cacheados; formulários e POST vão para a rede
  if (event.request.method !== 'GET') {
    return;
  }

  // Não cachear endpoints de API e admin autenticado para evitar stale state
  const url = new URL(event.request.url);
  if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/admin/') || url.pathname.startsWith('/pro/')) {
    event.respondWith(
      fetch(event.request).catch(() => {
        return caches.match(event.request);
      })
    );
    return;
  }

  // Network first com fallback para cache
  event.respondWith(
    fetch(event.request)
      .then((networkResponse) => {
        if (networkResponse && networkResponse.status === 200) {
          const responseToCache = networkResponse.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseToCache);
          });
        }
        return networkResponse;
      })
      .catch(() => caches.match(event.request))
  );
});
