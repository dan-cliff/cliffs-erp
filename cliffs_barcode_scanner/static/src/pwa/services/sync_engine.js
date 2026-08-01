import { reactive } from "../../../lib/owl/owl.js";
import { callKw, NetworkError } from "./barcode_rpc.js";
import * as db from "./offline_db.js";

// Shared reactive state: components read it via `useState(syncState)` (Owl's
// reactive() plays nicely across module boundaries - see sync_status_badge.js).
export const syncState = reactive({
    online: navigator.onLine,
    pendingCount: 0,
    syncing: false,
    lastError: null,
});

async function refreshPendingCount() {
    const entries = await db.getOutboxEntries();
    syncState.pendingCount = entries.length;
    return entries;
}

// Handles what button_validate() hands back: `true` when the transfer just
// completed, or an action dict opening a wizard (most commonly the backorder
// confirmation when scanned quantities were less than reserved). We drive
// that wizard headlessly - defaulting to "no backorder" since the scanned
// quantities are the ground truth for what actually happened - instead of
// leaving the transfer stuck half-validated with no UI to finish it.
async function driveValidateResult(pickingId, result) {
    if (!result || result === true) {
        return;
    }
    if (typeof result === "object" && result.res_model === "stock.backorder.confirmation") {
        const context = result.context || {};
        // default_pick_ids already comes as an (4, id) command tuple list
        // meant for this exact many2many field - see
        // StockPicking._action_generate_backorder_wizard in Odoo core.
        const pickIds = context.default_pick_ids || [[4, pickingId]];
        const created = await callKw("stock.backorder.confirmation", "create", [
            { pick_ids: pickIds },
        ]);
        const wizardId = Array.isArray(created) ? created[0] : created;
        try {
            await callKw("stock.backorder.confirmation", "process_cancel_backorder", [[wizardId]]);
        } catch (err) {
            // Naming for "validate without creating a backorder" has moved
            // around between Odoo versions; fall back to the method that
            // creates one rather than leaving the transfer stuck.
            await callKw("stock.backorder.confirmation", "process", [[wizardId]]);
        }
        return;
    }
    throw new Error(
        `Validating this transfer needs a follow-up step (${result.res_model || result.type || "unknown"}) ` +
            "that isn't supported from the scanner yet. Finish it in the regular Odoo backend."
    );
}

async function replayEntry(entry) {
    if (entry.kind === "set_qty") {
        // stock.move.quantity is the actually-done quantity (Odoo 17+ renamed
        // this from stock.move.line.qty_done); picked is set alongside it so
        // the line reads as confirmed if someone opens the transfer in the
        // regular Odoo backend afterwards.
        await callKw("stock.move", "write", [
            [entry.moveId],
            { quantity: entry.quantity, picked: true },
        ]);
    } else if (entry.kind === "validate") {
        const result = await callKw("stock.picking", "button_validate", [[entry.pickingId]]);
        await driveValidateResult(entry.pickingId, result);
    } else {
        throw new Error(`Unknown outbox entry kind: ${entry.kind}`);
    }
}

let flushing = false;

export async function flush() {
    if (flushing) {
        return;
    }
    flushing = true;
    syncState.syncing = true;
    try {
        const entries = await refreshPendingCount();
        const failedPickingIds = new Set();
        for (const entry of entries.sort((a, b) => a.createdAt - b.createdAt)) {
            if (entry.status === "error" || failedPickingIds.has(entry.pickingId)) {
                continue;
            }
            try {
                await replayEntry(entry);
                await db.removeOutboxEntry(entry.localId);
                syncState.online = true;
                syncState.lastError = null;
            } catch (err) {
                if (err instanceof NetworkError) {
                    // No connectivity: stop for now, everything stays queued.
                    syncState.online = false;
                    break;
                }
                // A real rejection from the server: keep the picking's other
                // queued entries pending (order matters) but don't retry this
                // one automatically - surface it for the user to resolve.
                await db.markOutboxEntryError(entry.localId, err.message);
                failedPickingIds.add(entry.pickingId);
                syncState.lastError = err.message;
            }
        }
        await refreshPendingCount();
    } finally {
        syncState.syncing = false;
        flushing = false;
    }
}

export async function retryOutboxEntry(localId) {
    await db.resetOutboxEntryToPending(localId);
    await refreshPendingCount();
    await flush();
}

export async function discardOutboxEntry(localId) {
    await db.removeOutboxEntry(localId);
    await refreshPendingCount();
}

// -- Mutations exposed to the UI: apply optimistically to the local cache,
// queue for sync, and immediately try to flush (so it feels instant while
// online, and just queues quietly while offline). ------------------------

export async function setScannedQty(pickingId, moveId, quantity) {
    const picking = await db.getPicking(pickingId);
    if (picking) {
        const move = picking.moves.find((m) => m.id === moveId);
        if (move) {
            move.quantity = quantity;
            move.picked = true;
        }
        await db.putPicking(picking);
    }
    // Each entry carries the absolute final quantity (not a delta), so
    // replaying it is idempotent no matter how many times sync retries.
    await db.addOutboxEntry({ kind: "set_qty", pickingId, moveId, quantity });
    await refreshPendingCount();
    flush();
}

export async function queueValidate(pickingId) {
    const picking = await db.getPicking(pickingId);
    if (picking) {
        picking.pendingValidate = true;
        await db.putPicking(picking);
    }
    await db.addOutboxEntry({ kind: "validate", pickingId });
    await refreshPendingCount();
    flush();
}

// -- Wiring: keep syncState.online honest and retry periodically. ---------

window.addEventListener("online", () => {
    syncState.online = true;
    flush();
});
window.addEventListener("offline", () => {
    syncState.online = false;
});
document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible" && navigator.onLine) {
        flush();
    }
});
setInterval(() => {
    if (navigator.onLine) {
        flush();
    }
}, 30000);

refreshPendingCount();
