import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Truck } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { api, ApiError } from "../lib/api";
import { hasPermission } from "../lib/permissions";
import { Dispatch, SalesOrder } from "../types/sales";
import { StatusNotice } from "../components/MasterDataControls";

export function DispatchesPage() {
  const { user } = useAuth();
  const canDispatch = hasPermission(user, "dispatches:manage");
  const [dispatches, setDispatches] = useState<Dispatch[]>([]);
  const [readyOrders, setReadyOrders] = useState<SalesOrder[]>([]);
  const [selectedOrderId, setSelectedOrderId] = useState("");
  const [vehicleNumber, setVehicleNumber] = useState("");
  const [transporter, setTransporter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const loadAll = async () => {
    setLoading(true);
    try {
      const [dspRes, ordRes] = await Promise.all([
        api.listDispatches({ page_size: 50 }),
        api.listSalesOrders({ status: "INVOICED", page_size: 50 }),
      ]);
      setDispatches(dspRes.items);
      setReadyOrders(ordRes.items);
      if (ordRes.items[0] && !selectedOrderId) {
        setSelectedOrderId(ordRes.items[0].id);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load dispatches.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleDispatch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedOrderId) return;
    setError(null);
    setSuccess(null);
    try {
      const created = await api.createDispatch({
        sales_order_id: selectedOrderId,
        vehicle_number: vehicleNumber.trim() || null,
        transporter_name: transporter.trim() || null,
      });
      setSuccess(`Recorded Dispatch ${created.dispatch_number} and posted StockLedger deduction.`);
      setSelectedOrderId("");
      setVehicleNumber("");
      setTransporter("");
      await loadAll();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to record dispatch.");
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-slate-900">Dispatch Management</h2>
        <p className="text-xs text-slate-500">
          Physical dispatch validates available finished-goods stock and records append-only SALES_DISPATCH ledger entries.
        </p>
      </div>

      <StatusNotice error={error} success={success} />

      {canDispatch && readyOrders.length > 0 && (
        <form
          onSubmit={handleDispatch}
          className="grid gap-3 rounded-xl border border-slate-200 bg-white p-5 shadow-sm sm:grid-cols-4"
        >
          <select
            value={selectedOrderId}
            onChange={(e) => setSelectedOrderId(e.target.value)}
            required
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs"
          >
            <option value="">Select invoiced order...</option>
            {readyOrders.map((o) => (
              <option key={o.id} value={o.id}>
                {o.order_number} — {o.customer_name} ({o.invoice_number})
              </option>
            ))}
          </select>
          <input
            type="text"
            value={vehicleNumber}
            onChange={(e) => setVehicleNumber(e.target.value)}
            placeholder="Vehicle no. (optional)"
            className="rounded-lg border border-slate-300 px-3 py-2 text-xs"
          />
          <input
            type="text"
            value={transporter}
            onChange={(e) => setTransporter(e.target.value)}
            placeholder="Transporter (optional)"
            className="rounded-lg border border-slate-300 px-3 py-2 text-xs"
          />
          <button
            type="submit"
            className="inline-flex items-center justify-center gap-1.5 rounded-lg bg-emerald-700 px-4 py-2 text-xs font-medium text-white"
          >
            <Truck className="h-4 w-4" /> Record Dispatch
          </button>
        </form>
      )}

      {loading ? (
        <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-xs text-slate-500">
          Loading dispatch register...
        </div>
      ) : (
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-[11px] uppercase tracking-wider text-slate-500">
              <tr>
                <th className="px-4 py-3 font-medium">Dispatch #</th>
                <th className="px-4 py-3 font-medium">Order</th>
                <th className="px-4 py-3 font-medium">Invoice</th>
                <th className="px-4 py-3 font-medium">Customer</th>
                <th className="px-4 py-3 font-medium">Qty Dispatched</th>
                <th className="px-4 py-3 font-medium">Vehicle / Date</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {dispatches.map((d) => (
                <tr key={d.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3 font-mono font-semibold text-slate-900">
                    {d.dispatch_number}
                  </td>
                  <td className="px-4 py-3 font-mono">
                    <Link to={`/sales/orders/${d.sales_order_id}`} className="text-sky-700 hover:underline">
                      {d.order_number}
                    </Link>
                  </td>
                  <td className="px-4 py-3 font-mono">
                    <Link to={`/invoices/${d.invoice_id}`} className="text-sky-700 hover:underline">
                      {d.invoice_number}
                    </Link>
                  </td>
                  <td className="px-4 py-3">{d.customer_name}</td>
                  <td className="px-4 py-3 font-mono">
                    {d.items.map((it) => `${it.product_name}: ${Number(it.quantity)}`).join(", ")}
                  </td>
                  <td className="px-4 py-3">
                    {d.vehicle_number ?? "—"} ({d.dispatch_date})
                  </td>
                </tr>
              ))}
              {dispatches.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-slate-400">
                    No dispatches recorded yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
