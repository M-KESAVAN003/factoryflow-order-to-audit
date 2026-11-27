import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "../lib/api";
import { ProductionCostDashboard } from "../types/costingPayment";
import { StatusNotice } from "../components/MasterDataControls";

export function ProductionCostingDashboardPage() {
  const [data, setData] = useState<ProductionCostDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        setData(await api.productionCostDashboard());
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Failed to load costing dashboard.");
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, []);

  if (loading) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-xs text-slate-500">
        Computing production costs from stock ledger and posted overheads...
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Production Costing Dashboard</h2>
          <p className="text-xs text-slate-500">
            Actual weighted-average material & packaging cost plus posted labour/utility overheads (excluding GST).
          </p>
        </div>
        <Link
          to="/costing/expenses"
          className="rounded-lg bg-slate-900 px-3 py-2 text-xs font-medium text-white hover:bg-slate-800"
        >
          Manage Run Expenses
        </Link>
      </div>

      <StatusNotice error={error} />

      {data && (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
              <p className="text-xs text-slate-500">Total Production Cost</p>
              <p className="mt-1 font-mono text-2xl font-semibold text-slate-900">
                Rs {Number(data.total_production_cost).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
              </p>
              <p className="mt-0.5 text-[11px] text-slate-500">
                Across {data.total_runs_costed} runs ({Number(data.total_good_output)} good packets)
              </p>
            </div>
            <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
              <p className="text-xs text-slate-500">Materials & Packaging</p>
              <p className="mt-1 font-mono text-2xl font-semibold text-slate-900">
                Rs {(Number(data.total_raw_material_cost) + Number(data.total_packaging_cost)).toFixed(2)}
              </p>
              <p className="mt-0.5 text-[11px] text-slate-500">
                Raw Rs {Number(data.total_raw_material_cost).toFixed(2)} | Pkg Rs {Number(data.total_packaging_cost).toFixed(2)}
              </p>
            </div>
            <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
              <p className="text-xs text-slate-500">Avg Cost / Packet</p>
              <p className="mt-1 font-mono text-2xl font-semibold text-sky-700">
                Rs {Number(data.avg_cost_per_packet).toFixed(2)}
              </p>
            </div>
            <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
              <p className="text-xs text-slate-500">Avg Gross Margin %</p>
              <p className="mt-1 font-mono text-2xl font-semibold text-emerald-700">
                {Number(data.avg_gross_margin_pct).toFixed(2)}%
              </p>
            </div>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm space-y-3">
            <h3 className="text-sm font-semibold text-slate-900">Cost Breakdown Mix</h3>
            {[
              { label: "Raw Materials", val: Number(data.total_raw_material_cost), color: "bg-sky-600" },
              { label: "Packaging (incl. damaged)", val: Number(data.total_packaging_cost), color: "bg-indigo-600" },
              { label: "Direct Labour", val: Number(data.total_labour_cost), color: "bg-amber-600" },
              { label: "Gas & Power", val: Number(data.total_gas_and_power_cost), color: "bg-emerald-600" },
              { label: "Other Overhead", val: Number(data.total_other_overhead_cost), color: "bg-slate-600" },
            ].map((bar) => {
              const total = Number(data.total_production_cost) || 1;
              const pct = Math.min(100, Math.round((bar.val / total) * 100));
              return (
                <div key={bar.label} className="space-y-1 text-xs">
                  <div className="flex justify-between">
                    <span className="text-slate-700">{bar.label}</span>
                    <span className="font-mono font-medium">Rs {bar.val.toFixed(2)} ({pct}%)</span>
                  </div>
                  <div className="h-2 w-full rounded-full bg-slate-100">
                    <div className={`h-2 rounded-full ${bar.color}`} style={{ width: `${pct}%` }} />
                  </div>
                </div>
              );
            })}
          </div>

          <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
            <div className="border-b border-slate-200 px-5 py-3 text-sm font-semibold text-slate-900">
              Batch-wise & Run Costing Comparison
            </div>
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-[11px] uppercase tracking-wider text-slate-500">
                <tr>
                  <th className="px-3 py-3 font-medium">Run / Batch</th>
                  <th className="px-3 py-3 font-medium">Good Out</th>
                  <th className="px-3 py-3 font-medium">Raw Mat</th>
                  <th className="px-3 py-3 font-medium">Packaging</th>
                  <th className="px-3 py-3 font-medium">Labour</th>
                  <th className="px-3 py-3 font-medium">Gas/Power</th>
                  <th className="px-3 py-3 font-medium">Total Cost</th>
                  <th className="px-3 py-3 font-medium">Cost/Pkt</th>
                  <th className="px-3 py-3 font-medium">Sell (Pre-GST)</th>
                  <th className="px-3 py-3 font-medium">Profit/Pkt</th>
                  <th className="px-3 py-3 font-medium">Margin</th>
                  <th className="px-3 py-3 font-medium">Inspect</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data.runs.map((r) => (
                  <tr key={r.production_run_id} className="hover:bg-slate-50">
                    <td className="px-3 py-3">
                      <div className="font-mono font-semibold text-slate-900">{r.order_number}</div>
                      <div className="text-[11px] text-slate-500">{r.product_name} ({r.batch_number})</div>
                    </td>
                    <td className="px-3 py-3 font-mono">{Number(r.actual_good_output)}</td>
                    <td className="px-3 py-3 font-mono">Rs {Number(r.raw_material_cost).toFixed(2)}</td>
                    <td className="px-3 py-3 font-mono">Rs {Number(r.packaging_cost).toFixed(2)}</td>
                    <td className="px-3 py-3 font-mono">Rs {Number(r.labour_cost).toFixed(2)}</td>
                    <td className="px-3 py-3 font-mono">Rs {Number(r.gas_and_power_cost).toFixed(2)}</td>
                    <td className="px-3 py-3 font-mono font-semibold">Rs {Number(r.total_production_cost).toFixed(2)}</td>
                    <td className="px-3 py-3 font-mono font-semibold text-sky-700">
                      Rs {Number(r.cost_per_packet_display).toFixed(2)}
                    </td>
                    <td className="px-3 py-3 font-mono">Rs {Number(r.selling_price_before_gst).toFixed(2)}</td>
                    <td className="px-3 py-3 font-mono text-emerald-700">
                      Rs {Number(r.gross_profit_per_packet).toFixed(2)}
                    </td>
                    <td className="px-3 py-3 font-mono font-semibold text-emerald-700">
                      {Number(r.gross_margin_pct).toFixed(2)}%
                    </td>
                    <td className="px-3 py-3">
                      <Link
                        to={`/costing/runs/${r.production_run_id}`}
                        className="font-medium text-sky-700 hover:underline"
                      >
                        Details
                      </Link>
                    </td>
                  </tr>
                ))}
                {data.runs.length === 0 && (
                  <tr>
                    <td colSpan={12} className="px-4 py-8 text-center text-slate-400">
                      No production runs available for costing yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
