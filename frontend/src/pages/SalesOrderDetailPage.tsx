import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, FileText, PackageCheck, ShieldCheck } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { api, ApiError } from "../lib/api";
import { hasPermission } from "../lib/permissions";
import { SalesOrder } from "../types/sales";
import { StatusNotice } from "../components/MasterDataControls";

export function SalesOrderDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const [order, setOrder] = useState<SalesOrder | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const canApprove = hasPermission(user, "sales_orders:approve");
  const canInvoice = hasPermission(user, "invoices:manage");
  const canDispatch = hasPermission(user, "dispatches:manage");

  const loadOrder = async () => {
    if (!id) return;
    setLoading(true);
    try {
      setOrder(await api.getSalesOrder(id));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load sales order.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadOrder();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const handleGenerateInvoice = async () => {
    if (!order) return;
    setError(null);
    setSuccess(null);
    try {
      const inv = await api.createInvoice({ sales_order_id: order.id });
      setSuccess(`Generated GST Invoice ${inv.invoice_number}.`);
      await loadOrder();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to generate invoice.");
    }
  };

  const handleDispatch = async () => {
    if (!order) return;
    setError(null);
    setSuccess(null);
    try {
      const dsp = await api.createDispatch({ sales_order_id: order.id });
      setSuccess(`Recorded Dispatch ${dsp.dispatch_number} and updated finished stock.`);
      await loadOrder();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to record dispatch.");
    }
  };

  if (loading) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-xs text-slate-500">
        Loading order details...
      </div>
    );
  }
  if (!order) return <StatusNotice error={error ?? "Order not found."} />;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Link
            to={canApprove ? "/sales/admin" : "/sales/my-orders"}
            className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700"
          >
            <ArrowLeft className="h-3.5 w-3.5" /> Back
          </Link>
          <div>
            <h2 className="font-mono text-lg font-semibold text-slate-900">{order.order_number}</h2>
            <p className="text-xs text-slate-500">
              {order.customer_name} ({order.customer_state}) • Place of Supply: {order.place_of_supply}
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Link
            to={`/sales/orders/${order.id}/stock-check`}
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-medium text-slate-700"
          >
            Stock Check
          </Link>
          {canApprove && ["SUBMITTED", "UNDER_REVIEW", "AWAITING_STOCK"].includes(order.status) && (
            <Link
              to={`/sales/orders/${order.id}/approve`}
              className="inline-flex items-center gap-1.5 rounded-lg bg-slate-900 px-3 py-2 text-xs font-medium text-white"
            >
              <ShieldCheck className="h-3.5 w-3.5" /> Review / Approve
            </Link>
          )}
          {canInvoice && ["APPROVED", "PARTIALLY_FULFILLED"].includes(order.status) && (
            <button
              type="button"
              onClick={handleGenerateInvoice}
              className="inline-flex items-center gap-1.5 rounded-lg bg-sky-700 px-3 py-2 text-xs font-medium text-white"
            >
              <FileText className="h-3.5 w-3.5" /> Generate GST Invoice
            </button>
          )}
          {canDispatch && order.status === "INVOICED" && (
            <button
              type="button"
              onClick={handleDispatch}
              className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-700 px-3 py-2 text-xs font-medium text-white"
            >
              <PackageCheck className="h-3.5 w-3.5" /> Dispatch & Deduct Stock
            </button>
          )}
          {order.invoice_id && (
            <Link
              to={`/invoices/${order.invoice_id}`}
              className="rounded-lg border border-sky-200 bg-sky-50 px-3 py-2 text-xs font-medium text-sky-800"
            >
              View Invoice {order.invoice_number}
            </Link>
          )}
        </div>
      </div>

      <StatusNotice error={error} success={success} />

      {order.has_stock_shortage && (
        <div className="rounded-xl border border-amber-300 bg-amber-50 p-4 text-xs text-amber-900">
          <strong>Stock Shortage Flagged:</strong> {order.shortage_notes}
        </div>
      )}

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-50 text-[11px] uppercase tracking-wider text-slate-500">
            <tr>
              <th className="px-4 py-3 font-medium">Product</th>
              <th className="px-4 py-3 font-medium">HSN</th>
              <th className="px-4 py-3 font-medium">Requested</th>
              <th className="px-4 py-3 font-medium">Approved</th>
              <th className="px-4 py-3 font-medium">Unit Price</th>
              <th className="px-4 py-3 font-medium">Taxable</th>
              <th className="px-4 py-3 font-medium">GST</th>
              <th className="px-4 py-3 font-medium">Line Total</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {order.items.map((it) => (
              <tr key={it.id}>
                <td className="px-4 py-3 font-medium text-slate-900">
                  {it.product_name} <span className="text-slate-500">({it.sku})</span>
                </td>
                <td className="px-4 py-3 font-mono">{it.hsn_code}</td>
                <td className="px-4 py-3 font-mono">{Number(it.requested_quantity)} {it.unit_symbol}</td>
                <td className="px-4 py-3 font-mono">{Number(it.approved_quantity)} {it.unit_symbol}</td>
                <td className="px-4 py-3 font-mono">Rs {Number(it.unit_price).toFixed(2)}</td>
                <td className="px-4 py-3 font-mono">Rs {Number(it.taxable_value).toFixed(2)}</td>
                <td className="px-4 py-3 font-mono">
                  {order.tax_type === "INTRA_STATE"
                    ? `CGST ${Number(it.cgst_amount).toFixed(2)} + SGST ${Number(it.sgst_amount).toFixed(2)}`
                    : `IGST ${Number(it.igst_amount).toFixed(2)}`}
                </td>
                <td className="px-4 py-3 font-mono font-semibold">Rs {Number(it.line_total).toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
