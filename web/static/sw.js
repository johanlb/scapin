// Scapin Service Worker
// Version: 0.9.0

const VERSION = '0.9.0';
const CACHE_NAME = `scapin-v${VERSION}`;
const STATIC_CACHE = `scapin-static-v${VERSION}`;
const API_CACHE = `scapin-api-v${VERSION}`;

// Static assets to cache immediately on install
const PRECACHE_ASSETS = [
  '/',
  '/manifest.json',
  '/icons/icon.svg',
  '/icons/icon-192.png',
  '/icons/icon-512.png',
  '/icons/apple-touch-icon.png',
  '/icons/favicon-32.png',
  '/icons/favicon-16.png',
  '/icons/favicon.ico'
];

// API routes to cache with network-first strategy
const CACHEABLE_API_ROUTES = [
  '/api/briefing/morning',
  '/api/stats'
];

// Install event - cache static assets
self.addEventListener('install', (event) => {
  console.log('[SW] Installing service worker v' + VERSION);
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then((cache) => {
        console.log('[SW] Precaching static assets');
        return cache.addAll(PRECACHE_ASSETS);
      })
      .then(() => self.skipWaiting())
      .catch((err) => {
        console.error('[SW] Precache failed:', err);
      })
  );
});

// Activate event - clean old caches
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating service worker v' + VERSION);
  event.waitUntil(
    caches.keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames
            .filter((name) => {
              // Delete old version caches
              return name.startsWith('scapin-') &&
                     !name.includes(VERSION);
            })
            .map((name) => {
              console.log('[SW] Deleting old cache:', name);
              return caches.delete(name);
            })
        );
      })
      .then(() => self.clients.claim())
  );
});

// Fetch event - smart caching strategy
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests
  if (request.method !== 'GET') return;

  // Skip WebSocket upgrades
  if (request.headers.get('upgrade') === 'websocket') return;

  // Skip cross-origin requests
  if (url.origin !== self.location.origin) return;

  // API requests - network first, cache fallback
  if (url.pathname.startsWith('/api')) {
    event.respondWith(networkFirstStrategy(request, API_CACHE));
    return;
  }

  // Static assets and pages - cache first, network fallback
  event.respondWith(cacheFirstStrategy(request, CACHE_NAME));
});

// Network first strategy (for API calls)
async function networkFirstStrategy(request, cacheName) {
  const url = new URL(request.url);

  // Check if this API route should be cached
  const shouldCache = CACHEABLE_API_ROUTES.some(route =>
    url.pathname.startsWith(route)
  );

  try {
    const response = await fetch(request);

    // Cache successful responses for cacheable routes
    if (response.ok && shouldCache) {
      const cache = await caches.open(cacheName);
      cache.put(request, response.clone());
    }

    return response;
  } catch (error) {
    // Network failed, try cache
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      console.log('[SW] Serving from cache (offline):', request.url);
      return cachedResponse;
    }

    // Return error response for API
    return new Response(
      JSON.stringify({
        error: 'offline',
        message: 'Vous semblez hors ligne'
      }),
      {
        status: 503,
        headers: { 'Content-Type': 'application/json' }
      }
    );
  }
}

// Cache first strategy (for static assets)
async function cacheFirstStrategy(request, cacheName) {
  const cachedResponse = await caches.match(request);

  if (cachedResponse) {
    // Return cache immediately, but update in background
    updateCache(request, cacheName);
    return cachedResponse;
  }

  try {
    const response = await fetch(request);

    // Cache successful responses
    if (response.ok) {
      const cache = await caches.open(cacheName);
      cache.put(request, response.clone());
    }

    return response;
  } catch (error) {
    // Offline and no cache - return offline page for navigation
    if (request.mode === 'navigate') {
      const offlineResponse = await caches.match('/');
      if (offlineResponse) return offlineResponse;
    }

    return new Response('Hors ligne', {
      status: 503,
      statusText: 'Service Unavailable'
    });
  }
}

// Background cache update (stale-while-revalidate)
async function updateCache(request, cacheName) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(cacheName);
      cache.put(request, response);
    }
  } catch (error) {
    // Silently fail - we're just updating cache
  }
}

// Background Sync - queue failed actions for retry
self.addEventListener('sync', (event) => {
  console.log('[SW] Background sync:', event.tag);

  if (event.tag === 'sync-actions') {
    event.waitUntil(syncPendingActions());
  }
});

async function syncPendingActions() {
  // Get pending actions from IndexedDB (to be implemented)
  console.log('[SW] Syncing pending actions...');
  // TODO: Implement IndexedDB queue for offline actions
}

// Push notifications
self.addEventListener('push', (event) => {
  if (!event.data) return;

  let data;
  try {
    data = event.data.json();
  } catch {
    data = { title: 'Scapin', body: event.data.text() };
  }

  const options = {
    body: data.body || 'Nouvelle notification',
    icon: '/icons/icon-192.png',
    badge: '/icons/favicon-32.png',
    tag: data.tag || 'scapin-notification',
    data: {
      url: data.url || '/',
      ...data
    },
    vibrate: [100, 50, 100],
    actions: data.actions || []
  };

  // Add urgency-based styling
  if (data.urgency === 'high') {
    options.requireInteraction = true;
  }

  event.waitUntil(
    self.registration.showNotification(data.title || 'Scapin', options)
  );
});

// Notification click handler
self.addEventListener('notificationclick', (event) => {
  event.notification.close();

  const urlToOpen = event.notification.data?.url || '/';

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true })
      .then((windowClients) => {
        // Check if app is already open
        for (const client of windowClients) {
          if (client.url.includes(self.location.origin) && 'focus' in client) {
            client.navigate(urlToOpen);
            return client.focus();
          }
        }
        // Open new window
        if (clients.openWindow) {
          return clients.openWindow(urlToOpen);
        }
      })
  );
});

// Handle notification actions
self.addEventListener('notificationclick', (event) => {
  if (event.action) {
    console.log('[SW] Notification action clicked:', event.action);
    // Handle specific actions (e.g., 'snooze', 'dismiss', 'view')
    // TODO: Implement action handlers
  }
});

// Message handler for client communication
self.addEventListener('message', (event) => {
  if (event.data?.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }

  if (event.data?.type === 'CACHE_URLS') {
    event.waitUntil(
      caches.open(CACHE_NAME).then((cache) => {
        return cache.addAll(event.data.urls);
      })
    );
  }
});

console.log('[SW] Service Worker loaded v' + VERSION);
