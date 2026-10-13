// ==============================================================================
// FlexyRide Corporate - Progressive Web App Service Worker
// Version: 1.0.0
// Features: Full Offline Fallback, Dynamic Asset Caching & Native Web Push
// ==============================================================================

const CACHE_VERSION = 'flexyride-corp-v1';
const STATIC_CACHE_NAME = `static-${CACHE_VERSION}`;
const DYNAMIC_CACHE_NAME = `dynamic-${CACHE_VERSION}`;

// Core assets to pre-cache immediately on install
const PRECACHE_ASSETS = [
    '/offline/',
    '/static/portal/manifest.json',
    '/static/portal/img/logo_icon.png',
    '/static/portal/img/logo.png',
    '/static/portal/img/icons/icon-192x192.png',
    '/static/portal/img/icons/icon-512x512.png',
    '/static/portal/js/broker_providers.js',
    '/static/portal/js/request_wizard.js',
    '/static/portal/js/passenger_tracking.js',
    'https://unpkg.com/lucide@latest',
    'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap'
];

// ------------------------------------------------------------------------------
// 1. Lifecycle: Install
// ------------------------------------------------------------------------------
self.addEventListener('install', function(event) {
    event.waitUntil(
        caches.open(STATIC_CACHE_NAME).then(function(cache) {
            // Attempt pre-caching each asset safely (continue even if external CDN fails offline)
            return Promise.allSettled(
                PRECACHE_ASSETS.map(function(url) {
                    return cache.add(url).catch(function(err) {
                        console.warn('[SW] Precache failed for:', url, err);
                    });
                })
            );
        }).then(function() {
            return self.skipWaiting();
        })
    );
});

// ------------------------------------------------------------------------------
// 2. Lifecycle: Activate & Cache Cleanup
// ------------------------------------------------------------------------------
self.addEventListener('activate', function(event) {
    event.waitUntil(
        caches.keys().then(function(cacheNames) {
            return Promise.all(
                cacheNames.map(function(cacheName) {
                    if (cacheName !== STATIC_CACHE_NAME && cacheName !== DYNAMIC_CACHE_NAME) {
                        console.log('[SW] Deleting stale cache:', cacheName);
                        return caches.delete(cacheName);
                    }
                })
            );
        }).then(function() {
            return self.clients.claim();
        })
    );
});

// ------------------------------------------------------------------------------
// 3. Network Fetch & Caching Strategies
// ------------------------------------------------------------------------------
self.addEventListener('fetch', function(event) {
    const request = event.request;
    const url = new URL(request.url);

    // Only handle GET requests
    if (request.method !== 'GET') {
        return;
    }

    // Do NOT cache Django Admin or sensitive auth/payment API write endpoints
    if (url.pathname.startsWith('/admin/') || 
        url.pathname.startsWith('/portal/api/webpush/') ||
        url.pathname.startsWith('/payments/webhook/')) {
        return;
    }

    // Strategy A: Navigation requests (HTML Pages) -> Network-First with Offline Page Fallback
    if (request.mode === 'navigate' || request.headers.get('accept')?.includes('text/html')) {
        event.respondWith(
            fetch(request)
                .then(function(networkResponse) {
                    if (networkResponse && networkResponse.status === 200) {
                        const responseToCache = networkResponse.clone();
                        caches.open(DYNAMIC_CACHE_NAME).then(function(cache) {
                            cache.put(request, responseToCache);
                        });
                    }
                    return networkResponse;
                })
                .catch(function() {
                    // Try to serve previously cached version of this page
                    return caches.match(request).then(function(cachedResponse) {
                        if (cachedResponse) {
                            return cachedResponse;
                        }
                        // Fall back to branded offline page
                        return caches.match('/offline/');
                    });
                })
        );
        return;
    }

    // Strategy B: Static Assets (Images, Scripts, Styles, Fonts) -> Stale-While-Revalidate
    if (url.pathname.startsWith('/static/') || 
        url.hostname.includes('fonts.googleapis.com') ||
        url.hostname.includes('fonts.gstatic.com') ||
        url.hostname.includes('cdn.tailwindcss.com') ||
        url.hostname.includes('unpkg.com')) {
        
        event.respondWith(
            caches.match(request).then(function(cachedResponse) {
                const fetchPromise = fetch(request).then(function(networkResponse) {
                    if (networkResponse && networkResponse.status === 200) {
                        const responseToCache = networkResponse.clone();
                        caches.open(STATIC_CACHE_NAME).then(function(cache) {
                            cache.put(request, responseToCache);
                        });
                    }
                    return networkResponse;
                }).catch(function() {
                    // Ignore background network failure for cached static assets
                });

                return cachedResponse || fetchPromise;
            })
        );
        return;
    }

    // Default: Normal Network Fetch with Dynamic Cache Fallback
    event.respondWith(
        fetch(request)
            .then(function(response) {
                if (response && response.status === 200) {
                    const responseClone = response.clone();
                    caches.open(DYNAMIC_CACHE_NAME).then(function(cache) {
                        cache.put(request, responseClone);
                    });
                }
                return response;
            })
            .catch(function() {
                return caches.match(request);
            })
    );
});

// ------------------------------------------------------------------------------
// 4. Native Browser Web Push (100% Free Standard Web Push)
// ------------------------------------------------------------------------------
self.addEventListener('push', function(event) {
    let data = {};
    if (event.data) {
        try {
            data = event.data.json();
        } catch (e) {
            data = { title: 'FlexyRide Alert', body: event.data.text() };
        }
    }

    const title = data.title || 'FlexyRide Corporate';
    const options = {
        body: data.body || 'You have an operational update regarding your booking.',
        icon: data.icon || '/static/portal/img/icons/icon-192x192.png',
        badge: data.badge || '/static/portal/img/logo_icon.png',
        vibrate: [100, 50, 100],
        data: {
            url: data.url || '/portal/',
            timestamp: Date.now()
        },
        actions: [
            { action: 'open', title: 'View Details' },
            { action: 'dismiss', title: 'Close' }
        ]
    };

    event.waitUntil(
        self.registration.showNotification(title, options)
    );
});

self.addEventListener('notificationclick', function(event) {
    event.notification.close();
    if (event.action === 'dismiss') {
        return;
    }

    const targetUrl = (event.notification.data && event.notification.data.url) ? event.notification.data.url : '/portal/';

    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true }).then(function(clientList) {
            for (let i = 0; i < clientList.length; i++) {
                const client = clientList[i];
                if (client.url.includes(targetUrl) && 'focus' in client) {
                    return client.focus();
                }
            }
            if (clients.openWindow) {
                return clients.openWindow(targetUrl);
            }
        })
    );
});
