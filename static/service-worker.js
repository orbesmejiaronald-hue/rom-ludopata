const CACHE_NAME = 'rom-ludopata-v1.2';
const ASSETS = [
  '/',
  '/static/manifest.json',
  '/static/icon-192.png',
  '/static/icon-512.png'
];

self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(ASSETS);
    })
  );
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
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
});

self.addEventListener('fetch', (e) => {
  // Only intercept GET requests
  if (e.request.method !== 'GET') {
    return;
  }

  const url = new URL(e.request.url);

  // Skip API routes completely (no caching for dynamic predictions or chat streams)
  if (url.pathname.startsWith('/api/')) {
    return;
  }

  // Network First strategy for HTML root '/' to ensure updates show up instantly
  if (url.pathname === '/' || (e.request.headers.get('accept') && e.request.headers.get('accept').includes('text/html'))) {
    e.respondWith(
      fetch(e.request)
        .then((response) => {
          // Cache the fresh version of the page
          const responseClone = response.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(e.request, responseClone);
          });
          return response;
        })
        .catch(() => {
          // If network is offline, fallback to cache
          return caches.match(e.request);
        })
    );
  } else {
    // Cache First strategy for static assets (images, manifest, fonts)
    e.respondWith(
      caches.match(e.request).then((cachedResponse) => {
        return cachedResponse || fetch(e.request).then((response) => {
          const responseClone = response.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(e.request, responseClone);
          });
          return response;
        });
      })
    );
  }
});
