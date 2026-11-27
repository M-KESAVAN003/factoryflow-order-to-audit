import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "../lib/api";
import { RunVarianceReport, VarianceSummary } from "../types/bomProduction";
import { StatusNotice } from "../components/MasterDataControls";

const BADGE: Record<"GREEN" | "ORANGE" | "RED", string> = {
  GREEN: "bg-emerald-50 text-emerald-700 border-emerald-200",
  ORANGE: "bg-amber-50 text-amber-800 border-amber-200",
  RED: "bg-rose-50 text-rose-700 border-rose-200",
};

export function ProductionVariancePage() {
  const [summary, setSummary] = useState<VarianceSummary | null>(null);
  const [selectedRun, setSelectedRun] = useState<RunVarianceReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const sum = await api.varianceSummary();
        setSummary(sum);
        if (sum.runs[0]) {
          setSelectedRun(await api.getProductionRunVariance(sum.runs[0].production_run_id));
        }
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Failed to load variance report.");
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, []);

  const inspectRun = async (runId: string) => {
    try {
      setSelectedRun(await api.getProductionRunVariance(runId));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load run variance.");
    }
  };

  if (loading) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-xs text-slate-500">
        Computing planned vs actual variances...
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-slate-900">Production Variance Report</h2>
        <p className="text-xs text-slate-500">
          Consumption and yield variances flagged against the configured 3% tolerance threshold.
        </p>
      </div>

      <StatusNotice error={error} />

      {summary && (
        <div className="grid gap-4 sm:grid-cols-3">
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-xs text-slate-500">Completed / Posted Runs</p>
            <p className="mt-1 text-2xl font-semibold text-slate-900">{summary.total_runs}</p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-xs text-slate-500">Flagged Beyond Tolerance</p>
            <p className="mt-1 text-2xl font-semibold text-rose-700">{summary.flagged_runs}</p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-xs text-slate-500">Average Yield Variance</p>
            <p className="mt-1 font-mono text-2xl font-semibold text-slate-900">
              {Number(summary.avg_yield_variance_pct).toFixed(2)}%
            </p>
          </div>
        </div>
      )}

      {summary && summary.runs.length > 0 && (
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
          <div className="border-b border-slate-200 px-5 py-3 text-sm font-semibold text-slate-900">
            Run Variance Summary
          </div>
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-[11px] uppercase tracking-wider text-slate-500">
              <tr>
                <th className="px-4 py-3 font-medium">Order</th>
                <th className="px-4 py-3 font-medium">Product</th>
                <th className="px-4 py-3 font-medium">Expected / Good</th>
                <th className="px-4 py-3 font-medium">Yield Variance</th>
                <th className="px-4 py-3 font-medium">Flagged Materials</th>
                <th className="px-4 py-3 font-medium">Inspect</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {summary.runs.map((r) => (
                <tr key={r.production_run_id} className="hover:bg-slate-50/70">
                  <td className="px-4 py-3 font-mono font-medium">
                    <Link
                      to={`/production/runs/${r.production_run_id}`}
                      className="text-sky-700 hover:underline"
                    >
                      {r.order_number}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-slate-700">{r.product_name}</td>
                  <td className="px-4 py-3 font-mono">
                    {Number(r.expected_output)} / {Number(r.actual_good_output)}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex rounded border px-2 py-0.5 font-mono text-[11px] font-medium ${
                        BADGE[r.yield_status]
                      }`}
                    >
                      {Number(r.yield_variance_pct).toFixed(2)}% ({r.yield_status})
                    </span>
                  </td>
                  <td className="px-4 py-3 font-mono">{r.flagged_material_count}</td>
                  <td className="px-4 py-3">
                    <button
                      type="button"
                      onClick={() => void inspectRun(r.production_run_id)}
                      className="rounded border border-slate-200 px-2.5 py-1 text-[11px] font-medium text-slate-700 hover:bg-slate-50"
                    >
                      Breakdown
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {selectedRun && (
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 px-5 py-4">
            <div>
              <h3 className="text-sm font-semibold text-slate-900">
                Material Variance Breakdown — {selectedRun.order_number}
              </h3>
              <p className="text-xs text-slate-500">
                Tolerance: ±{Number(selectedRun.tolerance_pct)}% &bull; Yield:{" "}
                {Number(selectedRun.yield_variance_pct).toFixed(2)}% ({selectedRun.yield_status})
              </p>
            </div>
            {selectedRun.packaging_warning && (
              <span className="rounded bg-amber-50 px-2.5 py-1 text-[11px] font-medium text-amber-900 ring-1 ring-amber-200">
                {selectedRun.packaging_warning}
              </span>
            )}
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-[11px] uppercase tracking-wider text-slate-500">
                <tr>
                  <th className="px-4 py-3 font-medium">Material</th>
                  <th className="px-4 py-3 font-medium">Planned</th>
                  <th className="px-4 py-3 font-medium">Actual</th>
                  <th className="px-4 py-3 font-medium">Difference</th>
                  <th className="px-4 py-3 font-medium">Variance %</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {selectedRun.materials.map((m) => (
                  <tr key={m.stock_item_id}>
                    <td className="px-4 py-3 font-medium text-slate-900">
                      {m.material_name} ({m.unit_symbol})
                    </td>
                    <td className="px-4 py-3 font-mono">{Number(m.planned_consumption)}</td>
                    <td className="px-4 py-3 font-mono">{Number(m.actual_consumption)}</td>
                    <td className="px-4 py-3 font-mono">
                      {Number(m.difference) > 0 ? `+${Number(m.difference)}` : Number(m.difference)}
                    </td>
                    <td className="px-4 py-3 font-mono">
                      {Number(m.variance_pct) > 0
                        ? `+${Number(m.variance_pct).toFixed(2)}%`
                        : `${Number(m.variance_pct).toFixed(2)}%`}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex rounded border px-2 py-0.5 text-[11px] font-medium ${
                          BADGE[m.status]
                        }`}
                      >
                        {m.status}
                        {m.exceeds_tolerance ? " (ALERT)" : ""}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
