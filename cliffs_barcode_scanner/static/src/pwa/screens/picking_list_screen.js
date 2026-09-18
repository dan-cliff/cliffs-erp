import { Component, xml, useState, onWillStart } from "../../../lib/owl/owl.js";
import { loadPickingList } from "../services/data_loader.js";

export class PickingListScreen extends Component {
    static template = xml`
        <div class="o_screen o_picking_list_screen">
            <p t-if="state.loading" class="o_loading">Loading…</p>
            <p t-if="state.error" class="o_error" t-esc="state.error"/>
            <p t-if="state.fromCache" class="o_cache_notice">Showing cached data (offline)</p>
            <div class="o_picking_list">
                <div t-foreach="state.pickings" t-as="picking" t-key="picking.id"
                     class="o_picking_row"
                     t-on-click="() => this.props.onSelectPicking(picking)">
                    <div class="o_picking_row_main">
                        <span class="o_picking_name" t-esc="picking.name"/>
                        <span class="o_picking_partner" t-esc="picking.partnerName"/>
                    </div>
                    <span class="o_picking_state" t-esc="picking.state"/>
                </div>
            </div>
            <p t-if="isEmpty" class="o_empty">Nothing ready to process for this operation type.</p>
        </div>
    `;
    static props = {
        pickingTypeId: Number,
        pickingTypeName: { type: String, optional: true },
        onSelectPicking: Function,
    };

    setup() {
        this.state = useState({ loading: true, error: "", fromCache: false, pickings: [] });
        onWillStart(() => this.load());
    }

    get isEmpty() {
        return !this.state.loading && !this.state.pickings.length;
    }

    async load() {
        this.state.loading = true;
        this.state.error = "";
        try {
            const { pickings, fromCache } = await loadPickingList(this.props.pickingTypeId);
            this.state.pickings = pickings;
            this.state.fromCache = fromCache;
        } catch (err) {
            this.state.error = err.message;
        } finally {
            this.state.loading = false;
        }
    }
}
