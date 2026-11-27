import React, { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { CheckCircle2, Clock, CloudOff, RefreshCw, Search, Wifi } from "lucide-react";
import { useOfflineSync } from "../context/OfflineSyncContext";
import { estimateOfflineTaxBreakdown } from "../lib/syncEngine";
import { OfflineOrderRecord } from "../types/offline";
import { OfflineSyncBadge } from "../components/NetworkStatusBanner";
import { StatusNotice } from "../components/MasterDataControls";

export function OfflineOrderEntryPage() {
  const {
    isOnline,
    customers,
    products,
    offlineOrders,
    lastMasterSyncAt,
    syncMasterData,
    createOfflineOrder,
    syncNow,
    syncing,
  } = useOfflineSync();

  const [customerId, setCustomerId] = useState("");
  const [productSearch, setProductSearch] = useState("");
  const [productId, setProductId] = useState("");
  const [quantity, setQuantity] = useState("150");
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [refreshingCache, setRefreshingCache] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedNotice, setSavedNotice] = useState<OfflineOrderRecord | null>(null);

  useEffect(() => {
    if (!customerId && customers[0]) setCustomerId(customers[0].id);
  }, [customers, customerId]);

  useEffect(() => {
    if (!productId && products.length > 0) {
      const bench = products.find((p) => p.sku === "MUR-200") ?? products[0];
      if (bench) setProductId(bench.id);
    }
  }, [products, productId]);

  const selectedCustomer = useMemo(
    () => customers.find((c) => c.id === customerId) ?? null,
    [customers, customerId]
  );
  const selectedProduct = useMemo(
    () => products.find((p) => p.id === productId && p.is_active) ?? null,
    [products, productId]
  );
  const filteredProducts = useMemo(() => {
    const active = products.filter((p) => p.is_active);
    const q = productSearch.trim().toLowerCase();
    if (!q) return active;
    return active.filter(
      (p) => p.name.toLowerCase().includes(q) || p.sku.toLowerCase().includes(q)
    );
  }, [products, productSearch]);

  const preview = useMemo(() => {
    if (!selectedCustomer || !selectedProduct) {
      return { isIntra: true, taxable: 0, cgst: 0, sgst: 0, igst: 0, total: 0 };
    }
    return estimateOfflineTaxBreakdown(
      selectedCustomer.state,
      quantity,
      selectedProduct.selling_price,
      selectedProduct.gst_rate
    );
  }, [selectedCustomer, selectedProduct, quantity]);

  const handleSyncCatalog = async () => {
    setRefreshingCache(true);
    setError(null);
    try {
      await syncMasterData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to synchronize customers & products.");
    } finally {
      setRefreshingCache(false);
    }
  };

  const handleSaveOffline = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setSavedNotice(null);
    try {
      const rec = await createOfflineOrder({
        customerId,
        productId,
        quantity,
        notes,
      });
      setSavedNotice(rec);
      setNotes("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to store offline order.");
    } finally {
      setSaving(false);
    }
  };

  const pendingOrders = offlineOrders.filter((o) => o.syncStatus === "PENDING_SYNC");

  return (
    <div className="mx-auto max-w-xl space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Offline Order Entry (PWA)</h2>
          <p className="text-xs text-slate-500">
            Save customer orders into IndexedDB even with zero signal; auto-syncs as Submitted when online.
          </p>
        </div>
        <button
          type="button"
          disabled={!isOnline || refreshingCache}
          onClick={() => void handleSyncCatalog()}
          className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-medium text-slate-800 hover:bg-slate-50 disabled:opacity-50"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${refreshingCache ? "animate-spin" : ""}`} />
          Sync Customers & Products
        </button>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-slate-200 bg-white px-4 py-3 text-xs shadow-sm">
        <div className="flex items-center gap-2 text-slate-700">
          {isOnline ? (
            <Wifi className="h-4 w-4 text-emerald-600" />
          ) : (
            <CloudOff className="h-4 w-4 text-amber-600" />
          )}
          <span>
            Cached: <strong>{customers.length}</strong> customers, <strong>{products.length}</strong> active products
          </span>
        </div>
        <span className="inline-flex items-center gap-1 text-[11px] text-slate-500">
          <Clock className="h-3 w-3" />
          {lastMasterSyncAt
            ? `Last master sync: ${new Date(lastMasterSyncAt).toLocaleString()}`
            : "Not synced yet"}
        </span>
      </div>

      <StatusNotice error={error} />

      {savedNotice && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-3.5 text-xs text-amber-950 space-y-1">
          <div className="flex items-center justify-between">
            <span className="font-semibold">
              Saved locally: <span className="font-mono">{savedNotice.localOrderId}</span>
            </span>
            <OfflineSyncBadge status={savedNotice.syncStatus} />
          </div>
          <div>
            {savedNotice.customerName} — {savedNotice.productNameSnapshot} x {savedNotice.quantity}
          </div>
          {isOnline && (
            <button
              type="button"
              disabled={syncing}
              onClick={() => void syncNow(false)}
              className="mt-1 inline-flex items-center gap-1 rounded bg-slate-900 px-2.5 py-1 text-[11px] font-medium text-white"
            >
              <RefreshCw className="h-3 w-3" /> Sync Now
            </button>
          )}
        </div>
      )}

      {customers.length === 0 || products.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-300 bg-white p-6 text-center text-xs text-slate-600 space-y-3">
          <p>No cached customers or active products found in IndexedDB yet.</p>
          <p className="text-slate-500">
            Connect to the internet and click <strong>Sync Customers &amp; Products</strong> before heading offline.
          </p>
        </div>
      ) : (
        <form
          onSubmit={handleSaveOffline}
          className="space-y-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5"
        >
          <div>
            <label className="mb-1.5 block text-xs font-medium text-slate-700">
              Synchronized Customer
            </label>
            <select
              value={customerId}
              onChange={(e) => setCustomerId(e.target.value)}
              required
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm"
            >
              {customers.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} ({c.customer_type} — {c.state})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-1.5 block text-xs font-medium text-slate-700">
              Cached Active Product
            </label>
            <div className="relative mb-2">
              <Search className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-slate-400" />
              <input
                type="text"
                value={productSearch}
                onChange={(e) => setProductSearch(e.target.value)}
                placeholder="Search cached products..."
                className="w-full rounded-lg border border-slate-300 py-2 pl-9 pr-3 text-sm"
              />
            </div>
            <select
              value={productId}
              onChange={(e) => setProductId(e.target.value)}
              required
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm"
            >
              {filteredProducts.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} ({p.sku}) — Cached Rs {Number(p.selling_price).toFixed(2)}
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1.5 block text-xs font-medium text-slate-700">
                Quantity ({selectedProduct?.unit_symbol ?? "packet"})
              </label>
              <input
                type="number"
                step="1"
                min="1"
                required
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
                className="w-full rounded-lg border border-slate-300 px-3 py-2.5 font-mono text-sm"
              />
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-medium text-slate-700">
                Last Synced Price
              </label>
              <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-800">
                <div className="font-mono text-sm font-semibold">
                  Rs {selectedProduct ? Number(selectedProduct.selling_price).toFixed(2) : "0.00"}
                </div>
                <div className="text-[10px] text-slate-500">
                  Cached:{" "}
                  {selectedProduct
                    ? new Date(selectedProduct.price_cached_at).toLocaleString()
                    : "—"}
                </div>
              </div>
            </div>
          </div>

          <div>
            <label className="mb-1.5 block text-xs font-medium text-slate-700">Notes</label>
            <input
              type="text"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Field note (optional)"
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            />
          </div>

          <div className="rounded-lg border border-slate-200 bg-slate-50 p-3.5 text-xs space-y-1">
            <div className="flex justify-between text-slate-600">
              <span>Estimated Subtotal (Cached)</span>
              <span className="font-mono">Rs {preview.taxable.toFixed(2)}</span>
            </div>
            <div className="flex justify-between text-slate-600">
              <span>
                {preview.isIntra ? "Est. CGST + SGST" : "Est. IGST"} ({selectedProduct?.gst_rate ?? 0}%)
              </span>
              <span className="font-mono">
                Rs {(preview.cgst + preview.sgst + preview.igst).toFixed(2)}
              </span>
            </div>
            <div className="flex justify-between border-t border-slate-200 pt-1.5 font-semibold text-slate-900">
              <span>Estimated Total</span>
              <span className="font-mono">Rs {preview.total.toFixed(2)}</span>
            </div>
            <p className="pt-1 text-[11px] text-amber-800">
              Offline prices &amp; stock are cached snapshots. Stock is never reserved offline; backend revalidates pricing and Admin verifies stock before approval.
            </p>
          </div>

          <button
            type="submit"
            disabled={saving}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-slate-900 px-4 py-3 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-50"
          >
            <CheckCircle2 className="h-4 w-4" />
            {saving ? "Saving locally..." : "Save Order Locally (Pending Sync)"}
          </button>
        </form>
      )}

      {pendingOrders.length > 0 && (
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm space-y-2">
          <div className="flex items-center justify-between text-xs">
            <span className="font-semibold text-slate-900">
              Queued Offline Orders ({pendingOrders.length})
            </span>
            <Link to="/sales/pending-sync" className="font-medium text-sky-700 hover:underline">
              Open Sync Queue
            </Link>
          </div>
          {pendingOrders.slice(0, 3).map((o) => (
            <div key={o.localOrderId} className="flex items-center justify-between text-xs text-slate-700">
              <span>
                <span className="font-mono font-medium">{o.localOrderId}</span> — {o.customerName} ({o.quantity})
              </span>
              <OfflineSyncBadge status={o.syncStatus} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
