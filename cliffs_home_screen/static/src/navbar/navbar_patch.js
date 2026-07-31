/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { NavBar } from "@web/webclient/navbar/navbar";

patch(NavBar.prototype, {
    onCliffsHomeClick() {
        this.actionService.doAction("cliffs_home_screen.action_home_screen", {
            clearBreadcrumbs: true,
        });
    },
});
