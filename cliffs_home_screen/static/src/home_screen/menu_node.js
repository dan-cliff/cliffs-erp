/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class MenuNode extends Component {
    static template = "cliffs_home_screen.MenuNode";
    static components = { MenuNode };
    static props = {
        menu: Object,
        level: { type: Number, optional: true },
    };
    static defaultProps = { level: 0 };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            open: false,
            children: null,
            loading: false,
            iconError: false,
        });
    }

    get hasChildren() {
        return this.props.menu.child_id && this.props.menu.child_id.length > 0;
    }

    get iconUrl() {
        return `/web/image/ir.ui.menu/${this.props.menu.id}/web_icon_data`;
    }

    onIconError() {
        this.state.iconError = true;
    }

    async onClick() {
        if (this.hasChildren) {
            await this.toggle();
        } else if (this.props.menu.action) {
            await this.action.doAction(this.props.menu.action, {
                clearBreadcrumbs: true,
            });
        }
    }

    async toggle() {
        this.state.open = !this.state.open;
        if (this.state.open && this.state.children === null) {
            this.state.loading = true;
            try {
                this.state.children = await this.orm.searchRead(
                    "ir.ui.menu",
                    [["parent_id", "=", this.props.menu.id]],
                    ["name", "web_icon", "child_id", "action"],
                    { order: "sequence asc" }
                );
            } finally {
                this.state.loading = false;
            }
        }
    }
}
