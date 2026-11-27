import { useEffect, useState } from "react";
import { api, ApiError } from "../lib/api";
import { ReceivablesAgeingReport } from "../types/costingPayment";
import { StatusNotice } from "../components/MasterDataControls";

export function ReceivablesAgeingPage() {
  const [asOfDate, setAsOfDate] = useState(new Date().toISOString().slice(0, 10));
  const [report, setReport] = useState<ReceivablesAgeingReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        setReport(await api.receivablesAgeing({ as_of_date: asOfDate }));
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Failed to load ageing report.");
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, [asOfDate]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Receivables Ageing Report</h2>
          <p className="text-xs text-slate-500">
            Due date calculated from configurable {report?.default_payment_term_days ?? 30}-day credit term.
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs">
          <span className="text-slate-600">As of Date:</span>
          <input
            type="date"
            value={asOfDate}
            onChange={(e) => setAsOfDate(e.target.value)}
            className="rounded-lg border border-slate-300 px-3 py-1.5"
          />
        </div>
      </div>

      <StatusNotice error={error} />

      {report && (
        <div className="grid gap-3 sm:grid-cols-5">
          {report.buckets.map((b) => (
            <div key={b.category} className="rounded-xl border border-slate-200 bg-white p-3.5 shadow-sm">
              <div className="text-[11px] font-medium text-slate-500">{b.category}</div>
              <div className="mt-1 font-mono text-lg font-semibold text-slate-900">
                Rs {Number(b.outstanding_amount).toFixed(2)}
              </div>
              <div className="text-[11px] text-slate-400">{b.invoices_count} invoices</div>
            </div>
          ))}
        </div>
      )}

      {loading ? (
        <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-xs text-slate-500">
          Calculating ageing buckets...
        </div>
      ) : (
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-[11px] uppercase tracking-wider text-slate-500">
              <tr>
                <th className="px-3 py-3 font-medium">Customer</th>
                <th className="px-3 py-3 font-medium">Invoice #</th>
                <th className="px-3 py-3 font-medium">Invoice Date</th>
                <th className="px-3 py-3 font-medium">Due Date</th>
                <th className="px-3 py-3 font-medium">Amount</th>
                <th className="px-3 py-3 font-medium">Paid</th>
                <th className="px-3 py-3 font-medium">Outstanding</th>
                <th className="px-3 py-3 font-medium">Days Overdue</th>
                <th className="px-3 py-3 font-medium">Category</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {report?.rows.map((r) => (
                <tr key={r.invoice_id}>
                  <td className="px-3 py-3 font-medium">{r.customer_name}</td>
                  <td className="px-3 py-3 font-mono font-semibold">{r.invoice_number}</td>
                  <td className="px-3 py-3">{r.invoice_date}</td>
                  <td className="px-3 py-3">{r.due_date}</td>
                  <td className="px-3 py-3 font-mono">Rs {Number(r.invoice_amount).toFixed(2)}</td>
                  <td className="px-3 py-3 font-mono text-emerald-700">Rs {Number(r.paid_amount).toFixed(2)}</td>
                  <td className="px-3 py-3 font-mono font-semibold">Rs {Number(r.outstanding_amount).toFixed(2)}</td>
                  <td className="px-3 py-3 font-mono">{r.days_overdue}</td>
                  <td className="px-3 py-3">{r.ageing_category}</td>
                </tr>
              ))}
              {(!report || report.rows.length === 0) && (
                <tr>
                  <td colSpan={9} className="px-4 py-8 text-center text-slate-400">
                    No open overdue invoices as of {asOfDate}.
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
