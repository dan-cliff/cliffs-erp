// Thin JSON-RPC client for Odoo's /web/dataset/call_kw endpoint.
//
// Session auth is carried automatically by the browser's same-origin cookie
// (the user already logged into Odoo to reach /barcode_scanner). type="json"
// controllers like this one are CSRF-exempt, so no token handling is needed.
//
// A failed fetch (offline, DNS, timeout, ...) rejects with `NetworkError` so
// callers (the sync engine) can tell "no connectivity" apart from "the
// server rejected this call".

export class NetworkError extends Error {}

let nextRequestId = 1;

async function jsonRpc(url, params) {
    let response;
    try {
        response = await fetch(url, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            credentials: "same-origin",
            body: JSON.stringify({
                jsonrpc: "2.0",
                method: "call",
                id: nextRequestId++,
                params,
            }),
        });
    } catch (err) {
        throw new NetworkError(err.message);
    }
    if (!response.ok) {
        // Session expired / redirected to login, server error, etc: treat as
        // a real (non-network) failure so it surfaces instead of looping.
        throw new Error(`RPC request to ${url} failed with HTTP ${response.status}`);
    }
    const payload = await response.json();
    if (payload.error) {
        const message =
            payload.error.data?.message || payload.error.message || "Unknown RPC error";
        const error = new Error(message);
        error.rpcError = payload.error;
        throw error;
    }
    return payload.result;
}

export function callKw(model, method, args = [], kwargs = {}) {
    return jsonRpc("/web/dataset/call_kw", { model, method, args, kwargs });
}

export function searchRead(model, domain = [], fields = [], options = {}) {
    return callKw(model, "search_read", [], { domain, fields, ...options });
}
