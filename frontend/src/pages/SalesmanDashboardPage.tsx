import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { CloudOff, History, PlusCircle, RefreshCw, ShoppingCart, Users } from "lucide-react";
import { api, ApiError } from "../lib/api";
import { useOfflineSync } from "../context/OfflineSyncContext";
import { SalesOrder, SalesOverview } from "../types/sales";
import { StatusNotice } from "../components/MasterDataControls";

export function SalesmanDashboardPage() {
  const {
    isOnline,
    syncing,
    customers,
    products,
    lastMasterSyncAt,
    pendingCount,
    failedCount,
    needsReviewCount,
    syncedCount,
    syncMasterData,
    syncNow,
  } = useOfflineSync();

  const [overview, setOverview] = useState<SalesOverview | null>(null);
  const [recentOrders, setRecentOrders] = useState<SalesOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshingCatalog, setRefreshingCatalog] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [syncNotice, setSyncNotice] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const [ov, list] = await Promise.all([
          api.salesOverview(),
          api.listSalesOrders({ page: 1, page_size: 8 }),
        ]);
        setOverview(ov);
        setRecentOrders(list.items);
      } catch (err) {
        if (!navigator.onLine) {
          setError(null);
        } else {
          setError(err instanceof ApiError ? err.message : "Failed to load sales dashboard.");
        }
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, []);

  const handleMasterSync = async () => {
    setRefreshingCatalog(true);
    setError(null);
    setSyncNotice(null);
    try {
      await syncMasterData();
      setSyncNotice("Synchronized assigned customers and active products for offline use.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to sync master data.");
    } finally {
      setRefreshingCatalog(false);
    }
  };

  if (loading) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-xs text-slate-500">
        Loading sales overview...
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Salesman Mobile Dashboard (PWA)</h2>
          <p className="text-xs text-slate-500">
            Submit online or offline customer orders in under 60 seconds and synchronize safely.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Link
            to="/sales/offline-order"
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-xs font-medium text-slate-900 hover:bg-slate-50"
          >
            <CloudOff className="h-4 w-4 text-amber-600" /> Offline Order
          </Link>
          <Link
            to="/sales/mobile-order"
            className="inline-flex items-center gap-2 rounded-lg bg-slate-900 px-4 py-2 text-xs font-medium text-white hover:bg-slate-800"
          >
            <PlusCircle className="h-4 w-4" /> Quick Mobile Order
          </Link>
        </div>
      </div>

      <StatusNotice error={error} success={syncNotice} />

      <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <div className="text-xs font-semibold text-slate-900">Offline PWA Sync Center</div>
            <div className="text-[11px] text-slate-500">
              Cached catalog: {customers.length} customers, {products.length} products
              {lastMasterSyncAt ? ` • Synced ${new Date(lastMasterSyncAt).toLocaleString()}` : " • Sync before going offline"}
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              disabled={!isOnline || refreshingCatalog}
              onClick={() => void handleMasterSync()}
              className="inline-flex items-center gap-1 rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-800 hover:bg-slate-50 disabled:opacity-50"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${refreshingCatalog ? "animate-spin" : ""}`} />
              Sync Catalog
            </button>
            <button
              type="button"
              disabled={!isOnline || syncing || pendingCount + failedCount === 0}
              onClick={() => void syncNow(true)}
              className="inline-flex items-center gap-1 rounded-lg bg-slate-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-slate-800 disabled:opacity-50"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${syncing ? "animate-spin" : ""}`} />
              Sync Now ({pendingCount + failedCount})
            </button>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-4 text-xs">
          <Link to="/sales/pending-sync" className="rounded-lg border border-amber-200 bg-amber-50 p-3">
            <div className="text-[11px] text-amber-800">Pending Sync</div>
            <div className="mt-0.5 font-mono text-lg font-semibold text-amber-900">{pendingCount}</div>
          </Link>
          <Link to="/sales/failed-orders" className="rounded-lg border border-rose-200 bg-rose-50 p-3">
            <div className="text-[11px] text-rose-800">Sync Failed</div>
            <div className="mt-0.5 font-mono text-lg font-semibold text-rose-900">{failedCount}</div>
          </Link>
          <Link to="/sales/failed-orders" className="rounded-lg border border-orange-200 bg-orange-50 p-3">
            <div className="text-[11px] text-orange-800">Needs Review</div>
            <div className="mt-0.5 font-mono text-lg font-semibold text-orange-900">{needsReviewCount}</div>
          </Link>
          <Link to="/sales/sync-history" className="rounded-lg border border-emerald-200 bg-emerald-50 p-3">
            <div className="text-[11px] text-emerald-800">Synced Offline</div>
            <div className="mt-0.5 font-mono text-lg font-semibold text-emerald-900">{syncedCount}</div>
          </Link>
        </div>
      </div>

      {overview && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-xs text-slate-500">Submitted Orders</p>
            <p className="mt-1 text-2xl font-semibold text-slate-900">{overview.total_orders}</p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-xs text-slate-500">Pending Review / Hold</p>
            <p className="mt-1 text-2xl font-semibold text-amber-700">
              {overview.pending_review + overview.awaiting_stock}
            </p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-xs text-slate-500">Dispatched</p>
            <p className="mt-1 text-2xl font-semibold text-emerald-700">
              {overview.dispatched_count}
            </p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-xs text-slate-500">Total Order Value</p>
            <p className="mt-1 font-mono text-2xl font-semibold text-slate-900">
              Rs {Number(overview.total_sales_value).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
            </p>
          </div>
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-3">
        <Link
          to="/sales/my-orders"
          className="flex items-center justify-between rounded-xl border border-slate-200 bg-white p-4 shadow-sm hover:border-slate-300"
        >
          <div className="flex items-center gap-3">
            <ShoppingCart className="h-5 w-5 text-slate-700" />
            <div>
              <div className="text-sm font-semibold text-slate-900">My Orders</div>
              <div className="text-xs text-slate-500">Server order status &amp; invoices</div>
            </div>
          </div>
          <span className="text-xs font-medium text-sky-700">Open</span>
        </Link>
        <Link
          to="/sales/customers"
          className="flex items-center justify-between rounded-xl border border-slate-200 bg-white p-4 shadow-sm hover:border-slate-300"
        >
          <div className="flex items-center gap-3">
            <Users className="h-5 w-5 text-slate-700" />
            <div>
              <div className="text-sm font-semibold text-slate-900">Customer-wise Sales</div>
              <div className="text-xs text-slate-500">Volume by retailer &amp; distributor</div>
            </div>
          </div>
          <span className="text-xs font-medium text-sky-700">Open</span>
        </Link>
        <Link
          to="/sales/sync-history"
          className="flex items-center justify-between rounded-xl border border-slate-200 bg-white p-4 shadow-sm hover:border-slate-300"
        >
          <div className="flex items-center gap-3">
            <History className="h-5 w-5 text-slate-700" />
            <div>
              <div className="text-sm font-semibold text-slate-900">Sync History</div>
              <div className="text-xs text-slate-500">Local to server ID mappings</div>
            </div>
          </div>
          <span className="text-xs font-medium text-sky-700">Open</span>
        </Link>
      </div>

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-200 px-5 py-3 text-sm font-semibold text-slate-900">
          Recent Server Orders
        </div>
        <div className="divide-y divide-slate-100">
          {recentOrders.map((o) => (
            <Link
              key={o.id}
              to={`/sales/orders/${o.id}`}
              className="flex flex-wrap items-center justify-between gap-2 px-5 py-3 hover:bg-slate-50"
            >
              <div>
                <div className="font-mono text-xs font-semibold text-slate-900">{o.order_number}</div>
                <div className="text-xs text-slate-600">
                  {o.customer_name} ({o.customer_state}) — {o.order_date}
                </div>
              </div>
              <div className="text-right">
                <div className="font-mono text-xs font-semibold text-slate-900">
                  Rs {Number(o.total_amount).toFixed(2)}
                </div>
                <span className="inline-block rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-medium text-slate-700">
                  {o.status}
                </span>
              </div>
            </Link>
          ))}
          {recentOrders.length === 0 && (
            <div className="px-5 py-6 text-center text-xs text-slate-400">
              {isOnline ? "No sales orders submitted yet." : "Offline mode — view local orders in Sync Queue."}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
