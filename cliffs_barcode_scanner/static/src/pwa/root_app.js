import { Component, xml, useState } from "../../lib/owl/owl.js";
import { OperationTypesScreen } from "./screens/operation_types_screen.js";
import { PickingListScreen } from "./screens/picking_list_screen.js";
import { PickingScanScreen } from "./screens/picking_scan_screen.js";
import { SyncStatusBadge } from "./components/sync_status_badge.js";

export class RootApp extends Component {
    static template = xml`
        <div class="o_barcode_app">
            <header class="o_barcode_app_header">
                <button t-if="state.screen !== 'operationTypes'" class="o_back_button" t-on-click="() => this.goBack()">‹</button>
                <h1 class="o_barcode_app_title" t-esc="headerTitle"/>
                <SyncStatusBadge/>
            </header>
            <main class="o_barcode_app_main">
                <OperationTypesScreen t-if="state.screen === 'operationTypes'"
                                       onSelectType="(pt) => this.onSelectType(pt)"/>
                <PickingListScreen t-if="state.screen === 'pickingList'"
                                    pickingTypeId="state.pickingTypeId"
                                    pickingTypeName="state.pickingTypeName"
                                    onSelectPicking="(p) => this.onSelectPicking(p)"/>
                <PickingScanScreen t-if="state.screen === 'pickingScan'"
                                    pickingId="state.pickingId"
                                    onDone="() => this.onPickingDone()"/>
            </main>
        </div>
    `;
    static components = { OperationTypesScreen, PickingListScreen, PickingScanScreen, SyncStatusBadge };
    static props = {};

    setup() {
        this.state = useState({
            screen: "operationTypes",
            pickingTypeId: null,
            pickingTypeName: "",
            pickingId: null,
        });
    }

    get headerTitle() {
        if (this.state.screen === "pickingList") {
            return this.state.pickingTypeName;
        }
        if (this.state.screen === "pickingScan") {
            return "Scan";
        }
        return "Barcode Scanner";
    }

    onSelectType(pickingType) {
        this.state.pickingTypeId = pickingType.id;
        this.state.pickingTypeName = pickingType.name;
        this.state.screen = "pickingList";
    }

    onSelectPicking(picking) {
        this.state.pickingId = picking.id;
        this.state.screen = "pickingScan";
    }

    onPickingDone() {
        this.state.screen = "pickingList";
    }

    goBack() {
        if (this.state.screen === "pickingScan") {
            this.state.screen = "pickingList";
        } else if (this.state.screen === "pickingList") {
            this.state.screen = "operationTypes";
        }
    }
}
