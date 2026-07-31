/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";

function parseActionId(actionRef) {
    if (!actionRef) {
        return false;
    }
    if (typeof actionRef === "number") {
        return actionRef;
    }
    // ir.ui.menu's "action" field reads as a reference string, e.g.
    // "ir.actions.act_window,85" - extract the numeric id.
    const id = parseInt(String(actionRef).split(",").pop(), 10);
    return Number.isNaN(id) ? false : id;
}

export class CliffsHomeScreen extends Component {
    static template = "cliffs_home_screen.HomeScreen";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.state = useState({ apps: [], loadingAppId: null });

        onWillStart(async () => {
            this.state.apps = await this.orm.searchRead(
                "ir.ui.menu",
                [["parent_id", "=", false]],
                ["name", "web_icon", "action", "child_id"],
                { order: "sequence asc" }
            );
        });
    }

    iconUrl(app) {
        return `/web/image/ir.ui.menu/${app.id}/web_icon_data`;
    }

    onIconError(ev) {
        ev.target.closest(".o_cliffs_app_tile").classList.add("o_cliffs_app_icon_fallback");
    }

    async onAppClick(app) {
        this.state.loadingAppId = app.id;
        try {
            const actionId = await this.resolveActionId(app);
            if (!actionId) {
                this.notification.add(`"${app.name}" has no menu items to open.`, {
                    type: "warning",
                });
                return;
            }
            await this.action.doAction(actionId, { clearBreadcrumbs: true });
        } finally {
            this.state.loadingAppId = null;
        }
    }

    // Mirrors Odoo's own app-switcher fallback: if the app's own menu record
    // has no action, walk down its menu tree for the first descendant that does.
    async resolveActionId(app) {
        const direct = parseActionId(app.action);
        if (direct) {
            return direct;
        }
        let frontier = app.child_id || [];
        while (frontier.length) {
            const children = await this.orm.searchRead(
                "ir.ui.menu",
                [["id", "in", frontier]],
                ["action", "child_id"],
                { order: "sequence asc" }
            );
            for (const child of children) {
                const actionId = parseActionId(child.action);
                if (actionId) {
                    return actionId;
                }
            }
            frontier = children.flatMap((child) => child.child_id || []);
        }
        return false;
    }
}

registry.category("actions").add("cliffs_home_screen.home_screen", CliffsHomeScreen);
