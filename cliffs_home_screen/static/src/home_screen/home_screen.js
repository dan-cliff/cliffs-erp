/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState } from "@odoo/owl";

export class CliffsHomeScreen extends Component {
    static template = "cliffs_home_screen.HomeScreen";
    static props = ["*"];

    setup() {
        this.menuService = useService("menu");
        this.state = useState({ loadingAppId: null });
    }

    // Apps are exactly the menu service's top-level (parent-less) menus,
    // i.e. non-archived ir.ui.menu records with no Parent Menu.
    get apps() {
        return this.menuService.getApps();
    }

    async onAppClick(app) {
        this.state.loadingAppId = app.id;
        try {
            // selectMenu (not actionService.doAction) so the navbar's
            // current-app state and menu sections update along with it.
            await this.menuService.selectMenu(app);
        } finally {
            this.state.loadingAppId = null;
        }
    }
}

registry.category("actions").add("cliffs_home_screen.home_screen", CliffsHomeScreen);
