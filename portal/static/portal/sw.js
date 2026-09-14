// FlexyRide Corporate Web Push Service Worker (100% Free Standard Browser Push)

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
        icon: data.icon || '/static/portal/img/logo.png',
        badge: data.badge || '/static/portal/img/badge.png',
        vibrate: [100, 50, 100],
        data: {
            url: data.url || '/portal/dashboard/',
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

    const targetUrl = (event.notification.data && event.notification.data.url) ? event.notification.data.url : '/portal/dashboard/';

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
