import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, CheckCircle2, Edit2, XCircle } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { api, ApiError } from "../lib/api";
import { hasPermission } from "../lib/permissions";
import { Purchase } from "../types/inventoryPurchase";
import { ConfirmDialog, StatusNotice } from "../components/MasterDataControls";

export function PurchaseDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const canManage = hasPermission(user, "purchases:manage");

  const [purchase, setPurchase] = useState<Purchase | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [confirmPost, setConfirmPost] = useState(false);
  const [cancelReason, setCancelReason] = useState("");
  const [showCancelModal, setShowCancelModal] = useState(false);

  const loadPurchase = async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      setPurchase(await api.getPurchase(id));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load purchase.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadPurchase();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const handleMarkReviewed = async () => {
    if (!purchase) return;
    setError(null);
    try {
      const updated = await api.updatePurchase(purchase.id, { status: "REVIEWED" });
      setPurchase(updated);
      setSuccess("Purchase marked as Reviewed.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to review purchase.");
    }
  };

  const handlePost = async () => {
    if (!purchase) return;
    setError(null);
    setSuccess(null);
    try {
      const posted = await api.postPurchase(purchase.id);
      setPurchase(posted);
      setConfirmPost(false);
      setSuccess(
        "Purchase receipt posted! Stock balances, weighted-average costs, and StockLedger entries updated."
      );
    } catch (err) {
      setConfirmPost(false);
      setError(err instanceof ApiError ? err.message : "Failed to post purchase.");
    }
  };

  const handleCancel = async () => {
    if (!purchase || cancelReason.trim().length < 3) return;
    setError(null);
    setSuccess(null);
    try {
      const cancelled = await api.cancelPurchase(purchase.id, cancelReason.trim());
      setPurchase(cancelled);
      setShowCancelModal(false);
      setCancelReason("");
      setSuccess("Purchase cancelled and traceable reversal entries recorded if previously posted.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to cancel purchase.");
    }
  };

  if (loading) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-xs text-slate-500">
        Loading purchase details...
      </div>
    );
  }

  if (!purchase) {
    return <StatusNotice error={error ?? "Purchase not found."} />;
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Link
            to="/purchases"
            className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
          >
            <ArrowLeft className="h-3.5 w-3.5" /> Back
          </Link>
          <div>
            <h2 className="font-mono text-lg font-semibold text-slate-900">
              {purchase.reference_number}
            </h2>
            <p className="text-xs text-slate-500">
              Supplier: {purchase.supplier_name} &bull; Date: {purchase.purchase_date}
            </p>
          </div>
        </div>

        {canManage && purchase.status !== "CANCELLED" && (
          <div className="flex flex-wrap gap-2">
            {(purchase.status === "DRAFT" || purchase.status === "REVIEWED") && (
              <>
                <Link
                  to={`/purchases/${purchase.id}/edit`}
                  className="inline-flex items-center gap-1 rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50"
                >
                  <Edit2 className="h-3.5 w-3.5" /> Edit Draft
                </Link>
                {purchase.status === "DRAFT" && (
                  <button
                    type="button"
                    onClick={() => void handleMarkReviewed()}
                    className="rounded-lg border border-sky-300 bg-sky-50 px-3 py-2 text-xs font-semibold text-sky-800 hover:bg-sky-100"
                  >
                    Mark Reviewed
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => setConfirmPost(true)}
                  className="inline-flex items-center gap-1 rounded-lg bg-emerald-700 px-3.5 py-2 text-xs font-semibold text-white hover:bg-emerald-800"
                >
                  <CheckCircle2 className="h-3.5 w-3.5" /> Post Receipt
                </button>
              </>
            )}
            <button
              type="button"
              onClick={() => setShowCancelModal(true)}
              className="inline-flex items-center gap-1 rounded-lg border border-rose-200 bg-white px-3 py-2 text-xs font-semibold text-rose-700 hover:bg-rose-50"
            >
              <XCircle className="h-3.5 w-3.5" />
              {purchase.status === "POSTED" ? "Reverse & Cancel" : "Cancel"}
            </button>
          </div>
        )}
      </div>

      <StatusNotice error={error} success={success} />

      <div className="grid gap-4 sm:grid-cols-4">
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <p className="text-xs text-slate-500">Workflow Status</p>
          <p className="mt-1 font-mono text-base font-semibold text-slate-900">
            {purchase.status}
          </p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <p className="text-xs text-slate-500">Payment Status</p>
          <p className="mt-1 font-mono text-base font-semibold text-slate-900">
            {purchase.payment_status}
          </p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <p className="text-xs text-slate-500">Subtotal / Tax</p>
          <p className="mt-1 font-mono text-base font-semibold text-slate-900">
            ₹{Number(purchase.subtotal).toFixed(2)} + ₹{Number(purchase.tax_amount).toFixed(2)}
          </p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <p className="text-xs text-slate-500">Total Amount</p>
          <p className="mt-1 font-mono text-base font-semibold text-slate-900">
            ₹{Number(purchase.total_amount).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </p>
        </div>
      </div>

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-200 px-5 py-4">
          <h3 className="text-sm font-semibold text-slate-900">Purchase Line Items</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-[11px] uppercase tracking-wider text-slate-500">
              <tr>
                <th className="px-4 py-3 font-medium">Item</th>
                <th className="px-4 py-3 font-medium">Purchased Qty</th>
                <th className="px-4 py-3 font-medium">Base Qty</th>
                <th className="px-4 py-3 font-medium">Rate (₹)</th>
                <th className="px-4 py-3 font-medium">Tax (₹)</th>
                <th className="px-4 py-3 font-medium">Line Total (₹)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {purchase.items.map((item) => (
                <tr key={item.id}>
                  <td className="px-4 py-3">
                    <Link
                      to={`/inventory/items/${item.stock_item_id}`}
                      className="font-medium text-sky-700 hover:underline"
                    >
                      {item.stock_item_name}
                    </Link>
                    <div className="font-mono text-[11px] text-slate-400">
                      {item.stock_item_sku}
                    </div>
                  </td>
                  <td className="px-4 py-3 font-mono">
                    {Number(item.quantity)} {item.unit_symbol}
                  </td>
                  <td className="px-4 py-3 font-mono text-slate-600">
                    {Number(item.base_quantity)} {item.base_unit_symbol}
                  </td>
                  <td className="px-4 py-3 font-mono">₹{Number(item.unit_rate).toFixed(2)}</td>
                  <td className="px-4 py-3 font-mono">
                    ₹{Number(item.tax_amount).toFixed(2)} ({item.tax_rate}%)
                  </td>
                  <td className="px-4 py-3 font-mono font-medium text-slate-900">
                    ₹{Number(item.line_total).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <ConfirmDialog
        open={confirmPost}
        title="Post Purchase Receipt"
        message={`Posting ${purchase.reference_number} will permanently emit StockLedger PURCHASE_RECEIPT entries, increase inventory, and recalculate weighted-average cost.`}
        confirmLabel="Post Receipt"
        onConfirm={() => void handlePost()}
        onCancel={() => setConfirmPost(false)}
      />

      {showCancelModal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 p-4"
          role="dialog"
          aria-modal="true"
        >
          <div className="w-full max-w-md rounded-xl border border-slate-200 bg-white p-6 shadow-xl">
            <h3 className="text-base font-semibold text-slate-900">
              {purchase.status === "POSTED" ? "Reverse & Cancel Purchase" : "Cancel Purchase"}
            </h3>
            <p className="mt-1 text-xs text-slate-600">
              Provide a clear reason for audit traceability.
            </p>
            <textarea
              rows={3}
              required
              value={cancelReason}
              onChange={(e) => setCancelReason(e.target.value)}
              placeholder="Reason for cancellation/reversal..."
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
                onClick={() => void handleCancel()}
                className="rounded-lg bg-rose-600 px-3.5 py-2 text-xs font-semibold text-white hover:bg-rose-700 disabled:opacity-40"
              >
                Confirm Cancellation
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
