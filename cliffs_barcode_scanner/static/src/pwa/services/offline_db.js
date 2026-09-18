// IndexedDB-backed offline cache: operation types, the pickings opened under
// each of them (header + move lines embedded), and an outbox of mutations
// queued while offline (or just-in-case-it-fails-anyway) for the sync engine
// to replay. No external library: the native API is small enough to wrap
// directly, and vendoring one more dependency isn't worth it here.

const DB_NAME = "cliffs_barcode_scanner";
const DB_VERSION = 1;

let dbPromise = null;

function openDb() {
    if (!dbPromise) {
        dbPromise = new Promise((resolve, reject) => {
            const req = indexedDB.open(DB_NAME, DB_VERSION);
            req.onupgradeneeded = () => {
                const db = req.result;
                if (!db.objectStoreNames.contains("operationTypes")) {
                    db.createObjectStore("operationTypes", { keyPath: "id" });
                }
                if (!db.objectStoreNames.contains("pickings")) {
                    const store = db.createObjectStore("pickings", { keyPath: "id" });
                    store.createIndex("by_picking_type_id", "pickingTypeId");
                }
                if (!db.objectStoreNames.contains("outbox")) {
                    db.createObjectStore("outbox", { keyPath: "localId", autoIncrement: true });
                }
            };
            req.onsuccess = () => resolve(req.result);
            req.onerror = () => reject(req.error);
        });
    }
    return dbPromise;
}

async function runTx(storeNames, mode, fn) {
    const db = await openDb();
    return new Promise((resolve, reject) => {
        const tx = db.transaction(storeNames, mode);
        let result;
        Promise.resolve(fn(tx))
            .then((r) => {
                result = r;
            })
            .catch(reject);
        tx.oncomplete = () => resolve(result);
        tx.onerror = () => reject(tx.error);
        tx.onabort = () => reject(tx.error || new Error("IndexedDB transaction aborted"));
    });
}

function reqToPromise(req) {
    return new Promise((resolve, reject) => {
        req.onsuccess = () => resolve(req.result);
        req.onerror = () => reject(req.error);
    });
}

// -- Operation types ---------------------------------------------------

export async function putOperationTypes(operationTypes) {
    return runTx("operationTypes", "readwrite", (tx) => {
        const store = tx.objectStore("operationTypes");
        for (const opType of operationTypes) {
            store.put(opType);
        }
    });
}

export async function getOperationTypes() {
    return runTx("operationTypes", "readonly", (tx) =>
        reqToPromise(tx.objectStore("operationTypes").getAll())
    );
}

// -- Pickings (header + embedded move lines) ----------------------------

export async function putPicking(picking) {
    return runTx("pickings", "readwrite", (tx) => {
        tx.objectStore("pickings").put(picking);
    });
}

export async function getPicking(pickingId) {
    return runTx("pickings", "readonly", (tx) =>
        reqToPromise(tx.objectStore("pickings").get(pickingId))
    );
}

export async function getPickingsForType(pickingTypeId) {
    return runTx("pickings", "readonly", (tx) =>
        reqToPromise(
            tx.objectStore("pickings").index("by_picking_type_id").getAll(pickingTypeId)
        )
    );
}

// -- Outbox ---------------------------------------------------------------

export async function addOutboxEntry(entry) {
    return runTx("outbox", "readwrite", (tx) =>
        reqToPromise(
            tx.objectStore("outbox").add({
                status: "pending",
                errorMessage: null,
                createdAt: Date.now(),
                ...entry,
            })
        )
    );
}

export async function getOutboxEntries() {
    return runTx("outbox", "readonly", (tx) => reqToPromise(tx.objectStore("outbox").getAll()));
}

export async function removeOutboxEntry(localId) {
    return runTx("outbox", "readwrite", (tx) => {
        tx.objectStore("outbox").delete(localId);
    });
}

export async function markOutboxEntryError(localId, errorMessage) {
    return runTx("outbox", "readwrite", (tx) => {
        const store = tx.objectStore("outbox");
        const getReq = store.get(localId);
        getReq.onsuccess = () => {
            const entry = getReq.result;
            if (entry) {
                entry.status = "error";
                entry.errorMessage = errorMessage;
                store.put(entry);
            }
        };
    });
}

export async function resetOutboxEntryToPending(localId) {
    return runTx("outbox", "readwrite", (tx) => {
        const store = tx.objectStore("outbox");
        const getReq = store.get(localId);
        getReq.onsuccess = () => {
            const entry = getReq.result;
            if (entry) {
                entry.status = "pending";
                entry.errorMessage = null;
                store.put(entry);
            }
        };
    });
}
