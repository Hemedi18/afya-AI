self.addEventListener('install', function(event) {
  event.waitUntil(
    caches.open('aihealth-static-v1').then(function(cache) {
      return cache.addAll([
        '/',
        '/static/pharmacy/pharmacy.css',
        '/static/icons/icon-192x192.png',
        '/static/icons/icon-512x512.png',
      ]);
    })
  );
});

self.addEventListener('fetch', function(event) {
  event.respondWith(
    caches.match(event.request).then(function(response) {
      return response || fetch(event.request);
    })
  );
});
