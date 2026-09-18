// Cache-first app shell so the PWA still launches with no connectivity.
// Deliberately does NOT touch /web/dataset/* (Odoo's RPC endpoint): the app
// itself (sync_engine.js + offline_db.js) owns the online/offline/cache
// distinction for data, so this worker should never silently serve stale
// RPC responses as if they were live.
const CACHE_NAME = "cliffs-barcode-scanner-v1";
const APP_SHELL_URLS = [
    "/barcode_scanner",
    "/barcode_scanner/manifest.webmanifest",
    "/cliffs_barcode_scanner/static/src/pwa/app.js",
    "/cliffs_barcode_scanner/static/src/pwa/root_app.js",
    "/cliffs_barcode_scanner/static/src/pwa/pwa.css",
    "/cliffs_barcode_scanner/static/src/pwa/screens/operation_types_screen.js",
    "/cliffs_barcode_scanner/static/src/pwa/screens/picking_list_screen.js",
    "/cliffs_barcode_scanner/static/src/pwa/screens/picking_scan_screen.js",
    "/cliffs_barcode_scanner/static/src/pwa/components/scan_input.js",
    "/cliffs_barcode_scanner/static/src/pwa/components/camera_scanner_dialog.js",
    "/cliffs_barcode_scanner/static/src/pwa/components/sync_status_badge.js",
    "/cliffs_barcode_scanner/static/src/pwa/services/barcode_rpc.js",
    "/cliffs_barcode_scanner/static/src/pwa/services/offline_db.js",
    "/cliffs_barcode_scanner/static/src/pwa/services/sync_engine.js",
    "/cliffs_barcode_scanner/static/src/pwa/services/data_loader.js",
    "/cliffs_barcode_scanner/static/lib/owl/owl.js",
    "/cliffs_barcode_scanner/static/description/icon-192.png",
    "/cliffs_barcode_scanner/static/description/icon-512.png",
];

self.addEventListener("install", (event) => {
    event.waitUntil(
        caches
            .open(CACHE_NAME)
            .then((cache) => cache.addAll(APP_SHELL_URLS))
            .then(() => self.skipWaiting())
    );
});

self.addEventListener("activate", (event) => {
    event.waitUntil(
        caches
            .keys()
            .then((keys) => Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))))
            .then(() => self.clients.claim())
    );
});

self.addEventListener("fetch", (event) => {
    const url = new URL(event.request.url);

    if (event.request.method !== "GET" || url.pathname.startsWith("/web/dataset/")) {
        return;
    }

    event.respondWith(
        caches.match(event.request).then((cached) => {
            const networkFetch = fetch(event.request)
                .then((response) => {
                    if (response.ok) {
                        const clone = response.clone();
                        caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
                    }
                    return response;
                })
                .catch(() => cached);
            return cached || networkFetch;
        })
    );
});
