import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  PackageCheck,
  Play,
  Sliders,
  Trash2,
  XCircle,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { api, ApiError } from "../lib/api";
import { hasPermission } from "../lib/permissions";
import { ProductionRun } from "../types/bomProduction";
import { ConfirmDialog, StatusNotice } from "../components/MasterDataControls";

export function ProductionRunDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const canManage = hasPermission(user, "production_runs:manage");
  const isAdmin = user?.role === "admin";

  const [run, setRun] = useState<ProductionRun | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [confirmPost, setConfirmPost] = useState(false);
  const [showCancelModal, setShowCancelModal] = useState(false);
  const [cancelReason, setCancelReason] = useState("");

  const loadRun = async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      setRun(await api.getProductionRun(id));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load production run.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadRun();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const runAction = async (fn: () => Promise<ProductionRun>, msg: string) => {
    setError(null);
    setSuccess(null);
    try {
      setRun(await fn());
      setSuccess(msg);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Action failed.");
    }
  };

  if (loading) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-xs text-slate-500">
        Loading production run...
      </div>
    );
  }
  if (!run) return <StatusNotice error={error ?? "Production run not found."} />;

  const editable = run.status !== "POSTED" && run.status !== "CANCELLED";

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Link
            to="/production/runs"
            className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
          >
            <ArrowLeft className="h-3.5 w-3.5" /> Back
          </Link>
          <div>
            <h2 className="font-mono text-lg font-semibold text-slate-900">
              {run.order_number} ({run.batch_number})
            </h2>
            <p className="text-xs text-slate-500">
              {run.product_name} &bull; BOM v{run.bom_version_snapshot} &bull; Status:{" "}
              <strong>{run.status}</strong>
            </p>
          </div>
        </div>

        {canManage && run.status !== "CANCELLED" && (
          <div className="flex flex-wrap gap-2">
            {run.status === "DRAFT" && (
              <button
                type="button"
                onClick={() =>
                  void runAction(
                    () => api.updateProductionRun(run.id, { status: "PLANNED" }),
                    "Production run marked as PLANNED."
                  )
                }
                className="rounded-lg border border-sky-300 bg-sky-50 px-3 py-2 text-xs font-semibold text-sky-800 hover:bg-sky-100"
              >
                Mark Planned
              </button>
            )}
            {(run.status === "DRAFT" || run.status === "PLANNED") && (
              <button
                type="button"
                onClick={() =>
                  void runAction(() => api.startProductionRun(run.id), "Production started!")
                }
                className="inline-flex items-center gap-1 rounded-lg bg-amber-600 px-3 py-2 text-xs font-semibold text-white hover:bg-amber-700"
              >
                <Play className="h-3.5 w-3.5" /> Start Production
              </button>
            )}
            {editable && (
              <>
                <Link
                  to={`/production/runs/${run.id}/materials`}
                  className="inline-flex items-center gap-1 rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50"
                >
                  <Sliders className="h-3.5 w-3.5" /> Material Issue
                </Link>
                <Link
                  to={`/production/runs/${run.id}/output`}
                  className="inline-flex items-center gap-1 rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50"
                >
                  <PackageCheck className="h-3.5 w-3.5" /> Record Output
                </Link>
                <Link
                  to={`/production/runs/${run.id}/wastage`}
                  className="inline-flex items-center gap-1 rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50"
                >
                  <Trash2 className="h-3.5 w-3.5" /> Wastage
                </Link>
              </>
            )}
            {run.status === "IN_PROGRESS" && (
              <button
                type="button"
                onClick={() =>
                  void runAction(
                    () => api.completeProductionRun(run.id),
                    "Production run marked COMPLETED. Ready to post to stock ledger."
                  )
                }
                className="inline-flex items-center gap-1 rounded-lg bg-indigo-700 px-3 py-2 text-xs font-semibold text-white hover:bg-indigo-800"
              >
                <CheckCircle2 className="h-3.5 w-3.5" /> Complete Run
              </button>
            )}
            {run.status === "COMPLETED" && (
              <button
                type="button"
                onClick={() => setConfirmPost(true)}
                className="inline-flex items-center gap-1 rounded-lg bg-emerald-700 px-3.5 py-2 text-xs font-semibold text-white hover:bg-emerald-800"
              >
                <CheckCircle2 className="h-3.5 w-3.5" /> Post Production
              </button>
            )}
            {(run.status !== "POSTED" || isAdmin) && (
              <button
                type="button"
                onClick={() => setShowCancelModal(true)}
                className="inline-flex items-center gap-1 rounded-lg border border-rose-200 bg-white px-3 py-2 text-xs font-semibold text-rose-700 hover:bg-rose-50"
              >
                <XCircle className="h-3.5 w-3.5" />
                {run.status === "POSTED" ? "Reverse & Cancel" : "Cancel"}
              </button>
            )}
          </div>
        )}
      </div>

      <StatusNotice error={error} success={success} />

      {run.packaging_warning && (
        <div
          role="alert"
          className="flex items-start gap-2.5 rounded-xl border border-amber-300 bg-amber-50 p-4 text-xs text-amber-900"
        >
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-700" />
          <div>
            <div className="font-semibold">Packaging Capacity Discrepancy</div>
            <p className="mt-0.5">{run.packaging_warning}</p>
          </div>
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-4">
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <p className="text-xs text-slate-500">Expected Output</p>
          <p className="mt-1 font-mono text-lg font-semibold text-slate-900">
            {Number(run.expected_output)} pkts
          </p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <p className="text-xs text-slate-500">Actual Good Output</p>
          <p className="mt-1 font-mono text-lg font-semibold text-slate-900">
            {Number(run.actual_good_output)} pkts
          </p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <p className="text-xs text-slate-500">Yield Variance</p>
          <p
            className={`mt-1 font-mono text-lg font-semibold ${
              run.yield_status === "RED"
                ? "text-rose-700"
                : run.yield_status === "ORANGE"
                ? "text-amber-700"
                : "text-emerald-700"
            }`}
          >
            {run.yield_variance_pct !== null ? `${Number(run.yield_variance_pct).toFixed(2)}%` : "—"} (
            {run.yield_status})
          </p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <p className="text-xs text-slate-500">Damaged Pouches / Scrap</p>
          <p className="mt-1 font-mono text-lg font-semibold text-slate-900">
            {Number(run.damaged_pouches)} / {Number(run.scrap_quantity)}
          </p>
        </div>
      </div>

      {/* Material Requirements & Consumption */}
      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-200 px-5 py-4">
          <h3 className="text-sm font-semibold text-slate-900">
            Planned vs Actual Material Consumption
          </h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-[11px] uppercase tracking-wider text-slate-500">
              <tr>
                <th className="px-4 py-3 font-medium">Material</th>
                <th className="px-4 py-3 font-medium">Available</th>
                <th className="px-4 py-3 font-medium">Planned</th>
                <th className="px-4 py-3 font-medium">Actual Good</th>
                <th className="px-4 py-3 font-medium">Damaged</th>
                <th className="px-4 py-3 font-medium">Total Consumed</th>
                <th className="px-4 py-3 font-medium">Variance</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {run.materials.map((m) => (
                <tr key={m.id}>
                  <td className="px-4 py-3">
                    <div className="font-medium text-slate-900">{m.stock_item_name}</div>
                    <div className="text-[11px] text-slate-500">{m.input_category}</div>
                  </td>
                  <td className="px-4 py-3 font-mono">
                    <span className={m.insufficient_stock ? "font-semibold text-rose-700" : ""}>
                      {Number(m.available_stock)} {m.base_unit_symbol}
                    </span>
                  </td>
                  <td className="px-4 py-3 font-mono">
                    {Number(m.planned_base_quantity)} {m.base_unit_symbol}
                  </td>
                  <td className="px-4 py-3 font-mono">{Number(m.actual_quantity)}</td>
                  <td className="px-4 py-3 font-mono">{Number(m.damaged_quantity)}</td>
                  <td className="px-4 py-3 font-mono font-medium">
                    {Number(m.total_consumed_base_qty)} {m.base_unit_symbol}
                  </td>
                  <td className="px-4 py-3 font-mono">
                    {m.variance_pct !== null ? (
                      <span
                        className={`rounded px-2 py-0.5 text-[11px] font-medium ${
                          m.variance_status === "RED"
                            ? "bg-rose-50 text-rose-700"
                            : m.variance_status === "ORANGE"
                            ? "bg-amber-50 text-amber-800"
                            : "bg-emerald-50 text-emerald-700"
                        }`}
                      >
                        {Number(m.variance_pct).toFixed(2)}% ({m.variance_status})
                      </span>
                    ) : (
                      "—"
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <ConfirmDialog
        open={confirmPost}
        title="Post Production to Stock Ledger"
        message={`Posting ${run.order_number} will atomically deduct consumed materials & packaging from inventory and add ${Number(run.actual_good_output)} finished packets to StockLedger.`}
        confirmLabel="Post Production"
        onConfirm={() => {
          setConfirmPost(false);
          void runAction(
            () => api.postProductionRun(run.id),
            "Production posted! Stock balances and StockLedger updated atomically."
          );
        }}
        onCancel={() => setConfirmPost(false)}
      />

      {showCancelModal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 p-4"
          role="dialog"
          aria-modal="true"
        >
          <div className="w-full max-w-md rounded-xl border border-slate-200 bg-white p-6 shadow-xl">
            <h3 className="text-base font-semibold text-slate-900">Cancel Production Run</h3>
            <p className="mt-1 text-xs text-slate-600">
              {run.status === "POSTED"
                ? "Reversing a posted run restores consumed materials and removes produced goods via REVERSAL ledger entries."
                : "Provide a reason for cancellation."}
            </p>
            <textarea
              rows={3}
              value={cancelReason}
              onChange={(e) => setCancelReason(e.target.value)}
              className="mt-3 w-full rounded-lg border border-slate-300 px-3 py-2 text-xs"
            />
            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setShowCancelModal(false)}
                className="rounded-lg border border-slate-300 px-3.5 py-2 text-xs font-medium text-slate-700"
              >
                Close
              </button>
              <button
                type="button"
                disabled={cancelReason.trim().length < 3}
                onClick={() => {
                  const r = cancelReason.trim();
                  setShowCancelModal(false);
                  void runAction(
                    () => api.cancelProductionRun(run.id, r),
                    "Production run cancelled."
                  );
                }}
                className="rounded-lg bg-rose-600 px-3.5 py-2 text-xs font-semibold text-white hover:bg-rose-700 disabled:opacity-40"
              >
                Confirm Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
