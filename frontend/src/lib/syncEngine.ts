import { api, ApiError } from "./api";
import {
  getCachedCustomers,
  getCachedProducts,
  getOfflineOrder,
  getSessionMeta,
  listOfflineOrders,
  saveCachedCustomers,
  saveCachedProducts,
  saveOfflineOrder,
  saveSessionMeta,
} from "./offlineDb";
import { requestBackgroundOrderSync } from "./pwa";
import {
  CachedCustomerMin,
  CachedProductMin,
  OfflineOrderRecord,
  SalesOrderSyncResponse,
} from "../types/offline";

const FACTORY_STATE = "Tamil Nadu";

function generateUuid(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `id-${Date.now()}-${Math.random().toString(16).slice(2, 10)}-${Math.random().toString(16).slice(2, 10)}`;
}

export function generateLocalOrderId(): string {
  const d = new Date();
  const stamp = `${d.getFullYear()}${String(d.getMonth() + 1).padStart(2, "0")}${String(
    d.getDate()
  ).padStart(2, "0")}`;
  const rand = Math.random().toString(36).slice(2, 6).toUpperCase();
  return `LOC-${stamp}-${rand}`;
}

export async function syncMasterDataFromServer(): Promise<{
  customers: CachedCustomerMin[];
  products: CachedProductMin[];
  syncedAt: string;
}> {
  const syncedAt = new Date().toISOString();
  const [custRes, prodRes] = await Promise.all([
    api.listCustomers({ is_active: true, page_size: 100 }),
    api.listProducts({ is_active: true, page_size: 100 }),
  ]);

  const minCustomers: CachedCustomerMin[] = custRes.items.map((c) => ({
    id: c.id,
    name: c.name,
    customer_type: c.customer_type,
    state: c.state,
    state_code: c.state_code,
    cached_at: syncedAt,
  }));

  const minProducts: CachedProductMin[] = prodRes.items.map((p) => ({
    id: p.id,
    name: p.name,
    sku: p.sku,
    pack_size: p.pack_size,
    unit_symbol: p.unit_symbol,
    selling_price: String(p.selling_price),
    gst_rate: String(p.gst_rate),
    is_active: p.is_active,
    price_cached_at: syncedAt,
  }));

  await Promise.all([saveCachedCustomers(minCustomers), saveCachedProducts(minProducts)]);
  const meta = await getSessionMeta();
  if (meta) {
    await saveSessionMeta({ ...meta, lastMasterSyncAt: syncedAt });
  }
  return { customers: minCustomers, products: minProducts, syncedAt };
}

export async function loadOfflineMasterCache(): Promise<{
  customers: CachedCustomerMin[];
  products: CachedProductMin[];
  lastMasterSyncAt: string | null;
}> {
  const [customers, products, meta] = await Promise.all([
    getCachedCustomers(),
    getCachedProducts(),
    getSessionMeta(),
  ]);
  return {
    customers,
    products,
    lastMasterSyncAt: meta?.lastMasterSyncAt ?? null,
  };
}

export async function createLocalOfflineOrder(params: {
  salesmanId: string;
  customer: CachedCustomerMin;
  product: CachedProductMin;
  quantity: string;
  notes?: string | null;
}): Promise<OfflineOrderRecord> {
  const qtyNum = Number(params.quantity);
  if (!Number.isFinite(qtyNum) || qtyNum <= 0) {
    throw new Error("Quantity must be greater than zero.");
  }
  const priceNum = Number(params.product.selling_price);
  const gstRateNum = Number(params.product.gst_rate);
  const subtotal = Number((qtyNum * priceNum).toFixed(2));
  const gst = Number(((subtotal * gstRateNum) / 100).toFixed(2));
  const total = Number((subtotal + gst).toFixed(2));

  const record: OfflineOrderRecord = {
    localOrderId: generateLocalOrderId(),
    idempotencyKey: generateUuid(),
    salesmanId: params.salesmanId,
    customerId: params.customer.id,
    customerName: params.customer.name,
    customerState: params.customer.state,
    productId: params.product.id,
    productNameSnapshot: params.product.name,
    productSku: params.product.sku,
    unitSymbol: params.product.unit_symbol,
    gstRate: params.product.gst_rate,
    quantity: String(params.quantity).trim(),
    cachedUnitPrice: params.product.selling_price,
    cachedPriceTimestamp: params.product.price_cached_at,
    estimatedSubtotal: subtotal.toFixed(2),
    estimatedGst: gst.toFixed(2),
    estimatedTotal: total.toFixed(2),
    notes: params.notes?.trim() || null,
    createdAt: new Date().toISOString(),
    offlineStatus: "OFFLINE_SAVED",
    syncStatus: "PENDING_SYNC",
    serverOrderId: null,
    serverOrderNumber: null,
    serverStatus: null,
    serverUnitPrice: null,
    serverTotalAmount: null,
    priceConflictNotes: null,
    lastSyncAttemptAt: null,
    syncedAt: null,
    errorMessage: null,
    retryCount: 0,
  };

  await saveOfflineOrder(record);
  void requestBackgroundOrderSync();
  return record;
}

