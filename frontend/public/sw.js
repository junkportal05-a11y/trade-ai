/**
 * ApexTrade Service Worker
 * ========================
 * Strategy:
 *   - Static assets (JS, CSS, HTML, icons, fonts) → Cache First
 *   - API calls to Hugging Face backend            → Network Only (never cache)
 *   - Google Fonts                                 → Cache First (once loaded)
 */

const CACHE_VERSION = 'apextrade-v7-theme-tokens';
const STATIC_CACHE  = `${CACHE_VERSION}-static`;
const FONT_CACHE    = `${CACHE_VERSION}-fonts`;

// Assets to pre-cache on install
const PRECACHE_ASSETS = [
  '/',
  '/index.html',
  '/manifest.json',
  '/favicon.svg',
  '/icon-192.png',
  '/icon-512.png',
];

// Never cache these — always go to network
const NETWORK_ONLY_PATTERNS = [
  /hf\.space/,              // Hugging Face Space backend
  /localhost:8000/,         // Local dev backend
  /api\//,                  // Any /api/ route
  /ws\//,                   // WebSocket
  /wss?:\/\//,              // WebSocket protocol
  /googleapis\.com/,        // Google APIs (not fonts)
];

// ── Install: pre-cache static assets ─────────────────────────────────────────
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then(cache => {
        console.log('[SW] Pre-caching static assets');
        // Use individual adds to avoid failing the entire install on one error
        return Promise.allSettled(
          PRECACHE_ASSETS.map(url =>
            cache.add(url).catch(err =>
              console.warn(`[SW] Failed to pre-cache ${url}:`, err)
            )
          )
        );
      })
      .then(() => self.skipWaiting())
  );
});

// ── Activate: clean up old caches ─────────────────────────────────────────────
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then(keys => {
        const valid = [STATIC_CACHE, FONT_CACHE];
        return Promise.all(
          keys
            .filter(key => !valid.includes(key))
            .map(key => {
              console.log('[SW] Deleting old cache:', key);
              return caches.delete(key);
            })
        );
      })
      .then(() => self.clients.claim())
  );
});

// ── Fetch: routing strategy ────────────────────────────────────────────────────
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests entirely
  if (request.method !== 'GET') return;

  // Network Only: API calls, WebSockets, auth flows
  if (NETWORK_ONLY_PATTERNS.some(pattern => pattern.test(request.url))) {
    return; // Let browser handle normally
  }

  // Cache First: Google Fonts
  if (url.hostname === 'fonts.googleapis.com' ||
      url.hostname === 'fonts.gstatic.com') {
    event.respondWith(cacheFirst(request, FONT_CACHE));
    return;
  }

  // Cache First: same-origin static assets (JS, CSS, images, icons)
  if (url.origin === self.location.origin) {
    event.respondWith(cacheFirst(request, STATIC_CACHE));
    return;
  }
});

// ── Strategies ────────────────────────────────────────────────────────────────

async function cacheFirst(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);

  if (cached) {
    // Serve from cache, refresh in background (stale-while-revalidate)
    refreshCache(request, cache);
    return cached;
  }

  // Not in cache — fetch from network and cache it
  try {
    const response = await fetch(request);
    if (response.ok) {
      cache.put(request, response.clone());
    }
    return response;
  } catch (err) {
    // Network failed and not in cache — return offline fallback
    return offlineFallback(request);
  }
}

function refreshCache(request, cache) {
  fetch(request)
    .then(response => {
      if (response.ok) cache.put(request, response.clone());
    })
    .catch(() => {}); // Silent fail — we already served from cache
}

function offlineFallback(request) {
  // For HTML navigation requests, return the cached index.html
  if (request.headers.get('accept')?.includes('text/html')) {
    return caches.match('/index.html');
  }
  // For everything else, return a minimal offline response
  return new Response(
    JSON.stringify({ error: 'offline', message: 'No network connection' }),
    {
      status: 503,
      headers: { 'Content-Type': 'application/json' }
    }
  );
}

// ── Push notifications (future: signal alerts) ────────────────────────────────
self.addEventListener('push', (event) => {
  if (!event.data) return;
  try {
    const data = event.data.json();
    event.waitUntil(
      self.registration.showNotification(data.title || 'ApexTrade Signal', {
        body:    data.body  || 'New signal detected',
        icon:    '/icon-192.png',
        badge:   '/icon-192.png',
        tag:     data.tag   || 'apextrade-signal',
        data:    { url: data.url || '/' },
        actions: [
          { action: 'view', title: 'View Signal' },
          { action: 'dismiss', title: 'Dismiss' },
        ],
        vibrate: [200, 100, 200],
      })
    );
  } catch (err) {
    console.warn('[SW] Push notification error:', err);
  }
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  if (event.action === 'dismiss') return;
  const url = event.notification.data?.url || '/';
  event.waitUntil(
    clients.matchAll({ type: 'window' }).then(windowClients => {
      for (const client of windowClients) {
        if (client.url === url && 'focus' in client) {
          return client.focus();
        }
      }
      return clients.openWindow(url);
    })
  );
});
