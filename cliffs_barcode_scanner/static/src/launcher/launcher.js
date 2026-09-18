/** @odoo-module **/

import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";
import { Component, onWillStart } from "@odoo/owl";

// The real app lives at the standalone /barcode_scanner PWA route (its own
// asset bundle, manifest, and service worker scope) rather than as a client
// action in the backend SPA. This component is just the tile's landing spot
// in the menu/action system so it shows up in the home screen app grid.
export class BarcodeScannerLauncher extends Component {
    static template = "cliffs_barcode_scanner.Launcher";
    static props = ["*"];

    setup() {
        onWillStart(() => {
            browser.location.href = "/barcode_scanner";
        });
    }
}

registry.category("actions").add("cliffs_barcode_scanner.launcher", BarcodeScannerLauncher);
