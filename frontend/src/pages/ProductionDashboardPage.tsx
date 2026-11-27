import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  AlertTriangle,
  BarChart3,
  CheckCircle2,
  ClipboardList,
  Plus,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { api, ApiError } from "../lib/api";
import { hasPermission } from "../lib/permissions";
import { Bom, ProductionDashboard } from "../types/bomProduction";
import { InventoryItemRow } from "../types/inventoryPurchase";
import { StatusNotice } from "../components/MasterDataControls";

export function ProductionDashboardPage() {
  const { user } = useAuth();
  const canManage = hasPermission(user, "production_runs:manage");
  const canReadInv = hasPermission(user, "inventory:read");

  const [dash, setDash] = useState<ProductionDashboard | null>(null);
  const [boms, setBoms] = useState<Bom[]>([]);
  const [rawStock, setRawStock] = useState<InventoryItemRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const [d, b] = await Promise.all([
          api.productionDashboard(),
          api.listBoms({ is_active: true, page_size: 10 }),
        ]);
        setDash(d);
        setBoms(b.items);
        if (canReadInv) {
          const inv = await api.inventoryRawMaterials({ page_size: 10 });
          setRawStock(inv.items);
        }
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Failed to load production dashboard.");
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, [canReadInv]);

  if (loading) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-xs text-slate-500">
        Loading live production dashboard...
      </div>
    );
  }
  if (error || !dash) return <StatusNotice error={error ?? "Unable to load dashboard."} />;

  const latestRun = dash.recent_runs[0];
  const maxTrendVal = Math.max(
    1,
    ...dash.daily_trend.map((p) => Math.max(Number(p.planned_output), Number(p.actual_output)))
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Production Dashboard</h2>
          <p className="text-xs text-slate-500">
            Live shop-floor execution, planned vs actual yield, material variances, and stock readiness.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link
            to="/production/variance"
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50"
          >
            <BarChart3 className="h-3.5 w-3.5" /> Variance Report
          </Link>
          {canManage && (
            <Link
              to="/production/runs/new"
              className="inline-flex items-center gap-1.5 rounded-lg bg-slate-900 px-3.5 py-2 text-xs font-semibold text-white hover:bg-slate-800"
            >
              <Plus className="h-3.5 w-3.5" /> New Production Run
            </Link>
          )}
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7">
        {[
          { label: "Today's Runs", value: String(dash.todays_runs) },
          { label: "Planned Output", value: `${Number(dash.planned_output)} pkts` },
          { label: "Actual Output", value: `${Number(dash.actual_output)} pkts` },
          { label: "Total Wastage", value: String(Number(dash.total_wastage)) },
          { label: "Yield Variance", value: `${Number(dash.overall_yield_variance_pct).toFixed(2)}%` },
          { label: "Pending Runs", value: String(dash.pending_runs) },
          { label: "Active BOMs", value: String(dash.active_boms) },
        ].map((card) => (
          <div key={card.label} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-[11px] font-medium uppercase tracking-wider text-slate-500">
              {card.label}
            </p>
            <p className="mt-1.5 text-lg font-semibold text-slate-900 tabular-nums">
              {card.value}
            </p>
          </div>
        ))}
      </div>

      {/* Charts Grid */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Planned vs Actual & Daily Trend */}
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-slate-900">
            Planned vs Actual Output & Daily Trend
          </h3>
          {dash.daily_trend.length === 0 ? (
            <p className="mt-4 text-xs text-slate-500">No production runs recorded yet.</p>
          ) : (
            <div className="mt-4 space-y-3">
              {dash.daily_trend.map((pt) => {
                const pPct = Math.round((Number(pt.planned_output) / maxTrendVal) * 100);
                const aPct = Math.round((Number(pt.actual_output) / maxTrendVal) * 100);
                return (
                  <div key={pt.date} className="space-y-1 text-xs">
                    <div className="flex justify-between font-mono text-[11px] text-slate-600">
                      <span>{pt.date}</span>
                      <span>
                        Plan {Number(pt.planned_output)} / Act {Number(pt.actual_output)} (Waste{" "}
                        {Number(pt.wastage)})
                      </span>
                    </div>
                    <div className="space-y-1">
                      <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100">
                        <div className="h-full bg-slate-400" style={{ width: `${pPct}%` }} />
                      </div>
                      <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100">
                        <div className="h-full bg-sky-600" style={{ width: `${aPct}%` }} />
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Product-wise Yield & Latest Material Comparison */}
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-slate-900">
            Product-wise Yield & Material Consumption
          </h3>
          {dash.product_yield.length === 0 ? (
            <p className="mt-4 text-xs text-slate-500">No completed production runs yet.</p>
          ) : (
            <div className="mt-4 space-y-3">
              {dash.product_yield.map((py) => (
                <div
                  key={py.product_name}
                  className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs"
                >
                  <div className="flex justify-between font-medium text-slate-900">
                    <span>{py.product_name}</span>
                    <span className="font-mono">{Number(py.yield_pct).toFixed(2)}% yield</span>
                  </div>
                  <div className="mt-1 text-[11px] text-slate-500">
                    {py.runs_count} run(s) &bull; {Number(py.actual_output)} /{" "}
                    {Number(py.expected_output)} expected
                  </div>
                </div>
              ))}
            </div>
          )}

          {latestRun && latestRun.materials.length > 0 && (
            <div className="mt-4 border-t border-slate-100 pt-3">
              <p className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                Latest Run Material Variance ({latestRun.order_number})
              </p>
              <div className="space-y-1.5 text-xs">
                {latestRun.materials.map((m) => (
                  <div key={m.id} className="flex items-center justify-between">
                    <span className="text-slate-700">{m.stock_item_name}</span>
                    <span className="font-mono text-slate-600">
                      {Number(m.total_consumed_base_qty)} / {Number(m.planned_base_quantity)}{" "}
                      {m.base_unit_symbol}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Variance Alerts & BOM + Stock Panels */}
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-900">Variance Alerts</h3>
            <AlertTriangle className="h-4 w-4 text-rose-600" />
          </div>
          {dash.variance_alerts.length === 0 ? (
            <div className="flex items-center gap-2 text-xs text-emerald-700">
              <CheckCircle2 className="h-4 w-4" /> All runs within tolerance.
            </div>
          ) : (
            <div className="space-y-2">
              {dash.variance_alerts.map((al) => (
                <Link
                  key={al.production_run_id}
                  to={`/production/runs/${al.production_run_id}`}
                  className="block rounded-lg border border-rose-200 bg-rose-50/70 p-3 text-xs hover:bg-rose-50"
                >
                  <div className="flex justify-between font-mono font-semibold text-rose-800">
                    <span>{al.order_number}</span>
                    <span>{Number(al.yield_variance_pct).toFixed(2)}% yield</span>
                  </div>
                  <div className="mt-1 text-[11px] text-rose-700">
                    {al.product_name} &bull; {al.flagged_material_count} material alert(s)
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-900">Active BOM Overview</h3>
            <Link to="/boms" className="text-xs font-medium text-sky-700">
              View all →
            </Link>
          </div>
          <div className="space-y-2">
            {boms.map((b) => (
              <Link
                key={b.id}
                to={`/boms/${b.id}`}
                className="block rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs hover:bg-slate-100"
              >
                <div className="flex justify-between font-medium text-slate-900">
                  <span>{b.product_name}</span>
                  <span className="font-mono">v{b.version_number}</span>
                </div>
                <div className="mt-1 text-[11px] text-slate-500">
                  {Number(b.expected_output)} {b.output_unit_symbol}/batch &bull; {b.lines.length} inputs
                </div>
              </Link>
            ))}
          </div>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-900">Raw Material Availability</h3>
            {canReadInv && (
              <Link to="/inventory/raw-materials" className="text-xs font-medium text-sky-700">
                Inventory →
              </Link>
            )}
          </div>
          {rawStock.length === 0 ? (
            <p className="text-xs text-slate-500">Stock visibility restricted or empty.</p>
          ) : (
            <div className="space-y-2 text-xs">
              {rawStock.map((item) => (
                <div
                  key={item.stock_item_id}
                  className="flex items-center justify-between rounded-lg border border-slate-100 bg-slate-50 px-3 py-2"
                >
                  <span className="font-medium text-slate-800">{item.name}</span>
                  <span className="font-mono text-slate-900">
                    {Number(item.available_quantity)} {item.base_unit_symbol}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Recent Runs Table */}
      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
          <div className="flex items-center gap-2">
            <ClipboardList className="h-4 w-4 text-slate-500" />
            <h3 className="text-sm font-semibold text-slate-900">Recent Production Runs</h3>
          </div>
          <Link to="/production/runs" className="text-xs font-medium text-sky-700">
            All runs →
          </Link>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-[11px] uppercase tracking-wider text-slate-500">
              <tr>
                <th className="px-4 py-3 font-medium">Order</th>
                <th className="px-4 py-3 font-medium">Product (BOM)</th>
                <th className="px-4 py-3 font-medium">Date</th>
                <th className="px-4 py-3 font-medium">Expected / Good</th>
                <th className="px-4 py-3 font-medium">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {dash.recent_runs.map((r) => (
                <tr key={r.id} className="hover:bg-slate-50/70">
                  <td className="px-4 py-3 font-mono font-medium">
                    <Link
                      to={`/production/runs/${r.id}`}
                      className="text-sky-700 hover:underline"
                    >
                      {r.order_number}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-slate-700">
                    {r.product_name} (v{r.bom_version_snapshot})
                  </td>
                  <td className="px-4 py-3 font-mono text-slate-600">{r.production_date}</td>
                  <td className="px-4 py-3 font-mono">
                    {Number(r.expected_output)} / {Number(r.actual_good_output)}
                  </td>
                  <td className="px-4 py-3 font-mono text-slate-800">{r.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
