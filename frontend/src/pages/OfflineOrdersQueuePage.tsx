import { Link } from "react-router-dom";
import { AlertTriangle, CheckCircle2, RefreshCw } from "lucide-react";
import { useOfflineSync } from "../context/OfflineSyncContext";
import { OfflineSyncBadge } from "../components/NetworkStatusBanner";

export type OfflineQueueMode = "pending" | "history" | "failed";

export function OfflineOrdersQueuePage({ mode }: { mode: OfflineQueueMode }) {
  const {
    isOnline,
    syncing,
    offlineOrders,
    lastOrderSyncMessage,
    syncNow,
    retryOrder,
    resolveOrderConflict,
  } = useOfflineSync();

  const filtered = offlineOrders.filter((o) => {
    if (mode === "pending") {
      return o.syncStatus === "PENDING_SYNC" || o.syncStatus === "SYNCING";
    }
    if (mode === "failed") {
      return (
        o.syncStatus === "SYNC_FAILED" ||
        o.syncStatus === "NEEDS_REVIEW" ||
        o.syncStatus === "CONFLICT"
      );
    }
    return o.syncStatus === "SYNCED" || o.syncStatus === "NEEDS_REVIEW";
  });

  const heading = {
    pending: "Pending Sync Orders",
    history: "Offline Sync History",
    failed: "Failed & Review Orders",
  }[mode];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">{heading}</h2>
          <p className="text-xs text-slate-500">
            IndexedDB order queue synced idempotently to PostgreSQL as Submitted for admin review.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Link
            to="/sales/offline-order"
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-medium text-slate-800 hover:bg-slate-50"
          >
            + Offline Order
          </Link>
          <button
            type="button"
            disabled={!isOnline || syncing}
            onClick={() => void syncNow(true)}
            className="inline-flex items-center gap-1.5 rounded-lg bg-slate-900 px-3 py-2 text-xs font-medium text-white hover:bg-slate-800 disabled:opacity-50"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${syncing ? "animate-spin" : ""}`} />
            Sync Now
          </button>
        </div>
      </div>

      <div className="flex flex-wrap gap-2 text-xs">
        <Link
          to="/sales/pending-sync"
          className={`rounded-lg px-3 py-1.5 font-medium ${
            mode === "pending" ? "bg-slate-900 text-white" : "bg-white border border-slate-200 text-slate-700"
          }`}
        >
          Pending Sync
        </Link>
        <Link
          to="/sales/failed-orders"
          className={`rounded-lg px-3 py-1.5 font-medium ${
            mode === "failed" ? "bg-slate-900 text-white" : "bg-white border border-slate-200 text-slate-700"
          }`}
        >
          Failed / Needs Review
        </Link>
        <Link
          to="/sales/sync-history"
          className={`rounded-lg px-3 py-1.5 font-medium ${
            mode === "history" ? "bg-slate-900 text-white" : "bg-white border border-slate-200 text-slate-700"
          }`}
        >
          Sync History
        </Link>
      </div>

      {lastOrderSyncMessage && (
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs text-emerald-800">
          {lastOrderSyncMessage}
        </div>
      )}

      <div className="space-y-3">
        {filtered.map((o) => (
          <div
            key={o.localOrderId}
            className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm space-y-2 text-xs"
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="space-y-0.5">
                <div className="flex flex-wrap items-center gap-2">
                  <Link
                    to={`/sales/offline-orders/${o.localOrderId}`}
                    className="font-mono font-semibold text-slate-900 hover:underline"
                  >
                    {o.localOrderId}
                  </Link>
                  <OfflineSyncBadge status={o.syncStatus} />
                  {o.serverOrderNumber && (
                    <Link
                      to={`/sales/orders/${o.serverOrderId}`}
                      className="rounded bg-slate-100 px-2 py-0.5 font-mono text-[11px] font-medium text-sky-800 hover:underline"
                    >
                      Server: {o.serverOrderNumber} ({o.serverOrderId})
                    </Link>
                  )}
                </div>
                <div className="text-slate-700">
                  <strong>{o.customerName}</strong> ({o.customerState}) — {o.productNameSnapshot} ×{" "}
                  <span className="font-mono">{o.quantity}</span> @ cached Rs{" "}
                  <span className="font-mono">{o.cachedUnitPrice}</span>
                </div>
              </div>

              <div className="flex items-center gap-2">
                {(o.syncStatus === "SYNC_FAILED" || o.syncStatus === "PENDING_SYNC" || o.syncStatus === "CONFLICT") && (
                  <button
                    type="button"
                    disabled={!isOnline || syncing}
                    onClick={() => void retryOrder(o.localOrderId)}
                    className="inline-flex items-center gap-1 rounded-md bg-slate-900 px-2.5 py-1.5 text-[11px] font-medium text-white disabled:opacity-50"
                  >
                    <RefreshCw className="h-3 w-3" /> Retry Sync
                  </button>
                )}
                {(o.syncStatus === "NEEDS_REVIEW" || o.syncStatus === "CONFLICT") && (
                  <button
                    type="button"
                    onClick={() => void resolveOrderConflict(o.localOrderId)}
                    className="inline-flex items-center gap-1 rounded-md border border-emerald-300 bg-emerald-50 px-2.5 py-1.5 text-[11px] font-medium text-emerald-800"
                  >
                    <CheckCircle2 className="h-3 w-3" /> Acknowledge Price
                  </button>
                )}
              </div>
            </div>

            <div className="flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-slate-500">
              <span>Created: {new Date(o.createdAt).toLocaleString()}</span>
              <span>
                Last Attempt:{" "}
                {o.lastSyncAttemptAt ? new Date(o.lastSyncAttemptAt).toLocaleString() : "Not attempted"}
              </span>
              {o.syncedAt && <span>Synced: {new Date(o.syncedAt).toLocaleString()}</span>}
              {o.retryCount > 0 && <span>Retries: {o.retryCount}</span>}
            </div>

            {o.errorMessage && (
              <div className="flex items-start gap-1.5 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-[11px] text-rose-800">
                <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                <span>{o.errorMessage}</span>
              </div>
            )}

            {o.priceConflictNotes && (
              <div className="flex items-start gap-1.5 rounded-lg border border-orange-200 bg-orange-50 px-3 py-2 text-[11px] text-orange-900">
                <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                <span>Price conflict flagged for Admin review: {o.priceConflictNotes}</span>
              </div>
            )}
          </div>
        ))}

        {filtered.length === 0 && (
          <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-xs text-slate-400">
            No offline orders in this queue.
          </div>
        )}
      </div>
    </div>
  );
}
