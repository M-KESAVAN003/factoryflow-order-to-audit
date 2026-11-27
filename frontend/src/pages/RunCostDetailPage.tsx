import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, PlusCircle } from "lucide-react";
import { api, ApiError } from "../lib/api";
import { RunCosting } from "../types/costingPayment";
import { StatusNotice } from "../components/MasterDataControls";

export function RunCostDetailPage() {
  const { runId } = useParams<{ runId: string }>();
  const [cost, setCost] = useState<RunCosting | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!runId) return;
    const load = async () => {
      setLoading(true);
      try {
        setCost(await api.runCosting(runId));
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Failed to load run costing.");
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, [runId]);

  if (loading) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-xs text-slate-500">
        Loading run costing breakdown...
      </div>
    );
  }
  if (!cost) return <StatusNotice error={error ?? "Cost sheet not found."} />;

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Link
            to="/costing"
            className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700"
          >
            <ArrowLeft className="h-3.5 w-3.5" /> Costing Dashboard
          </Link>
          <div>
            <h2 className="font-mono text-lg font-semibold text-slate-900">
              {cost.order_number} — Cost Sheet
            </h2>
            <p className="text-xs text-slate-500">
              {cost.product_name} (Batch {cost.batch_number}) • {Number(cost.actual_good_output)} good {cost.unit_symbol}
            </p>
          </div>
        </div>
        <Link
          to={`/costing/runs/${cost.production_run_id}/expenses/new`}
          className="inline-flex items-center gap-1.5 rounded-lg bg-slate-900 px-3 py-2 text-xs font-medium text-white"
        >
          <PlusCircle className="h-4 w-4" /> Add Expense
        </Link>
      </div>

      <div className="grid gap-4 sm:grid-cols-4">
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="text-xs text-slate-500">Material + Packaging</div>
          <div className="mt-1 font-mono text-xl font-semibold">
            Rs {Number(cost.material_and_packaging_cost).toFixed(2)}
          </div>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="text-xs text-slate-500">Overheads (Labour + Utility)</div>
          <div className="mt-1 font-mono text-xl font-semibold">
            Rs {Number(cost.total_overhead_cost).toFixed(2)}
          </div>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="text-xs text-slate-500">Total Cost / Cost per Pkt</div>
          <div className="mt-1 font-mono text-xl font-semibold text-sky-700">
            Rs {Number(cost.total_production_cost).toFixed(2)} / Rs {Number(cost.cost_per_packet_display).toFixed(2)}
          </div>
          <div className="font-mono text-[10px] text-slate-400">
            Exact: Rs {cost.cost_per_packet_exact}
          </div>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="text-xs text-slate-500">Gross Profit / Margin</div>
          <div className="mt-1 font-mono text-xl font-semibold text-emerald-700">
            Rs {Number(cost.gross_profit_per_packet).toFixed(2)} ({Number(cost.gross_margin_pct).toFixed(2)}%)
          </div>
        </div>
      </div>

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-200 px-5 py-3 text-sm font-semibold text-slate-900">
          Actual Material & Packaging Cost Breakdown
        </div>
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-50 text-[11px] uppercase tracking-wider text-slate-500">
            <tr>
              <th className="px-4 py-2.5">Material</th>
              <th className="px-4 py-2.5">Category</th>
              <th className="px-4 py-2.5">Actual + Damaged</th>
              <th className="px-4 py-2.5">Total Consumed</th>
              <th className="px-4 py-2.5">Weighted Avg Rate</th>
              <th className="px-4 py-2.5">Cost</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {cost.materials.map((m) => (
              <tr key={m.stock_item_id}>
                <td className="px-4 py-2.5 font-medium">{m.stock_item_name} ({m.sku})</td>
                <td className="px-4 py-2.5">{m.category}</td>
                <td className="px-4 py-2.5 font-mono">
                  {Number(m.actual_quantity)} + {Number(m.damaged_quantity)} {m.unit_symbol}
                </td>
                <td className="px-4 py-2.5 font-mono">{Number(m.total_consumed_qty)} {m.unit_symbol}</td>
                <td className="px-4 py-2.5 font-mono">Rs {Number(m.weighted_avg_rate).toFixed(3)}</td>
                <td className="px-4 py-2.5 font-mono font-semibold">Rs {Number(m.total_cost).toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
