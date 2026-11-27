import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { api, ApiError } from "../lib/api";
import { hasPermission } from "../lib/permissions";
import { CustomerPayment, InvoicePaymentStatusRow } from "../types/costingPayment";
import { StatusNotice } from "../components/MasterDataControls";

export function PaymentHistoryPage() {
  const { user } = useAuth();
  const canManage = hasPermission(user, "payments:manage");
  const [payments, setPayments] = useState<CustomerPayment[]>([]);
  const [search, setSearch] = useState("");
  const [allocTarget, setAllocTarget] = useState<CustomerPayment | null>(null);
  const [openInvoices, setOpenInvoices] = useState<InvoicePaymentStatusRow[]>([]);
  const [allocInputs, setAllocInputs] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      const res = await api.listPayments({ search: search || undefined, page_size: 50 });
      setPayments(res.items);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load payment history.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search]);

  const openAllocatePanel = async (payment: CustomerPayment) => {
    setAllocTarget(payment);
    setAllocInputs({});
    try {
      const rec = await api.receivablesReport({ customer_id: payment.customer_id });
      setOpenInvoices(rec.invoices.filter((i) => Number(i.outstanding_amount) > 0));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to fetch customer invoices.");
    }
  };

  const submitAlloc = async () => {
    if (!allocTarget) return;
    setError(null);
    setSuccess(null);
    try {
      const allocations = Object.entries(allocInputs)
        .filter(([, amt]) => Number(amt) > 0)
        .map(([invoice_id, amt]) => ({ invoice_id, amount: amt }));
      await api.allocatePayment(allocTarget.id, { allocations });
      setSuccess(`Allocated advance on ${allocTarget.payment_reference}.`);
      setAllocTarget(null);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Allocation failed.");
    }
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Customer Payment History</h2>
          <p className="text-xs text-slate-500">
            All recorded customer receipts, invoice allocations, and unallocated advances.
          </p>
        </div>
        <div className="flex gap-2">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search reference or customer..."
            className="rounded-lg border border-slate-300 px-3 py-2 text-xs"
          />
          {canManage && (
            <Link to="/payments/new" className="rounded-lg bg-slate-900 px-3 py-2 text-xs font-medium text-white">
              + Record Payment
            </Link>
          )}
        </div>
      </div>

      <StatusNotice error={error} success={success} />

      {allocTarget && (
        <div className="rounded-xl border border-sky-200 bg-sky-50/70 p-4 space-y-3 text-xs">
          <div className="font-semibold text-slate-900">
            Allocate Unallocated Advance from {allocTarget.payment_reference} (Available: Rs{" "}
            {Number(allocTarget.unallocated_advance).toFixed(2)})
          </div>
          {openInvoices.map((inv) => (
            <div key={inv.invoice_id} className="flex items-center justify-between rounded-lg bg-white p-2.5 border border-slate-200">
              <span>
                <strong className="font-mono">{inv.invoice_number}</strong> — Outstanding Rs{" "}
                {Number(inv.outstanding_amount).toFixed(2)}
              </span>
              <input
                type="number"
                step="0.01"
                min="0"
                value={allocInputs[inv.invoice_id] ?? ""}
                onChange={(e) => setAllocInputs({ ...allocInputs, [inv.invoice_id]: e.target.value })}
                placeholder="Amount"
                className="w-32 rounded border border-slate-300 px-2 py-1 font-mono"
              />
            </div>
          ))}
          <div className="flex gap-2">
            <button
              type="button"
              onClick={submitAlloc}
              className="rounded-lg bg-slate-900 px-3 py-1.5 font-medium text-white"
            >
              Confirm Allocation
            </button>
            <button
              type="button"
              onClick={() => setAllocTarget(null)}
              className="rounded-lg border border-slate-300 bg-white px-3 py-1.5"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {loading ? (
        <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-xs text-slate-500">
          Loading payments...
        </div>
      ) : (
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-[11px] uppercase tracking-wider text-slate-500">
              <tr>
                <th className="px-4 py-3 font-medium">Ref #</th>
                <th className="px-4 py-3 font-medium">Customer</th>
                <th className="px-4 py-3 font-medium">Method / Ref</th>
                <th className="px-4 py-3 font-medium">Date</th>
                <th className="px-4 py-3 font-medium">Received</th>
                <th className="px-4 py-3 font-medium">Allocated</th>
                <th className="px-4 py-3 font-medium">Advance</th>
                <th className="px-4 py-3 font-medium">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {payments.map((p) => (
                <tr key={p.id}>
                  <td className="px-4 py-3 font-mono font-semibold text-slate-900">{p.payment_reference}</td>
                  <td className="px-4 py-3">
                    <Link to={`/customers/${p.customer_id}/ledger`} className="text-sky-700 hover:underline">
                      {p.customer_name}
                    </Link>
                  </td>
                  <td className="px-4 py-3">
                    {p.payment_method} {p.transaction_reference ? `(${p.transaction_reference})` : ""}
                  </td>
                  <td className="px-4 py-3">{p.payment_date}</td>
                  <td className="px-4 py-3 font-mono font-semibold">Rs {Number(p.amount_received).toFixed(2)}</td>
                  <td className="px-4 py-3 font-mono text-emerald-700">Rs {Number(p.allocated_amount).toFixed(2)}</td>
                  <td className="px-4 py-3 font-mono text-amber-700">Rs {Number(p.unallocated_advance).toFixed(2)}</td>
                  <td className="px-4 py-3">
                    {canManage && Number(p.unallocated_advance) > 0 ? (
                      <button
                        type="button"
                        onClick={() => openAllocatePanel(p)}
                        className="font-medium text-sky-700 hover:underline"
                      >
                        Allocate
                      </button>
                    ) : (
                      <span className="text-slate-400">{p.allocations.map((a) => a.invoice_number).join(", ") || "—"}</span>
                    )}
                  </td>
                </tr>
              ))}
              {payments.length === 0 && (
                <tr>
                  <td colSpan={8} className="px-4 py-8 text-center text-slate-400">
                    No customer payments found.
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
