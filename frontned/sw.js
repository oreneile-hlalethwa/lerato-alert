// Minimal service worker so the app installs as an Android app.
// It always goes to the network: alerts and evidence must never come from a stale cache.
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (e) => e.waitUntil(self.clients.claim()));
self.addEventListener('fetch', () => {});