import { Component, xml, useState } from "../../../lib/owl/owl.js";
import { syncState } from "../services/sync_engine.js";

export class SyncStatusBadge extends Component {
    static template = xml`
        <div class="o_sync_status_badge" t-att-class="statusClass">
            <span class="o_sync_dot"/>
            <span t-esc="statusLabel"/>
        </div>
    `;
    static props = {};

    setup() {
        // syncState is a shared owl reactive() from sync_engine.js; wrapping
        // it again with useState ties re-renders of this component to it.
        this.state = useState(syncState);
    }

    get statusClass() {
        return this.state.online ? "o_sync_online" : "o_sync_offline";
    }

    get statusLabel() {
        if (!this.state.online) {
            return this.state.pendingCount
                ? `Offline · ${this.state.pendingCount} queued`
                : "Offline";
        }
        return this.state.pendingCount ? `Syncing ${this.state.pendingCount}…` : "Online";
    }
}
