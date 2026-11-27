import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "../lib/api";
import { Invoice } from "../types/sales";
import { StatusNotice } from "../components/MasterDataControls";

export function InvoicesPage() {
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const res = await api.listInvoices({ search: search || undefined, page_size: 50 });
        setInvoices(res.items);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Failed to load invoices.");
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, [search]);

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">GST Invoice History</h2>
          <p className="text-xs text-slate-500">
            Sequential financial-year GST tax invoices with CGST/SGST and IGST breakdown.
          </p>
        </div>
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search invoice # or customer..."
          className="rounded-lg border border-slate-300 px-3 py-2 text-xs"
        />
      </div>

      <StatusNotice error={error} />

      {loading ? (
        <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-xs text-slate-500">
          Loading GST invoices...
        </div>
      ) : (
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-[11px] uppercase tracking-wider text-slate-500">
              <tr>
                <th className="px-4 py-3 font-medium">Invoice No.</th>
                <th className="px-4 py-3 font-medium">Date / FY</th>
                <th className="px-4 py-3 font-medium">Customer</th>
                <th className="px-4 py-3 font-medium">Supply</th>
                <th className="px-4 py-3 font-medium">Taxable</th>
                <th className="px-4 py-3 font-medium">Total GST</th>
                <th className="px-4 py-3 font-medium">Grand Total</th>
                <th className="px-4 py-3 font-medium">PDF / Detail</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {invoices.map((inv) => (
                <tr key={inv.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3 font-mono font-semibold text-slate-900">
                    {inv.invoice_number}
                  </td>
                  <td className="px-4 py-3">
                    {inv.invoice_date} <span className="text-slate-400">({inv.financial_year})</span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="font-medium text-slate-900">{inv.customer_name}</div>
                    <div className="font-mono text-[10px] text-slate-500">{inv.customer_gstin}</div>
                  </td>
                  <td className="px-4 py-3">{inv.place_of_supply}</td>
                  <td className="px-4 py-3 font-mono">Rs {Number(inv.subtotal).toFixed(2)}</td>
                  <td className="px-4 py-3 font-mono">Rs {Number(inv.tax_amount).toFixed(2)}</td>
                  <td className="px-4 py-3 font-mono font-semibold text-slate-900">
                    Rs {Number(inv.grand_total).toFixed(2)}
                  </td>
                  <td className="px-4 py-3 space-x-2">
                    <Link to={`/invoices/${inv.id}`} className="text-sky-700 hover:underline">
                      Details
                    </Link>
                    <Link to={`/invoices/${inv.id}/pdf`} className="font-medium text-emerald-700 hover:underline">
                      PDF
                    </Link>
                  </td>
                </tr>
              ))}
              {invoices.length === 0 && (
                <tr>
                  <td colSpan={8} className="px-4 py-8 text-center text-slate-400">
                    No GST invoices generated yet.
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
