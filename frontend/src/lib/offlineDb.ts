import {
  CachedCustomerMin,
  CachedProductMin,
  OfflineOrderRecord,
  OfflineSessionMeta,
} from "../types/offline";

const DB_NAME = "factoryflow_offline_db";
const DB_VERSION = 1;

export const STORE_SESSION_META = "session_meta";
export const STORE_CUSTOMERS_CACHE = "customers_cache";
export const STORE_PRODUCTS_CACHE = "products_cache";
export const STORE_OFFLINE_ORDERS = "offline_orders";

let inMemoryFallback: {
  session: OfflineSessionMeta | null;
  customers: Map<string, CachedCustomerMin>;
  products: Map<string, CachedProductMin>;
  orders: Map<string, OfflineOrderRecord>;
} = {
  session: null,
  customers: new Map(),
  products: new Map(),
  orders: new Map(),
};

function hasIndexedDb(): boolean {
  return typeof window !== "undefined" && typeof window.indexedDB !== "undefined";
}

function openOfflineDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = window.indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains(STORE_SESSION_META)) {
        db.createObjectStore(STORE_SESSION_META, { keyPath: "key" });
      }
      if (!db.objectStoreNames.contains(STORE_CUSTOMERS_CACHE)) {
        db.createObjectStore(STORE_CUSTOMERS_CACHE, { keyPath: "id" });
      }
      if (!db.objectStoreNames.contains(STORE_PRODUCTS_CACHE)) {
        db.createObjectStore(STORE_PRODUCTS_CACHE, { keyPath: "id" });
      }
      if (!db.objectStoreNames.contains(STORE_OFFLINE_ORDERS)) {
        const orderStore = db.createObjectStore(STORE_OFFLINE_ORDERS, {
          keyPath: "localOrderId",
        });
        orderStore.createIndex("by_sync_status", "syncStatus", { unique: false });
        orderStore.createIndex("by_salesman", "salesmanId", { unique: false });
        orderStore.createIndex("by_idempotency", "idempotencyKey", { unique: true });
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error ?? new Error("Failed to open IndexedDB."));
  });
}

function txDone(tx: IDBTransaction): Promise<void> {
  return new Promise((resolve, reject) => {
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error ?? new Error("IndexedDB transaction failed."));
    tx.onabort = () => reject(tx.error ?? new Error("IndexedDB transaction aborted."));
  });
}

function reqPromise<T>(req: IDBRequest<T>): Promise<T> {
  return new Promise((resolve, reject) => {
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error ?? new Error("IndexedDB request failed."));
  });
}

export async function saveSessionMeta(meta: OfflineSessionMeta): Promise<void> {
  if (!hasIndexedDb()) {
    inMemoryFallback.session = meta;
    return;
  }
  const db = await openOfflineDb();
  try {
    const tx = db.transaction(STORE_SESSION_META, "readwrite");
    tx.objectStore(STORE_SESSION_META).put(meta);
    await txDone(tx);
  } finally {
    db.close();
  }
}

export async function getSessionMeta(): Promise<OfflineSessionMeta | null> {
  if (!hasIndexedDb()) {
    return inMemoryFallback.session;
  }
  const db = await openOfflineDb();
  try {
    const tx = db.transaction(STORE_SESSION_META, "readonly");
    const res = await reqPromise<OfflineSessionMeta | undefined>(
      tx.objectStore(STORE_SESSION_META).get("active_session")
    );
    return res ?? null;
  } finally {
    db.close();
  }
}

export async function saveCachedCustomers(customers: CachedCustomerMin[]): Promise<void> {
  if (!hasIndexedDb()) {
    inMemoryFallback.customers = new Map(customers.map((c) => [c.id, c]));
    return;
  }
  const db = await openOfflineDb();
  try {
    const tx = db.transaction(STORE_CUSTOMERS_CACHE, "readwrite");
    const store = tx.objectStore(STORE_CUSTOMERS_CACHE);
    store.clear();
    for (const c of customers) {
      store.put(c);
    }
    await txDone(tx);
  } finally {
    db.close();
  }
}

export async function getCachedCustomers(): Promise<CachedCustomerMin[]> {
  if (!hasIndexedDb()) {
    return Array.from(inMemoryFallback.customers.values());
  }
  const db = await openOfflineDb();
  try {
    const tx = db.transaction(STORE_CUSTOMERS_CACHE, "readonly");
    return await reqPromise<CachedCustomerMin[]>(
      tx.objectStore(STORE_CUSTOMERS_CACHE).getAll()
    );
  } finally {
    db.close();
  }
}

