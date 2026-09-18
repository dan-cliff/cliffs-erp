import { Component, xml, useState, onWillStart, onWillUnmount } from "../../../lib/owl/owl.js";
import { loadPickingDetail } from "../services/data_loader.js";
import { setScannedQty, queueValidate } from "../services/sync_engine.js";
import { ScanInput } from "../components/scan_input.js";
import { CameraScannerDialog, isCameraScanningSupported } from "../components/camera_scanner_dialog.js";

export class PickingScanScreen extends Component {
    static template = xml`
        <div class="o_screen o_picking_scan_screen">
            <p t-if="state.loading" class="o_loading">Loading…</p>
            <p t-if="state.error" class="o_error" t-esc="state.error"/>
            <p t-if="state.fromCache" class="o_cache_notice">Showing cached data (offline)</p>
            <p t-if="notFound" class="o_error">This transfer hasn't been opened online yet, so it isn't available offline.</p>

            <div t-if="state.picking" class="o_move_list">
                <div t-foreach="state.picking.moves" t-as="move" t-key="move.id"
                     class="o_move_row" t-att-class="moveRowClass(move)">
                    <div class="o_move_info">
                        <span class="o_move_product" t-esc="move.productName"/>
                        <span class="o_move_barcode" t-esc="move.barcode"/>
                    </div>
                    <div class="o_move_qty">
                        <button class="o_qty_btn" t-on-click="() => this.adjustQty(move, -1)">−</button>
                        <input class="o_qty_input" type="number" min="0" step="any"
                               t-att-value="move.quantity"
                               t-on-change="(ev) => this.setQtyFromInput(move, ev)"/>
                        <span class="o_qty_demand">/ <t t-esc="move.demandQty"/> <t t-esc="move.uomName"/></span>
                        <button class="o_qty_btn" t-on-click="() => this.adjustQty(move, 1)">+</button>
                    </div>
                </div>
                <p t-if="!state.picking.moves.length" class="o_empty">Nothing to pick on this transfer.</p>
            </div>

            <div t-if="state.flash" class="o_scan_flash" t-att-class="'o_scan_flash_' + state.flash.type" t-esc="state.flash.message"/>

            <div t-if="state.picking" class="o_scan_footer">
                <ScanInput onScan="(code) => this.onScan(code)"/>
                <div class="o_scan_actions">
                    <button t-if="cameraSupported" class="o_camera_button" t-on-click="() => this.openCamera()">📷 Camera</button>
                    <button class="o_validate_button" t-on-click="() => this.onValidate()">Validate</button>
                </div>
            </div>

            <CameraScannerDialog t-if="state.showCamera"
                                 onScan="(code) => this.onCameraScan(code)"
                                 onClose="() => this.closeCamera()"/>
        </div>
    `;
    static components = { ScanInput, CameraScannerDialog };
    static props = {
        pickingId: Number,
        onDone: Function,
    };

    setup() {
        this.state = useState({
            loading: true,
            error: "",
            fromCache: false,
            picking: null,
            showCamera: false,
            flash: null,
        });
        this.flashTimer = null;
        onWillStart(() => this.load());
        onWillUnmount(() => clearTimeout(this.flashTimer));
    }

    get cameraSupported() {
        return isCameraScanningSupported();
    }

    get notFound() {
        return !this.state.loading && !this.state.error && !this.state.picking;
    }

    async load() {
        this.state.loading = true;
        this.state.error = "";
        try {
            const { picking, fromCache } = await loadPickingDetail(this.props.pickingId);
            this.state.picking = picking;
            this.state.fromCache = fromCache;
        } catch (err) {
            this.state.error = err.message;
        } finally {
            this.state.loading = false;
        }
    }

    moveRowClass(move) {
        return move.demandQty > 0 && move.quantity >= move.demandQty ? "o_move_done" : "";
    }

    flash(type, message) {
        this.state.flash = { type, message };
        clearTimeout(this.flashTimer);
        this.flashTimer = setTimeout(() => {
            this.state.flash = null;
        }, 1500);
    }

    applyQty(move, quantity) {
        move.quantity = quantity;
        move.picked = quantity > 0;
        setScannedQty(this.props.pickingId, move.id, quantity);
    }

    adjustQty(move, delta) {
        this.applyQty(move, Math.max(0, (move.quantity || 0) + delta));
    }

    setQtyFromInput(move, ev) {
        const value = Math.max(0, parseFloat(ev.target.value) || 0);
        this.applyQty(move, value);
    }

    onScan(code) {
        const move = this.state.picking?.moves.find((m) => m.barcode && m.barcode === code);
        if (!move) {
            this.flash("error", `No match for "${code}" on this transfer`);
            if (navigator.vibrate) {
                navigator.vibrate([80, 60, 80]);
            }
            return;
        }
        this.adjustQty(move, 1);
        this.flash("success", `${move.productName} +1`);
        if (navigator.vibrate) {
            navigator.vibrate(60);
        }
    }

    openCamera() {
        this.state.showCamera = true;
    }

    closeCamera() {
        this.state.showCamera = false;
    }

    onCameraScan(code) {
        this.closeCamera();
        this.onScan(code);
    }

    async onValidate() {
        await queueValidate(this.props.pickingId);
        this.props.onDone();
    }
}