export function estimateOfflineTaxBreakdown(
  customerState: string,
  quantity: string,
  unitPrice: string,
  gstRate: string
) {
  const qty = Math.max(0, Number(quantity || 0));
  const price = Number(unitPrice || 0);
  const rate = Number(gstRate || 0);
  const taxable = Number((qty * price).toFixed(2));
  const isIntra = customerState.trim().toLowerCase() === FACTORY_STATE.toLowerCase();
  const cgst = isIntra ? Number(((taxable * (rate / 2)) / 100).toFixed(2)) : 0;
  const sgst = isIntra ? Number(((taxable * (rate / 2)) / 100).toFixed(2)) : 0;
  const igst = !isIntra ? Number(((taxable * rate) / 100).toFixed(2)) : 0;
  const total = Number((taxable + cgst + sgst + igst).toFixed(2));
  return { isIntra, taxable, cgst, sgst, igst, total };
}

export async function syncSingleOfflineOrder(
  localOrderId: string
): Promise<OfflineOrderRecord> {
  const current = await getOfflineOrder(localOrderId);
  if (!current) {
    throw new Error(`Offline order ${localOrderId} not found.`);
  }
  if (current.syncStatus === "SYNCED") {
    return current;
  }

  const attemptAt = new Date().toISOString();
  const syncingRec: OfflineOrderRecord = {
    ...current,
    syncStatus: "SYNCING",
    lastSyncAttemptAt: attemptAt,
    errorMessage: null,
  };
  await saveOfflineOrder(syncingRec);

  try {
    const resp: SalesOrderSyncResponse = await api.syncOfflineOrder({
      local_order_id: current.localOrderId,
      idempotency_key: current.idempotencyKey,
      customer_id: current.customerId,
      offline_created_at: current.createdAt,
      notes: current.notes,
      items: [
        {
          product_id: current.productId,
          product_name_snapshot: current.productNameSnapshot,
          quantity: current.quantity,
          cached_unit_price: current.cachedUnitPrice,
          cached_price_timestamp: current.cachedPriceTimestamp,
        },
      ],
    });

    const firstLine = resp.order.items[0];
    const updated: OfflineOrderRecord = {
      ...syncingRec,
      syncStatus: resp.price_review_required ? "NEEDS_REVIEW" : "SYNCED",
      serverOrderId: resp.server_order_id,
      serverOrderNumber: resp.server_order_number,
      serverStatus: resp.server_status,
      serverUnitPrice: firstLine ? String(firstLine.unit_price) : null,
      serverTotalAmount: String(resp.order.total_amount),
      priceConflictNotes: resp.price_conflict_notes,
      syncedAt: resp.synced_at,
      errorMessage: null,
    };
    await saveOfflineOrder(updated);
    return updated;
  } catch (err) {
    const isConflict =
      err instanceof ApiError && err.status === 409;
    const errMsg =
      err instanceof ApiError
        ? err.message
        : err instanceof Error
          ? err.message
          : "Network unavailable or synchronization failed.";
    const failed: OfflineOrderRecord = {
      ...syncingRec,
      syncStatus: isConflict ? "CONFLICT" : "SYNC_FAILED",
      errorMessage: errMsg,
      retryCount: current.retryCount + 1,
    };
    await saveOfflineOrder(failed);
    return failed;
  }
}

export async function syncPendingOfflineOrders(
  salesmanId?: string,
  includeFailed = false
): Promise<OfflineOrderRecord[]> {
  const all = await listOfflineOrders(salesmanId);
  const targets = all.filter((o) =>
    includeFailed
      ? o.syncStatus === "PENDING_SYNC" || o.syncStatus === "SYNC_FAILED"
      : o.syncStatus === "PENDING_SYNC"
  );
  const results: OfflineOrderRecord[] = [];
  for (const order of targets) {
    results.push(await syncSingleOfflineOrder(order.localOrderId));
  }
  return results;
}

export async function markConflictResolved(localOrderId: string): Promise<OfflineOrderRecord | null> {
  const current = await getOfflineOrder(localOrderId);
  if (!current) return null;
  const resolved: OfflineOrderRecord = {
    ...current,
    syncStatus: current.serverOrderId ? "SYNCED" : "PENDING_SYNC",
    errorMessage: null,
  };
  await saveOfflineOrder(resolved);
  return resolved;
}
