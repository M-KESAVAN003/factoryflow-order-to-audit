import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { api, ApiError } from "../lib/api";
import { CustomerStatement } from "../types/costingPayment";
import { StatusNotice } from "../components/MasterDataControls";

export function CustomerStatementPage() {
  const { customerId } = useParams<{ customerId: string }>();
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [statement, setStatement] = useState<CustomerStatement | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!customerId) return;
    const load = async () => {
      setLoading(true);
      try {
        setStatement(
          await api.customerStatement(customerId, {
            from_date: fromDate || undefined,
            to_date: toDate || undefined,
          })
        );
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Failed to load statement.");
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, [customerId, fromDate, toDate]);

  if (loading) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-xs text-slate-500">
        Generating customer account statement...
      </div>
    );
  }
  if (!statement) return <StatusNotice error={error ?? "Statement unavailable."} />;

  return (
    <div className="mx-auto max-w-4xl space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Link
            to={`/customers/${statement.customer_id}/ledger`}
            className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700"
          >
            <ArrowLeft className="h-3.5 w-3.5" /> Ledger
          </Link>
          <div>
            <h2 className="text-lg font-semibold text-slate-900">
              Account Statement — {statement.customer_name}
            </h2>
            <p className="text-xs text-slate-500">
              {statement.billing_address} • GSTIN: {statement.customer_gstin}
            </p>
          </div>
        </div>
        <div className="flex gap-2 text-xs">
          <input
            type="date"
            value={fromDate}
            onChange={(e) => setFromDate(e.target.value)}
            className="rounded-lg border border-slate-300 px-2.5 py-1.5"
          />
          <input
            type="date"
            value={toDate}
            onChange={(e) => setToDate(e.target.value)}
            className="rounded-lg border border-slate-300 px-2.5 py-1.5"
          />
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm text-xs">
        <div>
          <div className="text-slate-500">Opening Balance</div>
          <div className="font-mono text-base font-semibold">Rs {Number(statement.opening_balance).toFixed(2)}</div>
        </div>
        <div>
          <div className="text-slate-500">Period Debits</div>
          <div className="font-mono text-base font-semibold">Rs {Number(statement.period_debits).toFixed(2)}</div>
        </div>
        <div>
          <div className="text-slate-500">Period Credits</div>
          <div className="font-mono text-base font-semibold text-emerald-700">
            Rs {Number(statement.period_credits).toFixed(2)}
          </div>
        </div>
        <div>
          <div className="text-slate-500">Closing Receivable</div>
          <div className="font-mono text-base font-semibold text-amber-700">
            Rs {Number(statement.closing_balance).toFixed(2)}
          </div>
        </div>
      </div>

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-50 text-[11px] uppercase tracking-wider text-slate-500">
            <tr>
              <th className="px-4 py-3 font-medium">Date</th>
              <th className="px-4 py-3 font-medium">Reference</th>
              <th className="px-4 py-3 font-medium">Details</th>
              <th className="px-4 py-3 font-medium">Debit</th>
              <th className="px-4 py-3 font-medium">Credit</th>
              <th className="px-4 py-3 font-medium">Balance</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {statement.entries.map((e, i) => (
              <tr key={`${e.reference_number}-${i}`}>
                <td className="px-4 py-3">{e.entry_date}</td>
                <td className="px-4 py-3 font-mono font-semibold">{e.reference_number}</td>
                <td className="px-4 py-3">{e.description}</td>
                <td className="px-4 py-3 font-mono">Rs {Number(e.debit_amount).toFixed(2)}</td>
                <td className="px-4 py-3 font-mono text-emerald-700">Rs {Number(e.credit_amount).toFixed(2)}</td>
                <td className="px-4 py-3 font-mono font-semibold">Rs {Number(e.running_balance).toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
