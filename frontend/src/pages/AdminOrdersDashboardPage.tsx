import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { AlertTriangle } from "lucide-react";
import { api, ApiError } from "../lib/api";
import { SalesOrder, SalesOverview } from "../types/sales";
import { StatusNotice } from "../components/MasterDataControls";

export function AdminOrdersDashboardPage() {
  const [overview, setOverview] = useState<SalesOverview | null>(null);
  const [orders, setOrders] = useState<SalesOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const [ov, list] = await Promise.all([
          api.salesOverview(),
          api.listSalesOrders({ page: 1, page_size: 50 }),
        ]);
        setOverview(ov);
        setOrders(list.items);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Failed to load admin order queue.");
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, []);

  if (loading) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-xs text-slate-500">
        Loading incoming sales orders...
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-slate-900">Admin Order Management</h2>
        <p className="text-xs text-slate-500">
          Review incoming orders, verify finished-goods availability, generate GST invoices, and record dispatches.
        </p>
      </div>

      <StatusNotice error={error} />

      {overview && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-xs text-slate-500">Incoming / Pending Review</p>
            <p className="mt-1 text-2xl font-semibold text-slate-900">{overview.pending_review}</p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-xs text-slate-500">Awaiting Stock (Shortage)</p>
            <p className="mt-1 text-2xl font-semibold text-amber-700">{overview.awaiting_stock}</p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-xs text-slate-500">Invoiced / Dispatched</p>
            <p className="mt-1 text-2xl font-semibold text-emerald-700">
              {overview.invoiced_count} / {overview.dispatched_count}
            </p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-xs text-slate-500">Total GST Billed</p>
            <p className="mt-1 font-mono text-2xl font-semibold text-slate-900">
              Rs {Number(overview.total_gst_collected).toFixed(2)}
            </p>
          </div>
        </div>
      )}

      <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-50 text-[11px] uppercase tracking-wider text-slate-500">
            <tr>
              <th className="px-3 py-3 font-medium">Order ID</th>
              <th className="px-3 py-3 font-medium">Salesman</th>
              <th className="px-3 py-3 font-medium">Customer</th>
              <th className="px-3 py-3 font-medium">Product</th>
              <th className="px-3 py-3 font-medium">Req / Avail / Short</th>
              <th className="px-3 py-3 font-medium">Tax Preview</th>
              <th className="px-3 py-3 font-medium">Status</th>
              <th className="px-3 py-3 font-medium">Date</th>
              <th className="px-3 py-3 font-medium">Workflow</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {orders.map((o) => {
              const first = o.items[0];
              return (
                <tr key={o.id} className="hover:bg-slate-50">
                  <td className="px-3 py-3 font-mono font-semibold text-slate-900">
                    <Link to={`/sales/orders/${o.id}`} className="hover:underline">
                      {o.order_number}
                    </Link>
                  </td>
                  <td className="px-3 py-3 text-slate-700">{o.salesman_name}</td>
                  <td className="px-3 py-3">
                    <div className="font-medium text-slate-900">{o.customer_name}</div>
                    <div className="text-[11px] text-slate-500">{o.customer_state}</div>
                  </td>
                  <td className="px-3 py-3">{first ? first.product_name : "—"}</td>
                  <td className="px-3 py-3 font-mono">
                    {first ? (
                      <div className="flex items-center gap-1">
                        <span>
                          {Number(first.requested_quantity)} / {Number(first.available_stock)} /{" "}
                          <strong className={Number(first.shortage_quantity) > 0 ? "text-rose-700" : "text-emerald-700"}>
                            {Number(first.shortage_quantity)}
                          </strong>
                        </span>
                        {Number(first.shortage_quantity) > 0 && (
                          <AlertTriangle className="h-3.5 w-3.5 text-rose-600" />
                        )}
                      </div>
                    ) : (
                      "—"
                    )}
                  </td>
                  <td className="px-3 py-3 font-mono">
                    Rs {Number(o.tax_amount).toFixed(2)} ({o.tax_type === "INTRA_STATE" ? "CGST+SGST" : "IGST"})
                  </td>
                  <td className="px-3 py-3">
                    <div className="flex flex-wrap items-center gap-1">
                      <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-medium text-slate-800">
                        {o.status}
                      </span>
                      {o.is_offline_order && (
                        <span className="rounded-full bg-sky-100 px-2 py-0.5 text-[10px] font-medium text-sky-800">
                          PWA Sync
                        </span>
                      )}
                      {o.price_review_required && (
                        <span className="rounded-full bg-orange-100 px-2 py-0.5 text-[10px] font-semibold text-orange-900">
                          Price Review Required
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="px-3 py-3">{o.order_date}</td>
                  <td className="px-3 py-3 space-x-2 whitespace-nowrap">
                    <Link to={`/sales/orders/${o.id}/stock-check`} className="text-sky-700 hover:underline">
                      Stock
                    </Link>
                    <Link to={`/sales/orders/${o.id}/approve`} className="font-medium text-emerald-700 hover:underline">
                      Review
                    </Link>
                  </td>
                </tr>
              );
            })}
            {orders.length === 0 && (
              <tr>
                <td colSpan={9} className="px-4 py-8 text-center text-slate-400">
                  No incoming sales orders.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
