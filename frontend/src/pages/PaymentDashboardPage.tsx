import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { PlusCircle } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { api, ApiError } from "../lib/api";
import { hasPermission } from "../lib/permissions";
import { CustomerPayment, ReceivablesReport } from "../types/costingPayment";
import { StatusNotice } from "../components/MasterDataControls";

export function PaymentDashboardPage() {
  const { user } = useAuth();
  const canManage = hasPermission(user, "payments:manage");
  const [receivables, setReceivables] = useState<ReceivablesReport | null>(null);
  const [recentPayments, setRecentPayments] = useState<CustomerPayment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const [rec, pay] = await Promise.all([
          api.receivablesReport(),
          api.listPayments({ page: 1, page_size: 8 }),
        ]);
        setReceivables(rec);
        setRecentPayments(pay.items);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Failed to load payment dashboard.");
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, []);

  if (loading) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-xs text-slate-500">
        Loading customer collections and receivables...
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Payment & Collections Dashboard</h2>
          <p className="text-xs text-slate-500">
            Track customer receipts, invoice allocations, advances, and outstanding receivables.
          </p>
        </div>
        {canManage && (
          <Link
            to="/payments/new"
            className="inline-flex items-center gap-1.5 rounded-lg bg-slate-900 px-3 py-2 text-xs font-medium text-white"
          >
            <PlusCircle className="h-4 w-4" /> Record Customer Payment
          </Link>
        )}
      </div>

      <StatusNotice error={error} />

      {receivables && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-xs text-slate-500">Total Invoiced</p>
            <p className="mt-1 font-mono text-2xl font-semibold text-slate-900">
              Rs {Number(receivables.total_invoiced).toFixed(2)}
            </p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-xs text-slate-500">Total Collected</p>
            <p className="mt-1 font-mono text-2xl font-semibold text-emerald-700">
              Rs {Number(receivables.total_collected).toFixed(2)}
            </p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-xs text-slate-500">Outstanding Receivables</p>
            <p className="mt-1 font-mono text-2xl font-semibold text-amber-700">
              Rs {Number(receivables.total_outstanding).toFixed(2)}
            </p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-xs text-slate-500">Unallocated Advances</p>
            <p className="mt-1 font-mono text-2xl font-semibold text-sky-700">
              Rs {Number(receivables.total_unallocated_advances).toFixed(2)}
            </p>
          </div>
        </div>
      )}

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-200 px-5 py-3 text-sm font-semibold text-slate-900">
          Recent Customer Payments
        </div>
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-50 text-[11px] uppercase tracking-wider text-slate-500">
            <tr>
              <th className="px-4 py-3 font-medium">Reference</th>
              <th className="px-4 py-3 font-medium">Customer</th>
              <th className="px-4 py-3 font-medium">Method / Date</th>
              <th className="px-4 py-3 font-medium">Received</th>
              <th className="px-4 py-3 font-medium">Allocated</th>
              <th className="px-4 py-3 font-medium">Advance</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {recentPayments.map((p) => (
              <tr key={p.id}>
                <td className="px-4 py-3 font-mono font-semibold text-slate-900">{p.payment_reference}</td>
                <td className="px-4 py-3">
                  <Link to={`/customers/${p.customer_id}/ledger`} className="text-sky-700 hover:underline">
                    {p.customer_name}
                  </Link>
                </td>
                <td className="px-4 py-3">{p.payment_method} ({p.payment_date})</td>
                <td className="px-4 py-3 font-mono font-semibold">Rs {Number(p.amount_received).toFixed(2)}</td>
                <td className="px-4 py-3 font-mono text-emerald-700">Rs {Number(p.allocated_amount).toFixed(2)}</td>
                <td className="px-4 py-3 font-mono text-amber-700">Rs {Number(p.unallocated_advance).toFixed(2)}</td>
              </tr>
            ))}
            {recentPayments.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-slate-400">
                  No customer payments recorded yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
