/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";
import { MenuNode } from "./menu_node";

export class CliffsHomeScreen extends Component {
    static template = "cliffs_home_screen.HomeScreen";
    static components = { MenuNode };
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.state = useState({ apps: [] });

        onWillStart(async () => {
            this.state.apps = await this.orm.searchRead(
                "ir.ui.menu",
                [["parent_id", "=", false]],
                ["name", "web_icon", "child_id", "action"],
                { order: "sequence asc" }
            );
        });
    }
}

registry.category("actions").add("cliffs_home_screen.home_screen", CliffsHomeScreen);
