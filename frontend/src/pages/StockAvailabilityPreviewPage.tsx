import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { api, ApiError } from "../lib/api";
import { SalesOrderStockCheck } from "../types/sales";
import { StatusNotice } from "../components/MasterDataControls";

export function StockAvailabilityPreviewPage() {
  const { id } = useParams<{ id: string }>();
  const [check, setCheck] = useState<SalesOrderStockCheck | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    const load = async () => {
      setLoading(true);
      try {
        setCheck(await api.checkSalesOrderStock(id));
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Failed to load stock availability.");
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, [id]);

  if (loading) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-xs text-slate-500">
        Checking finished-goods stock balance...
      </div>
    );
  }
  if (!check) return <StatusNotice error={error ?? "Stock check unavailable."} />;

  return (
    <div className="mx-auto max-w-4xl space-y-5">
      <div className="flex items-center gap-3">
        <Link
          to={`/sales/orders/${check.sales_order_id}`}
          className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700"
        >
          <ArrowLeft className="h-3.5 w-3.5" /> Back
        </Link>
        <div>
          <h2 className="text-lg font-semibold text-slate-900">
            Stock Availability Preview — {check.order_number}
          </h2>
          <p className="text-xs text-slate-500">
            Recommended Action: <strong>{check.recommended_action}</strong> ({check.tax_type})
          </p>
        </div>
      </div>

      <StatusNotice error={error} />

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-50 text-[11px] uppercase tracking-wider text-slate-500">
            <tr>
              <th className="px-4 py-3 font-medium">Product</th>
              <th className="px-4 py-3 font-medium">Requested</th>
              <th className="px-4 py-3 font-medium">Physical Balance</th>
              <th className="px-4 py-3 font-medium">Committed</th>
              <th className="px-4 py-3 font-medium">Net Available</th>
              <th className="px-4 py-3 font-medium">Shortage</th>
              <th className="px-4 py-3 font-medium">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {check.lines.map((l) => (
              <tr key={l.product_id}>
                <td className="px-4 py-3 font-medium text-slate-900">{l.product_name}</td>
                <td className="px-4 py-3 font-mono">{Number(l.requested_quantity)} {l.unit_symbol}</td>
                <td className="px-4 py-3 font-mono">{Number(l.available_stock)}</td>
                <td className="px-4 py-3 font-mono">{Number(l.committed_stock)}</td>
                <td className="px-4 py-3 font-mono font-semibold">{Number(l.net_available_stock)}</td>
                <td className="px-4 py-3 font-mono font-semibold text-rose-700">
                  {Number(l.shortage_quantity)}
                </td>
                <td className="px-4 py-3">
                  <span
                    className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${
                      l.sufficient ? "bg-emerald-50 text-emerald-700" : "bg-rose-50 text-rose-700"
                    }`}
                  >
                    {l.sufficient ? "SUFFICIENT" : "SHORTAGE"}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-5 text-xs shadow-sm space-y-1">
        <div className="font-semibold text-slate-900">GST Tax Preview ({check.tax_type})</div>
        <div>Subtotal: Rs {Number(check.subtotal_preview).toFixed(2)}</div>
        <div>
          CGST: Rs {Number(check.cgst_preview).toFixed(2)} | SGST: Rs{" "}
          {Number(check.sgst_preview).toFixed(2)} | IGST: Rs{" "}
          {Number(check.igst_preview).toFixed(2)}
        </div>
        <div className="font-semibold text-slate-900">
          Estimated Total: Rs {Number(check.total_preview).toFixed(2)}
        </div>
      </div>
    </div>
  );
}
