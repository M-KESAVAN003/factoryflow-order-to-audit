import { AlertTriangle, CheckCircle2, CloudOff, Download, RefreshCw, UploadCloud } from "lucide-react";
import { useOfflineSync } from "../context/OfflineSyncContext";
import { OfflineSyncStatus } from "../types/offline";

export function OfflineSyncBadge({ status }: { status: OfflineSyncStatus }) {
  const styles: Record<OfflineSyncStatus, string> = {
    PENDING_SYNC: "bg-amber-100 text-amber-800 border-amber-200",
    SYNCING: "bg-sky-100 text-sky-800 border-sky-200",
    SYNCED: "bg-emerald-100 text-emerald-800 border-emerald-200",
    SYNC_FAILED: "bg-rose-100 text-rose-800 border-rose-200",
    NEEDS_REVIEW: "bg-orange-100 text-orange-800 border-orange-200",
    CONFLICT: "bg-purple-100 text-purple-800 border-purple-200",
  };
  const labels: Record<OfflineSyncStatus, string> = {
    PENDING_SYNC: "Pending Sync",
    SYNCING: "Syncing",
    SYNCED: "Synced",
    SYNC_FAILED: "Sync Failed",
    NEEDS_REVIEW: "Needs Review",
    CONFLICT: "Conflict",
  };
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold ${styles[status]}`}
    >
      {labels[status]}
    </span>
  );
}

export function NetworkStatusBanner() {
  const {
    isOnline,
    networkState,
    syncing,
    pendingCount,
    failedCount,
    updateAvailable,
    installPromptAvailable,
    promptInstall,
    applyAppUpdate,
    syncNow,
  } = useOfflineSync();

  const meta = {
    ONLINE: {
      label: "Online – Connected",
      cls: "border-emerald-200 bg-emerald-50 text-emerald-800",
      Icon: CheckCircle2,
    },
    OFFLINE: {
      label: "Offline – No Internet",
      cls: "border-slate-300 bg-slate-100 text-slate-800",
      Icon: CloudOff,
    },
    SYNCING: {
      label: "Syncing – Uploading Orders",
      cls: "border-sky-200 bg-sky-50 text-sky-800",
      Icon: UploadCloud,
    },
    PENDING: {
      label: "Pending – Orders Waiting",
      cls: "border-amber-200 bg-amber-50 text-amber-800",
      Icon: RefreshCw,
    },
    SYNC_FAILED: {
      label: "Sync Failed – Action Required",
      cls: "border-rose-200 bg-rose-50 text-rose-800",
      Icon: AlertTriangle,
    },
  }[networkState];

  const Icon = meta.Icon;

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        <span
          data-testid="network-status-pill"
          className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium ${meta.cls}`}
        >
          <Icon className={`h-3.5 w-3.5 ${syncing ? "animate-spin" : ""}`} />
          {meta.label}
        </span>

        {isOnline && (pendingCount > 0 || failedCount > 0) && (
          <button
            type="button"
            disabled={syncing}
            onClick={() => void syncNow(failedCount > 0)}
            className="inline-flex items-center gap-1 rounded-md bg-slate-900 px-2.5 py-1 text-[11px] font-medium text-white hover:bg-slate-800 disabled:opacity-50"
          >
            <RefreshCw className="h-3 w-3" /> Sync Now ({pendingCount + failedCount})
          </button>
        )}

        {installPromptAvailable && (
          <button
            type="button"
            onClick={() => void promptInstall()}
            className="inline-flex items-center gap-1 rounded-md border border-sky-300 bg-sky-50 px-2.5 py-1 text-[11px] font-medium text-sky-800 hover:bg-sky-100"
          >
            <Download className="h-3 w-3" /> Install PWA
          </button>
        )}
      </div>

      {updateAvailable && (
        <div className="flex items-center justify-between gap-2 rounded-lg border border-sky-200 bg-sky-50 px-3 py-1.5 text-xs text-sky-900">
          <span>New FactoryFlow PWA version available.</span>
          <button
            type="button"
            onClick={applyAppUpdate}
            className="rounded bg-sky-700 px-2.5 py-0.5 text-[11px] font-semibold text-white hover:bg-sky-800"
          >
            Update Now
          </button>
        </div>
      )}
    </div>
  );
}
