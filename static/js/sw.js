/**
 * Harmoni ERP — Service Worker
 * Estrategia: Cache-First para estáticos, Network-First para vistas Django
 */

const CACHE_NAME = 'harmoni-v1';
const CACHE_VERSION = 1;

// Assets estáticos que se cachean inmediatamente
const PRECACHE_URLS = [
  '/',
  '/static/css/harmoni.css',
  '/static/css/harmoni-ai.css',
  '/static/js/harmoni-ai-chat.js',
];

// Patrones que NUNCA se cachean (siempre red)
const NEVER_CACHE = [
  '/ia/',
  '/api/',
  '/admin/',
  '/csrf/',
  '/login/',
  '/logout/',
];

// ── Install ─────────────────────────────────────────────────────────────
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      // Pre-cachear sin fallar si algún recurso no existe
      return Promise.allSettled(
        PRECACHE_URLS.map(url => cache.add(url).catch(() => null))
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
          .filter(key => key !== CACHE_NAME)
          .map(key => caches.delete(key))
      )
    ).then(() => self.clients.claim())
  );
});

// ── Fetch ─────────────────────────────────────────────────────────────────
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // Solo interceptar same-origin GET requests
  if (event.request.method !== 'GET' || url.origin !== location.origin) {
    return;
  }

  // Nunca cachear rutas dinámicas
  const neverCache = NEVER_CACHE.some(p => url.pathname.startsWith(p));
  if (neverCache) {
    return; // Usar red directamente
  }

  // Archivos estáticos: Cache-First
  if (url.pathname.startsWith('/static/')) {
    event.respondWith(
      caches.match(event.request).then((cached) => {
        if (cached) return cached;
        return fetch(event.request).then((response) => {
          if (response.ok) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then(c => c.put(event.request, clone));
          }
          return response;
        }).catch(() => cached || new Response('', { status: 503 }));
      })
    );
    return;
  }

  // Páginas Django: Network-First con fallback a caché
  event.respondWith(
    fetch(event.request)
      .then((response) => {
        if (response.ok) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then(c => c.put(event.request, clone));
        }
        return response;
      })
      .catch(() => caches.match(event.request))
  );
});
