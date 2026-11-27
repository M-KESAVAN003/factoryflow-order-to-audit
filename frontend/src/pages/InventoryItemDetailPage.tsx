import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, CheckCircle2, AlertTriangle } from "lucide-react";
import { api, ApiError } from "../lib/api";
import { InventoryItemDetail } from "../types/inventoryPurchase";
import { StatusNotice } from "../components/MasterDataControls";

export function InventoryItemDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [detail, setDetail] = useState<InventoryItemDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    const load = async () => {
      setLoading(true);
      try {
        setDetail(await api.inventoryItemDetail(id));
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Failed to load item detail.");
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, [id]);

  if (loading) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-xs text-slate-500">
        Loading item inventory & ledger...
      </div>
    );
  }

  if (error || !detail) {
    return <StatusNotice error={error ?? "Item not found."} />;
  }

  const { item } = detail;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Link
            to="/inventory"
            className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
          >
            <ArrowLeft className="h-3.5 w-3.5" /> Back
          </Link>
          <div>
            <h2 className="text-lg font-semibold text-slate-900">{item.name}</h2>
            <p className="font-mono text-xs text-slate-500">
              {item.sku} &bull; {item.category_label}
            </p>
          </div>
        </div>

        <span
          className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium ${
            detail.reconciled
              ? "border-emerald-200 bg-emerald-50 text-emerald-700"
              : "border-rose-200 bg-rose-50 text-rose-700"
          }`}
        >
          {detail.reconciled ? (
            <CheckCircle2 className="h-3.5 w-3.5" />
          ) : (
            <AlertTriangle className="h-3.5 w-3.5" />
          )}
          {detail.reconciled
            ? "Reconciled with Stock Ledger"
            : "Ledger Discrepancy"}
        </span>
      </div>

      <div className="grid gap-4 sm:grid-cols-4">
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <p className="text-xs text-slate-500">Available Quantity</p>
          <p className="mt-1 text-xl font-semibold text-slate-900 tabular-nums">
            {Number(item.available_quantity)} {item.base_unit_symbol}
          </p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <p className="text-xs text-slate-500">Weighted Avg Cost</p>
          <p className="mt-1 text-xl font-semibold text-slate-900 tabular-nums">
            ₹{Number(item.average_cost).toFixed(3)} / {item.base_unit_symbol}
          </p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <p className="text-xs text-slate-500">Total Stock Value</p>
          <p className="mt-1 text-xl font-semibold text-slate-900 tabular-nums">
            ₹{Number(item.stock_value).toLocaleString()}
          </p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <p className="text-xs text-slate-500">Ledger Net Sum</p>
          <p className="mt-1 text-xl font-semibold text-slate-900 tabular-nums">
            {Number(detail.ledger_sum_quantity)} {item.base_unit_symbol}
          </p>
        </div>
      </div>

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-200 px-5 py-4">
          <h3 className="text-sm font-semibold text-slate-900">
            Item Stock Ledger History
          </h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-[11px] uppercase tracking-wider text-slate-500">
              <tr>
                <th className="px-4 py-3 font-medium">Timestamp</th>
                <th className="px-4 py-3 font-medium">Movement Type</th>
                <th className="px-4 py-3 font-medium">In</th>
                <th className="px-4 py-3 font-medium">Out</th>
                <th className="px-4 py-3 font-medium">Unit Cost</th>
                <th className="px-4 py-3 font-medium">Reference</th>
                <th className="px-4 py-3 font-medium">Closing Qty / Avg</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {detail.recent_movements.map((m) => (
                <tr key={m.id}>
                  <td className="px-4 py-3 font-mono text-[11px] text-slate-500">
                    {new Date(m.transaction_date).toLocaleString()}
                  </td>
                  <td className="px-4 py-3 font-mono text-slate-800">{m.movement_type}</td>
                  <td className="px-4 py-3 font-mono text-emerald-700">
                    {Number(m.quantity_in) > 0 ? `+${Number(m.quantity_in)}` : "—"}
                  </td>
                  <td className="px-4 py-3 font-mono text-rose-700">
                    {Number(m.quantity_out) > 0 ? `-${Number(m.quantity_out)}` : "—"}
                  </td>
                  <td className="px-4 py-3 font-mono">₹{Number(m.unit_cost).toFixed(3)}</td>
                  <td className="px-4 py-3 font-mono text-slate-600">
                    {m.reference_doc_type}: {m.reference_doc_id}
                  </td>
                  <td className="px-4 py-3 font-mono text-slate-900">
                    {Number(m.balance_qty_after)} {m.base_unit_symbol} @ ₹
                    {Number(m.avg_cost_after).toFixed(3)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
