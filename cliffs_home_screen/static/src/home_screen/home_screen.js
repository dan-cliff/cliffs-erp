/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";
import { Component, onWillStart, useState } from "@odoo/owl";

export class CliffsHomeScreen extends Component {
    static template = "cliffs_home_screen.HomeScreen";
    static props = ["*"];
    // Odoo's own action manager hides the top navbar for fullscreen client
    // actions (see WebClient's `state.fullscreen`), so it's only shown once
    // an app is opened from here.
    static target = "fullscreen";

    setup() {
        this.menuService = useService("menu");
        this.orm = useService("orm");
        this.state = useState({ loadingAppId: null });
        this.branding = useState({ color: "", opacity: 100, hasImage: false });

        const companyId = user.activeCompany?.id;
        this.backgroundImageUrl = companyId
            ? `/web/image/res.company/${companyId}/cliffs_home_background_image`
            : "";

        onWillStart(async () => {
            if (!companyId) {
                return;
            }
            // bin_size avoids downloading the image just to check it's set.
            const [company] = await this.orm.read(
                "res.company",
                [companyId],
                [
                    "cliffs_home_background_color",
                    "cliffs_home_background_opacity",
                    "cliffs_home_background_image",
                ],
                { context: { bin_size: true } }
            );
            this.branding.color = company.cliffs_home_background_color || "";
            this.branding.opacity = company.cliffs_home_background_opacity;
            this.branding.hasImage = Boolean(company.cliffs_home_background_image);
        });
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
