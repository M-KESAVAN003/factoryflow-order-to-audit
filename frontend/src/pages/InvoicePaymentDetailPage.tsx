import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { api, ApiError } from "../lib/api";
import { InvoicePaymentsDetail } from "../types/costingPayment";
import { StatusNotice } from "../components/MasterDataControls";

export function InvoicePaymentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [detail, setDetail] = useState<InvoicePaymentsDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    const load = async () => {
      setLoading(true);
      try {
        setDetail(await api.invoicePayments(id));
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Failed to load invoice payments.");
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, [id]);

  if (loading) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-xs text-slate-500">
        Loading invoice payment allocations...
      </div>
    );
  }
  if (!detail) return <StatusNotice error={error ?? "Unavailable."} />;

  const { invoice, allocations } = detail;

  return (
    <div className="mx-auto max-w-4xl space-y-5">
      <div className="flex items-center gap-3">
        <Link
          to={`/invoices/${invoice.invoice_id}`}
          className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700"
        >
          <ArrowLeft className="h-3.5 w-3.5" /> Invoice
        </Link>
        <div>
          <h2 className="font-mono text-lg font-semibold text-slate-900">
            Payment Details — {invoice.invoice_number}
          </h2>
          <p className="text-xs text-slate-500">
            {invoice.customer_name} • Due {invoice.due_date} ({invoice.payment_status})
          </p>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="text-xs text-slate-500">Invoice Total</div>
          <div className="mt-1 font-mono text-xl font-semibold">Rs {Number(invoice.invoice_amount).toFixed(2)}</div>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="text-xs text-slate-500">Paid Amount</div>
          <div className="mt-1 font-mono text-xl font-semibold text-emerald-700">
            Rs {Number(invoice.paid_amount).toFixed(2)}
          </div>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="text-xs text-slate-500">Outstanding</div>
          <div className="mt-1 font-mono text-xl font-semibold text-amber-700">
            Rs {Number(invoice.outstanding_amount).toFixed(2)}
          </div>
        </div>
      </div>

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-200 px-5 py-3 text-sm font-semibold text-slate-900">
          Posted Payment Allocations
        </div>
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-50 text-[11px] uppercase tracking-wider text-slate-500">
            <tr>
              <th className="px-4 py-3 font-medium">Payment Ref</th>
              <th className="px-4 py-3 font-medium">Allocation Date</th>
              <th className="px-4 py-3 font-medium">Allocated By</th>
              <th className="px-4 py-3 font-medium">Amount</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {allocations.map((a) => (
              <tr key={a.id}>
                <td className="px-4 py-3 font-mono font-semibold">{a.payment_reference}</td>
                <td className="px-4 py-3">{a.allocation_date}</td>
                <td className="px-4 py-3">{a.allocated_by_email}</td>
                <td className="px-4 py-3 font-mono font-semibold text-emerald-700">
                  Rs {Number(a.allocated_amount).toFixed(2)}
                </td>
              </tr>
            ))}
            {allocations.length === 0 && (
              <tr>
                <td colSpan={4} className="px-4 py-8 text-center text-slate-400">
                  No payment allocations recorded against this invoice yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
