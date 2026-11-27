import React, { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { AlertTriangle, ArrowLeft, CheckCircle2, PauseCircle, XCircle } from "lucide-react";
import { api, ApiError } from "../lib/api";
import { SalesOrder, SalesOrderStockCheck } from "../types/sales";
import { StatusNotice } from "../components/MasterDataControls";

export function OrderApprovalPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [order, setOrder] = useState<SalesOrder | null>(null);
  const [stockCheck, setStockCheck] = useState<SalesOrderStockCheck | null>(null);
  const [qty, setQty] = useState("");
  const [unitPrice, setUnitPrice] = useState("");
  const [rejectReason, setRejectReason] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadAll = async () => {
    if (!id) return;
    setLoading(true);
    try {
      const [o, sc] = await Promise.all([
        api.getSalesOrder(id),
        api.checkSalesOrderStock(id),
      ]);
      setOrder(o);
      setStockCheck(sc);
      if (o.items[0]) {
        setQty(String(Number(o.items[0].requested_quantity)));
        setUnitPrice(String(Number(o.items[0].unit_price)));
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load approval screen.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const handleSaveEdits = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!id || !order?.items[0]) return;
    setSaving(true);
    setError(null);
    try {
      await api.updateSalesOrder(id, {
        status: "UNDER_REVIEW",
        items: [{ product_id: order.items[0].product_id, quantity: qty, unit_price: unitPrice }],
      });
      await loadAll();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to update pending order.");
    } finally {
      setSaving(false);
    }
  };

  const handleDecision = async (action: "approve" | "hold" | "reject") => {
    if (!id) return;
    setSaving(true);
    setError(null);
    try {
      if (action === "approve") {
        await api.approveSalesOrder(id, { hold_if_insufficient: false });
      } else if (action === "hold") {
        await api.approveSalesOrder(id, { hold_if_insufficient: true });
      } else {
        await api.rejectSalesOrder(id, rejectReason.trim() || "Rejected during admin review");
      }
      navigate(`/sales/orders/${id}`, { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Action failed.");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-xs text-slate-500">
        Loading order approval workspace...
      </div>
    );
  }
  if (!order) return <StatusNotice error={error ?? "Order not found."} />;

  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <div className="flex items-center gap-3">
        <Link
          to={`/sales/orders/${order.id}`}
          className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700"
        >
          <ArrowLeft className="h-3.5 w-3.5" /> Back
        </Link>
        <div>
          <h2 className="text-lg font-semibold text-slate-900">
            Review & Approval — {order.order_number}
          </h2>
          <p className="text-xs text-slate-500">
            {order.customer_name} ({order.customer_state}) • {order.tax_type}
          </p>
        </div>
      </div>

      <StatusNotice error={error} />

      {order.price_review_required && (
        <div className="flex items-start gap-2.5 rounded-xl border border-orange-300 bg-orange-50 p-4 text-xs text-orange-950">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-orange-700" />
          <div>
            <div className="font-semibold">Offline Price Change — Admin Review Required</div>
            <div className="mt-0.5">{order.price_conflict_notes}</div>
            {order.items[0]?.submitted_unit_price && (
              <div className="mt-1 font-mono text-[11px]">
                Salesman cached snapshot: Rs {Number(order.items[0].submitted_unit_price).toFixed(2)} | Current server price: Rs {Number(order.items[0].unit_price).toFixed(2)}
              </div>
            )}
          </div>
        </div>
      )}

      {stockCheck && !stockCheck.all_available && (
        <div className="flex items-start gap-2.5 rounded-xl border border-rose-300 bg-rose-50 p-4 text-xs text-rose-900">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-rose-700" />
          <div>
            <div className="font-semibold">Insufficient Finished Goods Stock Warning</div>
            {stockCheck.lines.map((l) => (
              <div key={l.product_id} className="mt-0.5">
                {l.product_name}: Requested {Number(l.requested_quantity)}, Available{" "}
                {Number(l.net_available_stock)}, Shortage {Number(l.shortage_quantity)}. Keep in Awaiting Stock until replenishment.
              </div>
            ))}
          </div>
        </div>
      )}

      {order.items[0] && (
        <form
          onSubmit={handleSaveEdits}
          className="grid gap-4 rounded-xl border border-slate-200 bg-white p-5 shadow-sm sm:grid-cols-3"
        >
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">
              Pending Quantity ({order.items[0].unit_symbol})
            </label>
            <input
              type="number"
              min="1"
              step="1"
              value={qty}
              onChange={(e) => setQty(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 font-mono text-xs"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">
              Authorized Unit Price (Rs)
            </label>
            <input
              type="number"
              min="0.01"
              step="0.01"
              value={unitPrice}
              onChange={(e) => setUnitPrice(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 font-mono text-xs"
            />
          </div>
          <div className="flex items-end">
            <button
              type="submit"
              disabled={saving}
              className="w-full rounded-lg border border-slate-300 bg-slate-50 px-3 py-2 text-xs font-medium text-slate-800 hover:bg-slate-100"
            >
              Update Qty / Price
            </button>
          </div>
        </form>
      )}

      <div className="space-y-4 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap gap-3">
          <button
            type="button"
            disabled={saving || Boolean(stockCheck && !stockCheck.all_available)}
            onClick={() => handleDecision("approve")}
            className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-700 px-4 py-2 text-xs font-medium text-white disabled:opacity-50"
          >
            <CheckCircle2 className="h-4 w-4" /> Approve Order
          </button>
          <button
            type="button"
            disabled={saving}
            onClick={() => handleDecision("hold")}
            className="inline-flex items-center gap-1.5 rounded-lg bg-amber-600 px-4 py-2 text-xs font-medium text-white disabled:opacity-50"
          >
            <PauseCircle className="h-4 w-4" /> Hold (Awaiting Stock)
          </button>
        </div>

        <div className="border-t border-slate-100 pt-4 flex flex-wrap gap-2">
          <input
            type="text"
            value={rejectReason}
            onChange={(e) => setRejectReason(e.target.value)}
            placeholder="Rejection reason..."
            className="min-w-56 flex-1 rounded-lg border border-slate-300 px-3 py-2 text-xs"
          />
          <button
            type="button"
            disabled={saving}
            onClick={() => handleDecision("reject")}
            className="inline-flex items-center gap-1.5 rounded-lg bg-rose-700 px-4 py-2 text-xs font-medium text-white"
          >
            <XCircle className="h-4 w-4" /> Reject Order
          </button>
        </div>
      </div>
    </div>
  );
}
