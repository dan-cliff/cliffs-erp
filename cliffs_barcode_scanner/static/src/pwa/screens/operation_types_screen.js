import { Component, xml, useState, onWillStart } from "../../../lib/owl/owl.js";
import { loadOperationTypes } from "../services/data_loader.js";

export class OperationTypesScreen extends Component {
    static template = xml`
        <div class="o_screen o_operation_types_screen">
            <p t-if="state.loading" class="o_loading">Loading…</p>
            <p t-if="state.error" class="o_error" t-esc="state.error"/>
            <p t-if="state.fromCache" class="o_cache_notice">Showing cached data (offline)</p>
            <div class="o_operation_types_grid">
                <div t-foreach="state.types" t-as="opType" t-key="opType.id"
                     class="o_operation_type_tile"
                     t-on-click="() => this.props.onSelectType(opType)">
                    <span class="o_operation_type_name" t-esc="opType.name"/>
                    <span class="o_operation_type_count" t-esc="opType.readyCount"/>
                </div>
            </div>
            <p t-if="isEmpty" class="o_empty">No operation types available.</p>
        </div>
    `;
    static props = { onSelectType: Function };

    setup() {
        this.state = useState({ loading: true, error: "", fromCache: false, types: [] });
        onWillStart(() => this.load());
    }

    get isEmpty() {
        return !this.state.loading && !this.state.types.length;
    }

    async load() {
        this.state.loading = true;
        this.state.error = "";
        try {
            const { types, fromCache } = await loadOperationTypes();
            this.state.types = types;
            this.state.fromCache = fromCache;
        } catch (err) {
            this.state.error = err.message;
        } finally {
            this.state.loading = false;
        }
    }
}
