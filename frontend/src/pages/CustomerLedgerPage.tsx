import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { api, ApiError } from "../lib/api";
import { CustomerLedger } from "../types/costingPayment";
import { StatusNotice } from "../components/MasterDataControls";

export function CustomerLedgerPage() {
  const { customerId } = useParams<{ customerId: string }>();
  const [ledger, setLedger] = useState<CustomerLedger | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!customerId) return;
    const load = async () => {
      setLoading(true);
      try {
        setLedger(await api.customerLedger(customerId));
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Failed to load customer ledger.");
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, [customerId]);

  if (loading) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-xs text-slate-500">
        Loading customer ledger...
      </div>
    );
  }
  if (!ledger) return <StatusNotice error={error ?? "Ledger unavailable."} />;

  return (
    <div className="mx-auto max-w-5xl space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Link
            to="/receivables"
            className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700"
          >
            <ArrowLeft className="h-3.5 w-3.5" /> Receivables
          </Link>
          <div>
            <h2 className="text-lg font-semibold text-slate-900">
              Customer Payment Ledger — {ledger.customer_name}
            </h2>
            <p className="font-mono text-xs text-slate-500">
              GSTIN: {ledger.customer_gstin} ({ledger.customer_state})
            </p>
          </div>
        </div>
        <Link
          to={`/customers/${ledger.customer_id}/statement`}
          className="rounded-lg bg-slate-900 px-3 py-2 text-xs font-medium text-white"
        >
          View Statement
        </Link>
      </div>

      <div className="grid gap-4 sm:grid-cols-4">
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="text-xs text-slate-500">Total Invoiced</div>
          <div className="mt-1 font-mono text-xl font-semibold">Rs {Number(ledger.total_invoiced).toFixed(2)}</div>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="text-xs text-slate-500">Total Paid</div>
          <div className="mt-1 font-mono text-xl font-semibold text-emerald-700">Rs {Number(ledger.total_paid).toFixed(2)}</div>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="text-xs text-slate-500">Unallocated Advance</div>
          <div className="mt-1 font-mono text-xl font-semibold text-sky-700">Rs {Number(ledger.unallocated_advance).toFixed(2)}</div>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="text-xs text-slate-500">Closing Outstanding</div>
          <div className="mt-1 font-mono text-xl font-semibold text-amber-700">
            Rs {Number(ledger.closing_outstanding).toFixed(2)}
          </div>
        </div>
      </div>

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-50 text-[11px] uppercase tracking-wider text-slate-500">
            <tr>
              <th className="px-4 py-3 font-medium">Date</th>
              <th className="px-4 py-3 font-medium">Type</th>
              <th className="px-4 py-3 font-medium">Reference</th>
              <th className="px-4 py-3 font-medium">Description</th>
              <th className="px-4 py-3 font-medium">Debit (+)</th>
              <th className="px-4 py-3 font-medium">Credit (-)</th>
              <th className="px-4 py-3 font-medium">Running Balance</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {ledger.entries.map((e, idx) => (
              <tr key={`${e.reference_number}-${idx}`}>
                <td className="px-4 py-3">{e.entry_date}</td>
                <td className="px-4 py-3">{e.doc_type}</td>
                <td className="px-4 py-3 font-mono font-semibold">{e.reference_number}</td>
                <td className="px-4 py-3">{e.description}</td>
                <td className="px-4 py-3 font-mono">{Number(e.debit_amount) > 0 ? `Rs ${Number(e.debit_amount).toFixed(2)}` : "—"}</td>
                <td className="px-4 py-3 font-mono text-emerald-700">{Number(e.credit_amount) > 0 ? `Rs ${Number(e.credit_amount).toFixed(2)}` : "—"}</td>
                <td className="px-4 py-3 font-mono font-semibold">Rs {Number(e.running_balance).toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
