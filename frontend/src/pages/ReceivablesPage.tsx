import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "../lib/api";
import { ReceivablesReport } from "../types/costingPayment";
import { StatusNotice } from "../components/MasterDataControls";

export function ReceivablesPage() {
  const [report, setReport] = useState<ReceivablesReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        setReport(await api.receivablesReport());
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Failed to load receivables.");
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, []);

  if (loading) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-xs text-slate-500">
        Reconciling receivables...
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Outstanding Receivables</h2>
          <p className="text-xs text-slate-500">
            Customer-wise and invoice-wise balances derived from posted GST invoices and allocations.
          </p>
        </div>
        <Link
          to="/receivables/ageing"
          className="rounded-lg bg-slate-900 px-3 py-2 text-xs font-medium text-white"
        >
          Ageing Report
        </Link>
      </div>

      <StatusNotice error={error} />

      {report && (
        <>
          <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
            <div className="border-b border-slate-200 px-5 py-3 text-sm font-semibold text-slate-900">
              Customer-wise Receivables
            </div>
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-[11px] uppercase tracking-wider text-slate-500">
                <tr>
                  <th className="px-4 py-3 font-medium">Customer</th>
                  <th className="px-4 py-3 font-medium">Invoices</th>
                  <th className="px-4 py-3 font-medium">Invoiced</th>
                  <th className="px-4 py-3 font-medium">Paid</th>
                  <th className="px-4 py-3 font-medium">Outstanding</th>
                  <th className="px-4 py-3 font-medium">Ledger / Statement</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {report.customers.map((c) => (
                  <tr key={c.customer_id}>
                    <td className="px-4 py-3 font-medium text-slate-900">{c.customer_name}</td>
                    <td className="px-4 py-3 font-mono">{c.invoices_count}</td>
                    <td className="px-4 py-3 font-mono">Rs {Number(c.total_invoiced).toFixed(2)}</td>
                    <td className="px-4 py-3 font-mono text-emerald-700">Rs {Number(c.total_paid).toFixed(2)}</td>
                    <td className="px-4 py-3 font-mono font-semibold text-amber-700">
                      Rs {Number(c.total_outstanding).toFixed(2)}
                    </td>
                    <td className="px-4 py-3 space-x-3">
                      <Link to={`/customers/${c.customer_id}/ledger`} className="text-sky-700 hover:underline">
                        Ledger
                      </Link>
                      <Link to={`/customers/${c.customer_id}/statement`} className="text-slate-700 hover:underline">
                        Statement
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
            <div className="border-b border-slate-200 px-5 py-3 text-sm font-semibold text-slate-900">
              Invoice-wise Payment Status
            </div>
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-[11px] uppercase tracking-wider text-slate-500">
                <tr>
                  <th className="px-4 py-3 font-medium">Invoice</th>
                  <th className="px-4 py-3 font-medium">Customer</th>
                  <th className="px-4 py-3 font-medium">Total</th>
                  <th className="px-4 py-3 font-medium">Paid</th>
                  <th className="px-4 py-3 font-medium">Outstanding</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {report.invoices.map((inv) => (
                  <tr key={inv.invoice_id}>
                    <td className="px-4 py-3 font-mono font-semibold">
                      <Link to={`/invoices/${inv.invoice_id}/payments`} className="text-sky-700 hover:underline">
                        {inv.invoice_number}
                      </Link>
                    </td>
                    <td className="px-4 py-3">{inv.customer_name}</td>
                    <td className="px-4 py-3 font-mono">Rs {Number(inv.invoice_amount).toFixed(2)}</td>
                    <td className="px-4 py-3 font-mono text-emerald-700">Rs {Number(inv.paid_amount).toFixed(2)}</td>
                    <td className="px-4 py-3 font-mono font-semibold">Rs {Number(inv.outstanding_amount).toFixed(2)}</td>
                    <td className="px-4 py-3">
                      <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-medium">
                        {inv.payment_status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
