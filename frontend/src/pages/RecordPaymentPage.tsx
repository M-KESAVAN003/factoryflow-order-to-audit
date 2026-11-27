import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { api, ApiError } from "../lib/api";
import { CustomerPaymentMethod, InvoicePaymentStatusRow } from "../types/costingPayment";
import { Customer } from "../types/masterData";
import { StatusNotice } from "../components/MasterDataControls";

export function RecordPaymentPage() {
  const navigate = useNavigate();
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [customerId, setCustomerId] = useState("");
  const [openInvoices, setOpenInvoices] = useState<InvoicePaymentStatusRow[]>([]);
  const [method, setMethod] = useState<CustomerPaymentMethod>("UPI");
  const [amount, setAmount] = useState("4000.00");
  const [paymentDate, setPaymentDate] = useState(new Date().toISOString().slice(0, 10));
  const [txRef, setTxRef] = useState("");
  const [notes, setNotes] = useState("");
  const [allocMap, setAllocMap] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const res = await api.listCustomers({ is_active: true, page_size: 100 });
        setCustomers(res.items);
        if (res.items[0]) {
          setCustomerId(res.items[0].id);
        }
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Failed to load customers.");
      }
    };
    void load();
  }, []);

  useEffect(() => {
    if (!customerId) return;
    const loadInv = async () => {
      try {
        const rec = await api.receivablesReport({ customer_id: customerId });
        setOpenInvoices(rec.invoices.filter((i) => Number(i.outstanding_amount) > 0));
        setAllocMap({});
      } catch {
        setOpenInvoices([]);
      }
    };
    void loadInv();
  }, [customerId]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!customerId) return;
    setSaving(true);
    setError(null);
    try {
      const allocations = Object.entries(allocMap)
        .filter(([, val]) => Number(val) > 0)
        .map(([invoice_id, val]) => ({ invoice_id, amount: val }));
      await api.createPayment({
        customer_id: customerId,
        payment_date: paymentDate,
        payment_method: method,
        amount_received: amount,
        transaction_reference: txRef.trim() || null,
        notes: notes.trim() || null,
        allocations,
      });
      navigate("/payments/history", { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to record customer payment.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <div className="flex items-center gap-3">
        <Link
          to="/payments"
          className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700"
        >
          <ArrowLeft className="h-3.5 w-3.5" /> Payments
        </Link>
        <h2 className="text-lg font-semibold text-slate-900">Record Customer Payment</h2>
      </div>

      <StatusNotice error={error} />

      <form
        onSubmit={handleSubmit}
        className="space-y-4 rounded-xl border border-slate-200 bg-white p-5 shadow-sm text-xs"
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="mb-1 block font-medium text-slate-700">Customer</label>
            <select
              value={customerId}
              onChange={(e) => setCustomerId(e.target.value)}
              required
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2"
            >
              {customers.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} ({c.state})
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block font-medium text-slate-700">Payment Method</label>
            <select
              value={method}
              onChange={(e) => setMethod(e.target.value as CustomerPaymentMethod)}
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2"
            >
              <option value="CASH">Cash</option>
              <option value="BANK_TRANSFER">Bank Transfer</option>
              <option value="UPI">UPI</option>
              <option value="CHEQUE">Cheque</option>
              <option value="OTHER">Other</option>
            </select>
          </div>
          <div>
            <label className="mb-1 block font-medium text-slate-700">Amount Received (INR)</label>
            <input
              type="number"
              step="0.01"
              min="0.01"
              required
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 font-mono"
            />
          </div>
          <div>
            <label className="mb-1 block font-medium text-slate-700">Payment Date</label>
            <input
              type="date"
              required
              value={paymentDate}
              onChange={(e) => setPaymentDate(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2"
            />
          </div>
          <div>
            <label className="mb-1 block font-medium text-slate-700">Transaction / UTR / Cheque Ref</label>
            <input
              type="text"
              value={txRef}
              onChange={(e) => setTxRef(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2"
            />
          </div>
          <div>
            <label className="mb-1 block font-medium text-slate-700">Notes</label>
            <input
              type="text"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2"
            />
          </div>
        </div>

        {openInvoices.length > 0 && (
          <div className="space-y-2 border-t border-slate-200 pt-4">
            <div className="font-semibold text-slate-900">
              Allocate to Open Invoices (leave 0 to record as unallocated advance)
            </div>
            {openInvoices.map((inv) => (
              <div key={inv.invoice_id} className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-200 p-2.5">
                <div>
                  <div className="font-mono font-semibold">{inv.invoice_number}</div>
                  <div className="text-[11px] text-slate-500">
                    Outstanding: Rs {Number(inv.outstanding_amount).toFixed(2)} (of Rs {Number(inv.invoice_amount).toFixed(2)})
                  </div>
                </div>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  max={Number(inv.outstanding_amount)}
                  value={allocMap[inv.invoice_id] ?? ""}
                  onChange={(e) => setAllocMap({ ...allocMap, [inv.invoice_id]: e.target.value })}
                  placeholder="Allocate INR"
                  className="w-36 rounded-lg border border-slate-300 px-2.5 py-1.5 font-mono"
                />
              </div>
            ))}
          </div>
        )}

        <button
          type="submit"
          disabled={saving}
          className="w-full rounded-lg bg-slate-900 px-4 py-2.5 font-medium text-white hover:bg-slate-800 disabled:opacity-50"
        >
          {saving ? "Posting Payment..." : "Record & Post Payment"}
        </button>
      </form>
    </div>
  );
}
