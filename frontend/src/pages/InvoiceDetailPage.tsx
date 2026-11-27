import React, { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, Download, Eye } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { api, ApiError } from "../lib/api";
import { hasPermission } from "../lib/permissions";
import { Invoice } from "../types/sales";
import { StatusNotice } from "../components/MasterDataControls";

export function InvoiceDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const canManage = hasPermission(user, "invoices:manage");
  const [invoice, setInvoice] = useState<Invoice | null>(null);
  const [cnReason, setCnReason] = useState("");
  const [cnAmount, setCnAmount] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const load = async () => {
    if (!id) return;
    setLoading(true);
    try {
      setInvoice(await api.getInvoice(id));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load invoice.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const handleDownload = async () => {
    if (!invoice) return;
    try {
      const blob = await api.downloadInvoicePdf(invoice.id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${invoice.invoice_number.replace(/\//g, "-")}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to download PDF.");
    }
  };

  const handleCreditNote = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!invoice) return;
    setError(null);
    setSuccess(null);
    try {
      const cn = await api.issueCreditNote(invoice.id, {
        reason: cnReason,
        amount: cnAmount || undefined,
      });
      setSuccess(`Issued Credit Note ${cn.credit_note_number}.`);
      setCnReason("");
      setCnAmount("");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to issue credit note.");
    }
  };

  if (loading) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-xs text-slate-500">
        Loading GST invoice...
      </div>
    );
  }
  if (!invoice) return <StatusNotice error={error ?? "Invoice not found."} />;

  return (
    <div className="mx-auto max-w-4xl space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Link
            to="/invoices"
            className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700"
          >
            <ArrowLeft className="h-3.5 w-3.5" /> Invoices
          </Link>
          <div>
            <h2 className="font-mono text-lg font-semibold text-slate-900">
              {invoice.invoice_number}
            </h2>
            <p className="text-xs text-slate-500">
              Order {invoice.order_number} • FY {invoice.financial_year}
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <Link
            to={`/invoices/${invoice.id}/pdf`}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-medium text-slate-700"
          >
            <Eye className="h-3.5 w-3.5" /> PDF View
          </Link>
          <button
            type="button"
            onClick={handleDownload}
            className="inline-flex items-center gap-1.5 rounded-lg bg-slate-900 px-3 py-2 text-xs font-medium text-white"
          >
            <Download className="h-3.5 w-3.5" /> Download PDF
          </button>
        </div>
      </div>

      <StatusNotice error={error} success={success} />

      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm space-y-4 text-xs">
        <div className="grid gap-4 border-b border-slate-200 pb-4 sm:grid-cols-2">
          <div>
            <div className="text-[11px] uppercase tracking-wider text-slate-400">Seller</div>
            <div className="font-semibold text-slate-900">{invoice.factory_name}</div>
            <div className="text-slate-600">{invoice.factory_address}</div>
            <div className="font-mono text-slate-700">GSTIN: {invoice.factory_gstin}</div>
          </div>
          <div>
            <div className="text-[11px] uppercase tracking-wider text-slate-400">Buyer</div>
            <div className="font-semibold text-slate-900">{invoice.customer_name}</div>
            <div className="text-slate-600">{invoice.billing_address}</div>
            <div className="font-mono text-slate-700">GSTIN: {invoice.customer_gstin}</div>
            <div>Place of Supply: {invoice.place_of_supply}</div>
          </div>
        </div>

        <table className="w-full text-left text-xs">
          <thead className="bg-slate-50 text-[11px] uppercase tracking-wider text-slate-500">
            <tr>
              <th className="px-3 py-2">Description / Pack</th>
              <th className="px-3 py-2">HSN</th>
              <th className="px-3 py-2">Qty</th>
              <th className="px-3 py-2">Rate</th>
              <th className="px-3 py-2">Taxable</th>
              <th className="px-3 py-2">CGST</th>
              <th className="px-3 py-2">SGST</th>
              <th className="px-3 py-2">IGST</th>
              <th className="px-3 py-2">Total</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {invoice.items.map((it) => (
              <tr key={it.id}>
                <td className="px-3 py-2 font-medium">{it.product_name} ({it.pack_size})</td>
                <td className="px-3 py-2 font-mono">{it.hsn_code}</td>
                <td className="px-3 py-2 font-mono">{Number(it.quantity)} {it.unit_symbol}</td>
                <td className="px-3 py-2 font-mono">Rs {Number(it.unit_price).toFixed(2)}</td>
                <td className="px-3 py-2 font-mono">Rs {Number(it.taxable_value).toFixed(2)}</td>
                <td className="px-3 py-2 font-mono">Rs {Number(it.cgst_amount).toFixed(2)}</td>
                <td className="px-3 py-2 font-mono">Rs {Number(it.sgst_amount).toFixed(2)}</td>
                <td className="px-3 py-2 font-mono">Rs {Number(it.igst_amount).toFixed(2)}</td>
                <td className="px-3 py-2 font-mono font-semibold">Rs {Number(it.line_total).toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>

        <div className="flex flex-wrap justify-between gap-4 border-t border-slate-200 pt-4">
          <div className="text-slate-600">
            <strong>Amount in Words:</strong> {invoice.amount_in_words}
          </div>
          <div className="text-right font-mono space-y-1">
            <div>Taxable Value: Rs {Number(invoice.subtotal).toFixed(2)}</div>
            <div>Total Tax: Rs {Number(invoice.tax_amount).toFixed(2)}</div>
            <div className="text-sm font-semibold text-slate-900">
              Grand Total: Rs {Number(invoice.grand_total).toFixed(2)}
            </div>
          </div>
        </div>
      </div>

      {canManage && (
        <form
          onSubmit={handleCreditNote}
          className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm space-y-3"
        >
          <div className="text-sm font-semibold text-slate-900">
            Issue Traceable Credit Note (Reversal)
          </div>
          <div className="flex flex-wrap gap-2">
            <input
              type="text"
              required
              value={cnReason}
              onChange={(e) => setCnReason(e.target.value)}
              placeholder="Audit reason for credit note..."
              className="min-w-56 flex-1 rounded-lg border border-slate-300 px-3 py-2 text-xs"
            />
            <input
              type="number"
              step="0.01"
              value={cnAmount}
              onChange={(e) => setCnAmount(e.target.value)}
              placeholder="Amount (optional full)"
              className="w-40 rounded-lg border border-slate-300 px-3 py-2 font-mono text-xs"
            />
            <button
              type="submit"
              className="rounded-lg bg-slate-900 px-4 py-2 text-xs font-medium text-white"
            >
              Issue Credit Note
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
