/**
 * Harmoni ERP — Service Worker v2
 * Cache-First para estáticos, Network-First para vistas Django
 * Offline fallback, cache versioning, push notifications
 */

const CACHE_VERSION = 2;
const CACHE_NAME = `harmoni-v${CACHE_VERSION}`;
const OFFLINE_URL = '/offline/';

// Assets estáticos que se cachean inmediatamente al instalar
const PRECACHE_URLS = [
  '/',
  OFFLINE_URL,
  '/static/css/harmoni.css',
  '/static/css/harmoni-ai.css',
  '/static/css/responsive-mobile.css',
  '/static/js/harmoni-ai-chat.js',
  '/static/images/favicon.svg',
];

// CDN assets to precache
const CDN_ASSETS = [
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css',
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js',
  'https://code.jquery.com/jquery-3.7.1.min.js',
];

// Patrones que NUNCA se cachean (siempre red)
const NEVER_CACHE = [
  '/ia/',
  '/api/',
  '/admin/',
  '/csrf/',
  '/login/',
  '/logout/',
  '/asistencia/ia/',
];

// ── Install ─────────────────────────────────────────────────────────────
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      // Pre-cachear sin fallar si algún recurso no existe
      const allUrls = [...PRECACHE_URLS, ...CDN_ASSETS];
      return Promise.allSettled(
        allUrls.map(url => cache.add(url).catch(() => {
          console.warn('[SW] Failed to precache:', url);
        }))
      );
    }).then(() => self.skipWaiting())
  );
});

// ── Activate ─────────────────────────────────────────────────────────────
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter(key => key.startsWith('harmoni-') && key !== CACHE_NAME)
          .map(key => {
            console.log('[SW] Deleting old cache:', key);
            return caches.delete(key);
          })
      )
    ).then(() => self.clients.claim())
  );
});

// ── Fetch ─────────────────────────────────────────────────────────────────
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // Solo interceptar GET requests
  if (event.request.method !== 'GET') return;

  // Nunca cachear rutas dinámicas sensibles
  if (url.origin === location.origin) {
    const neverCache = NEVER_CACHE.some(p => url.pathname.startsWith(p));
    if (neverCache) return;
  }

  // ── Static assets: Cache-First ──
  const isStatic = url.pathname.startsWith('/static/') ||
                   url.hostname.includes('cdn.jsdelivr.net') ||
                   url.hostname.includes('cdnjs.cloudflare.com') ||
                   url.hostname.includes('code.jquery.com') ||
                   url.hostname.includes('fonts.googleapis.com') ||
                   url.hostname.includes('fonts.gstatic.com');

  if (isStatic) {
    event.respondWith(
      caches.match(event.request).then((cached) => {
        if (cached) return cached;
        return fetch(event.request).then((response) => {
          if (response.ok) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then(c => c.put(event.request, clone));
          }
          return response;
        }).catch(() => {
          // Return cached version if available, else empty response
          return cached || new Response('', { status: 503, statusText: 'Offline' });
        });
      })
    );
    return;
  }

  // ── HTML pages (same-origin): Network-First with offline fallback ──
  if (url.origin === location.origin) {
    const isNavigate = event.request.mode === 'navigate' ||
                       event.request.headers.get('accept')?.includes('text/html');

    if (isNavigate) {
      event.respondWith(
        fetch(event.request)
          .then((response) => {
            if (response.ok) {
              const clone = response.clone();
              caches.open(CACHE_NAME).then(c => c.put(event.request, clone));
            }
            return response;
          })
          .catch(() => {
            return caches.match(event.request).then(cached => {
              return cached || caches.match(OFFLINE_URL);
            });
          })
      );
      return;
    }

    // ── API/JSON requests: Network-only with graceful fail ──
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          if (response.ok) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then(c => c.put(event.request, clone));
          }
          return response;
        })
        .catch(() => {
          return caches.match(event.request).then(cached => {
            return cached || new Response(
              JSON.stringify({ error: 'offline', message: 'Sin conexión a Internet' }),
              { status: 503, headers: { 'Content-Type': 'application/json' } }
            );
          });
        })
    );
  }
});

// ── Push Notifications ──────────────────────────────────────────────────
self.addEventListener('push', (event) => {
  let data = { title: 'Harmoni ERP', body: 'Tienes una nueva notificación' };

  if (event.data) {
    try {
      data = event.data.json();
    } catch (e) {
      data.body = event.data.text();
    }
  }

  const options = {
    body: data.body || data.message || '',
    icon: '/static/images/icon-192.png',
    badge: '/static/images/favicon.svg',
    tag: data.tag || 'harmoni-notification',
    data: {
      url: data.url || '/',
    },
    actions: data.actions || [],
    vibrate: [200, 100, 200],
    requireInteraction: data.requireInteraction || false,
  };

  event.waitUntil(
    self.registration.showNotification(data.title || 'Harmoni ERP', options)
  );
});

// ── Notification click ──────────────────────────────────────────────────
self.addEventListener('notificationclick', (event) => {
  event.notification.close();

  const url = event.notification.data?.url || '/';

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((windowClients) => {
      // Focus existing tab if open
      for (const client of windowClients) {
        if (client.url.includes(self.location.origin) && 'focus' in client) {
          client.navigate(url);
          return client.focus();
        }
      }
      // Open new tab
      return clients.openWindow(url);
    })
  );
});

// ── Background sync (future use) ────────────────────────────────────────
self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-attendance') {
    event.waitUntil(syncAttendance());
  }
});

async function syncAttendance() {
  // Placeholder for offline attendance sync
  console.log('[SW] Background sync: attendance');
}

// ── Message handler for cache management ────────────────────────────────
self.addEventListener('message', (event) => {
  if (event.data === 'skipWaiting') {
    self.skipWaiting();
  }
  if (event.data === 'clearCache') {
    caches.keys().then(keys => {
      keys.forEach(key => caches.delete(key));
    });
  }
});
