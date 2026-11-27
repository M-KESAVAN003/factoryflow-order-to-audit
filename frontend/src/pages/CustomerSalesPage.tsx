import { useEffect, useState } from "react";
import { api, ApiError } from "../lib/api";
import { SalesOverview } from "../types/sales";
import { StatusNotice } from "../components/MasterDataControls";

export function CustomerSalesPage() {
  const [overview, setOverview] = useState<SalesOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        setOverview(await api.salesOverview());
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Failed to load customer sales.");
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, []);

  if (loading) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-xs text-slate-500">
        Loading customer-wise sales...
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-lg font-semibold text-slate-900">Customer-wise Sales Summary</h2>
        <p className="text-xs text-slate-500">
          Order value, invoiced totals, and dispatch completions grouped per retailer and distributor.
        </p>
      </div>

      <StatusNotice error={error} />

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-50 text-[11px] uppercase tracking-wider text-slate-500">
            <tr>
              <th className="px-4 py-3 font-medium">Customer</th>
              <th className="px-4 py-3 font-medium">Type</th>
              <th className="px-4 py-3 font-medium">State</th>
              <th className="px-4 py-3 font-medium">Orders</th>
              <th className="px-4 py-3 font-medium">Dispatched</th>
              <th className="px-4 py-3 font-medium">Order Value</th>
              <th className="px-4 py-3 font-medium">Invoiced Value</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {overview?.customer_summary.map((row) => (
              <tr key={row.customer_id} className="hover:bg-slate-50">
                <td className="px-4 py-3 font-medium text-slate-900">{row.customer_name}</td>
                <td className="px-4 py-3">{row.customer_type}</td>
                <td className="px-4 py-3">{row.customer_state}</td>
                <td className="px-4 py-3 font-mono">{row.orders_count}</td>
                <td className="px-4 py-3 font-mono">{row.dispatched_count}</td>
                <td className="px-4 py-3 font-mono font-medium">
                  Rs {Number(row.total_order_value).toFixed(2)}
                </td>
                <td className="px-4 py-3 font-mono text-emerald-700">
                  Rs {Number(row.invoiced_value).toFixed(2)}
                </td>
              </tr>
            ))}
            {(!overview || overview.customer_summary.length === 0) && (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-slate-400">
                  No customer orders recorded yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
