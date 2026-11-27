import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { useOfflineSync } from "../context/OfflineSyncContext";
import { getOfflineOrder } from "../lib/offlineDb";
import { OfflineOrderRecord } from "../types/offline";
import { OfflineSyncBadge } from "../components/NetworkStatusBanner";

export function OfflineOrderDetailPage() {
  const { localOrderId } = useParams<{ localOrderId: string }>();
  const { isOnline, syncing, retryOrder, resolveOrderConflict, offlineOrders } = useOfflineSync();
  const [record, setRecord] = useState<OfflineOrderRecord | null>(null);

  useEffect(() => {
    const match = offlineOrders.find((o) => o.localOrderId === localOrderId);
    if (match) {
      setRecord(match);
    } else if (localOrderId) {
      void getOfflineOrder(localOrderId).then(setRecord);
    }
  }, [localOrderId, offlineOrders]);

  if (!record) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-xs text-slate-500">
        Offline order not found in IndexedDB.
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="font-mono text-lg font-semibold text-slate-900">{record.localOrderId}</h2>
            <OfflineSyncBadge status={record.syncStatus} />
          </div>
          <p className="text-xs text-slate-500">
            Idempotency Key: <span className="font-mono">{record.idempotencyKey}</span>
          </p>
        </div>

        <div className="flex gap-2">
          {record.syncStatus !== "SYNCED" && (
            <button
              type="button"
              disabled={!isOnline || syncing}
              onClick={() => void retryOrder(record.localOrderId)}
              className="inline-flex items-center gap-1.5 rounded-lg bg-slate-900 px-3 py-2 text-xs font-medium text-white disabled:opacity-50"
            >
              <RefreshCw className="h-3.5 w-3.5" /> Sync Now
            </button>
          )}
          {record.serverOrderId && (
            <Link
              to={`/sales/orders/${record.serverOrderId}`}
              className="rounded-lg border border-sky-300 bg-sky-50 px-3 py-2 text-xs font-medium text-sky-800"
            >
              View Server Order ({record.serverOrderNumber})
            </Link>
          )}
        </div>
      </div>

      {record.priceConflictNotes && (
        <div className="rounded-xl border border-orange-200 bg-orange-50 p-4 text-xs text-orange-900 space-y-2">
          <div className="flex items-center gap-1.5 font-semibold">
            <AlertTriangle className="h-4 w-4" /> Price Change Detected on Server Sync
          </div>
          <p>{record.priceConflictNotes}</p>
          {record.syncStatus === "NEEDS_REVIEW" && (
            <button
              type="button"
              onClick={() => void resolveOrderConflict(record.localOrderId)}
              className="rounded bg-orange-800 px-3 py-1 text-[11px] font-medium text-white"
            >
              Acknowledge &amp; Mark Synced Locally
            </button>
          )}
        </div>
      )}

      {record.errorMessage && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-xs text-rose-900">
          <strong>Sync Error:</strong> {record.errorMessage}
        </div>
      )}

      <div className="grid gap-3 rounded-xl border border-slate-200 bg-white p-4 text-xs shadow-sm sm:grid-cols-2">
        <div>
          <span className="text-slate-500">Customer:</span>{" "}
          <strong>{record.customerName}</strong> ({record.customerState})
        </div>
        <div>
          <span className="text-slate-500">Product:</span>{" "}
          <strong>{record.productNameSnapshot}</strong> ({record.productSku})
        </div>
        <div>
          <span className="text-slate-500">Quantity:</span>{" "}
          <span className="font-mono font-semibold">{record.quantity} {record.unitSymbol}</span>
        </div>
        <div>
          <span className="text-slate-500">Cached Offline Unit Price:</span>{" "}
          <span className="font-mono font-semibold">Rs {record.cachedUnitPrice}</span>
        </div>
        <div>
          <span className="text-slate-500">Server Unit Price:</span>{" "}
          <span className="font-mono">{record.serverUnitPrice ? `Rs ${record.serverUnitPrice}` : "Pending sync"}</span>
        </div>
        <div>
          <span className="text-slate-500">Server Order Status:</span>{" "}
          <span className="font-semibold">{record.serverStatus ?? "Not yet synced"}</span>
        </div>
        <div>
          <span className="text-slate-500">Offline Created At:</span>{" "}
          {new Date(record.createdAt).toLocaleString()}
        </div>
        <div>
          <span className="text-slate-500">Price Snapshot Time:</span>{" "}
          {new Date(record.cachedPriceTimestamp).toLocaleString()}
        </div>
      </div>
    </div>
  );
}