export async function saveCachedProducts(products: CachedProductMin[]): Promise<void> {
  if (!hasIndexedDb()) {
    inMemoryFallback.products = new Map(products.map((p) => [p.id, p]));
    return;
  }
  const db = await openOfflineDb();
  try {
    const tx = db.transaction(STORE_PRODUCTS_CACHE, "readwrite");
    const store = tx.objectStore(STORE_PRODUCTS_CACHE);
    store.clear();
    for (const p of products) {
      store.put(p);
    }
    await txDone(tx);
  } finally {
    db.close();
  }
}

export async function getCachedProducts(): Promise<CachedProductMin[]> {
  if (!hasIndexedDb()) {
    return Array.from(inMemoryFallback.products.values());
  }
  const db = await openOfflineDb();
  try {
    const tx = db.transaction(STORE_PRODUCTS_CACHE, "readonly");
    return await reqPromise<CachedProductMin[]>(
      tx.objectStore(STORE_PRODUCTS_CACHE).getAll()
    );
  } finally {
    db.close();
  }
}

export async function saveOfflineOrder(order: OfflineOrderRecord): Promise<void> {
  if (!hasIndexedDb()) {
    inMemoryFallback.orders.set(order.localOrderId, order);
    return;
  }
  const db = await openOfflineDb();
  try {
    const tx = db.transaction(STORE_OFFLINE_ORDERS, "readwrite");
    tx.objectStore(STORE_OFFLINE_ORDERS).put(order);
    await txDone(tx);
  } finally {
    db.close();
  }
}

export async function getOfflineOrder(localOrderId: string): Promise<OfflineOrderRecord | null> {
  if (!hasIndexedDb()) {
    return inMemoryFallback.orders.get(localOrderId) ?? null;
  }
  const db = await openOfflineDb();
  try {
    const tx = db.transaction(STORE_OFFLINE_ORDERS, "readonly");
    const res = await reqPromise<OfflineOrderRecord | undefined>(
      tx.objectStore(STORE_OFFLINE_ORDERS).get(localOrderId)
    );
    return res ?? null;
  } finally {
    db.close();
  }
}

export async function listOfflineOrders(salesmanId?: string): Promise<OfflineOrderRecord[]> {
  let all: OfflineOrderRecord[];
  if (!hasIndexedDb()) {
    all = Array.from(inMemoryFallback.orders.values());
  } else {
    const db = await openOfflineDb();
    try {
      const tx = db.transaction(STORE_OFFLINE_ORDERS, "readonly");
      all = await reqPromise<OfflineOrderRecord[]>(
        tx.objectStore(STORE_OFFLINE_ORDERS).getAll()
      );
    } finally {
      db.close();
    }
  }
  const filtered = salesmanId ? all.filter((o) => o.salesmanId === salesmanId) : all;
  return filtered.sort((a, b) => b.createdAt.localeCompare(a.createdAt));
}

export async function clearOfflineCachesOnLogout(): Promise<void> {
  if (!hasIndexedDb()) {
    inMemoryFallback.session = null;
    inMemoryFallback.customers.clear();
    inMemoryFallback.products.clear();
    for (const [id, ord] of inMemoryFallback.orders.entries()) {
      if (ord.syncStatus === "SYNCED") {
        inMemoryFallback.orders.delete(id);
      }
    }
    return;
  }
  const db = await openOfflineDb();
  try {
    const tx = db.transaction(
      [STORE_SESSION_META, STORE_CUSTOMERS_CACHE, STORE_PRODUCTS_CACHE, STORE_OFFLINE_ORDERS],
      "readwrite"
    );
    tx.objectStore(STORE_SESSION_META).clear();
    tx.objectStore(STORE_CUSTOMERS_CACHE).clear();
    tx.objectStore(STORE_PRODUCTS_CACHE).clear();
    const orderStore = tx.objectStore(STORE_OFFLINE_ORDERS);
    const existing = await reqPromise<OfflineOrderRecord[]>(orderStore.getAll());
    for (const ord of existing) {
      if (ord.syncStatus === "SYNCED") {
        orderStore.delete(ord.localOrderId);
      }
    }
    await txDone(tx);
  } finally {
    db.close();
  }
}

export function resetInMemoryOfflineFallbackForTests(): void {
  inMemoryFallback = {
    session: null,
    customers: new Map(),
    products: new Map(),
    orders: new Map(),
  };
}
