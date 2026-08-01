import { mount, whenReady } from "../../lib/owl/owl.js";
import { RootApp } from "./root_app.js";

if ("serviceWorker" in navigator) {
    navigator.serviceWorker
        .register("/barcode_scanner/service_worker.js", { scope: "/barcode_scanner/" })
        .catch((err) => console.error("Barcode Scanner: service worker registration failed", err));
}

whenReady(() => {
    mount(RootApp, document.getElementById("barcode_scanner_root"), { dev: false });
});
