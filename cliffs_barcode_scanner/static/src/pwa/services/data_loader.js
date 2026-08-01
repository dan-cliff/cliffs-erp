// Reads go through here: try the network first and refresh the cache on
// success, fall back to whatever's cached when offline. Field names below
// were checked against Odoo 19's actual addons/stock source (not guessed):
// stock.move.line lost qty_done in the 17.0 rework, and doesn't carry a
// reserved-quantity field at all - so scanning operates on stock.move
// (one row per product on a transfer), using its `quantity` (done so far,
// writable via an inverse) and `product_uom_qty` (demand) fields.

import { searchRead, callKw, NetworkError } from "./barcode_rpc.js";
import * as db from "./offline_db.js";
import { syncState } from "./sync_engine.js";

const PICKING_TYPE_FIELDS = ["name", "sequence", "color", "count_picking_ready"];
const PICKING_FIELDS = ["name", "picking_type_id", "state", "partner_id", "scheduled_date", "origin"];
const MOVE_FIELDS = ["product_id", "product_uom", "product_uom_qty", "quantity", "picked", "state"];
const READY_STATES = ["assigned", "confirmed"];

function normalizePickingType(raw) {
    return {
        id: raw.id,
        name: raw.name,
        sequence: raw.sequence,
        color: raw.color,
        readyCount: raw.count_picking_ready,
    };
}

function normalizePicking(raw) {
    return {
        id: raw.id,
        name: raw.name,
        pickingTypeId: raw.picking_type_id ? raw.picking_type_id[0] : false,
        pickingTypeName: raw.picking_type_id ? raw.picking_type_id[1] : "",
        state: raw.state,
        partnerName: raw.partner_id ? raw.partner_id[1] : "",
        scheduledDate: raw.scheduled_date,
        origin: raw.origin || "",
    };
}

function normalizeMove(raw, productById) {
    const productId = raw.product_id ? raw.product_id[0] : false;
    const product = productById[productId] || {};
    return {
        id: raw.id,
        productId,
        productName: raw.product_id ? raw.product_id[1] : "",
        barcode: product.barcode || "",
        uomName: raw.product_uom ? raw.product_uom[1] : "",
        demandQty: raw.product_uom_qty || 0,
        quantity: raw.quantity || 0,
        picked: !!raw.picked,
    };
}

export async function loadOperationTypes() {
    try {
        const raw = await searchRead("stock.picking.type", [], PICKING_TYPE_FIELDS, {
            order: "sequence asc",
        });
        const types = raw.map(normalizePickingType);
        await db.putOperationTypes(types);
        syncState.online = true;
        return { types, fromCache: false };
    } catch (err) {
        if (err instanceof NetworkError) {
            syncState.online = false;
            return { types: await db.getOperationTypes(), fromCache: true };
        }
        throw err;
    }
}

export async function loadPickingList(pickingTypeId) {
    try {
        const raw = await searchRead(
            "stock.picking",
            [
                ["picking_type_id", "=", pickingTypeId],
                ["state", "in", READY_STATES],
            ],
            PICKING_FIELDS,
            { order: "scheduled_date asc" }
        );
        const pickings = raw.map(normalizePicking);
        for (const picking of pickings) {
            const existing = await db.getPicking(picking.id);
            await db.putPicking({ ...picking, moves: existing?.moves || [] });
        }
        syncState.online = true;
        return { pickings, fromCache: false };
    } catch (err) {
        if (err instanceof NetworkError) {
            syncState.online = false;
            const cached = await db.getPickingsForType(pickingTypeId);
            cached.sort((a, b) => (a.scheduledDate || "").localeCompare(b.scheduledDate || ""));
            return { pickings: cached, fromCache: true };
        }
        throw err;
    }
}

export async function loadPickingDetail(pickingId) {
    try {
        const [rawPicking] = await searchRead(
            "stock.picking",
            [["id", "=", pickingId]],
            [...PICKING_FIELDS, "move_ids"]
        );
        if (!rawPicking) {
            throw new Error(`Transfer ${pickingId} not found`);
        }
        const moveIds = rawPicking.move_ids || [];
        const rawMoves = moveIds.length
            ? await callKw("stock.move", "read", [moveIds, MOVE_FIELDS])
            : [];
        const activeMoves = rawMoves.filter((m) => !["cancel", "done"].includes(m.state));
        const productIds = [...new Set(activeMoves.map((m) => m.product_id && m.product_id[0]).filter(Boolean))];
        const products = productIds.length
            ? await callKw("product.product", "read", [productIds, ["barcode", "display_name"]])
            : [];
        const productById = Object.fromEntries(products.map((p) => [p.id, p]));

        const picking = normalizePicking(rawPicking);
        picking.moves = activeMoves.map((m) => normalizeMove(m, productById));
        await db.putPicking(picking);
        syncState.online = true;
        return { picking, fromCache: false };
    } catch (err) {
        if (err instanceof NetworkError) {
            syncState.online = false;
            return { picking: await db.getPicking(pickingId), fromCache: true };
        }
        throw err;
    }
}
