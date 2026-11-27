import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "../lib/api";
import { SalesOrder, SalesOrderStatus } from "../types/sales";
import { StatusNotice } from "../components/MasterDataControls";

export function MyOrdersPage() {
  const [orders, setOrders] = useState<SalesOrder[]>([]);
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const res = await api.listSalesOrders({
          status: statusFilter ? (statusFilter as SalesOrderStatus) : undefined,
          page_size: 50,
        });
        setOrders(res.items);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Failed to load orders.");
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, [statusFilter]);

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">My Sales Orders</h2>
          <p className="text-xs text-slate-500">Live status tracking from submission through GST billing and dispatch.</p>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs"
          >
            <option value="">All Statuses</option>
            <option value="SUBMITTED">Submitted</option>
            <option value="UNDER_REVIEW">Under Review</option>
            <option value="APPROVED">Approved</option>
            <option value="AWAITING_STOCK">Awaiting Stock</option>
            <option value="INVOICED">Invoiced</option>
            <option value="DISPATCHED">Dispatched</option>
            <option value="REJECTED">Rejected</option>
          </select>
          <Link
            to="/sales/mobile-order"
            className="rounded-lg bg-slate-900 px-3 py-2 text-xs font-medium text-white"
          >
            + New Order
          </Link>
        </div>
      </div>

      <StatusNotice error={error} />

      {loading ? (
        <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-xs text-slate-500">
          Loading orders...
        </div>
      ) : (
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-[11px] uppercase tracking-wider text-slate-500">
              <tr>
                <th className="px-4 py-3 font-medium">Order</th>
                <th className="px-4 py-3 font-medium">Customer</th>
                <th className="px-4 py-3 font-medium">Items</th>
                <th className="px-4 py-3 font-medium">Tax Type</th>
                <th className="px-4 py-3 font-medium">Total</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {orders.map((o) => (
                <tr key={o.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3 font-mono font-semibold text-slate-900">{o.order_number}</td>
                  <td className="px-4 py-3">
                    <div className="font-medium text-slate-800">{o.customer_name}</div>
                    <div className="text-[11px] text-slate-500">{o.customer_state}</div>
                  </td>
                  <td className="px-4 py-3">
                    {o.items.map((it) => `${it.product_name} (${Number(it.requested_quantity)})`).join(", ")}
                  </td>
                  <td className="px-4 py-3">{o.tax_type}</td>
                  <td className="px-4 py-3 font-mono font-medium">Rs {Number(o.total_amount).toFixed(2)}</td>
                  <td className="px-4 py-3">
                    <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-medium text-slate-700">
                      {o.status}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <Link to={`/sales/orders/${o.id}`} className="font-medium text-sky-700 hover:underline">
                      Track
                    </Link>
                  </td>
                </tr>
              ))}
              {orders.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-slate-400">
                    No matching sales orders found.
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
