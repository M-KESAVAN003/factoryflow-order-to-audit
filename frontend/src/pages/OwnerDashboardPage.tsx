import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { api, ApiError } from "../lib/api";
import { OwnerDashboard, ReportFilterParams } from "../types/reports";
import { PRESET_OPTIONS } from "../components/ReportScaffold";
import { StatusNotice } from "../components/MasterDataControls";

function MiniTrendCard({
  title,
  items,
  unitPrefix = "Rs ",
}: {
  title: string;
  items: { label: string; value: string; sub?: string | null }[];
  unitPrefix?: string;
}) {
  const max = Math.max(1, ...items.map((i) => Number(i.value) || 0));
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm space-y-2.5">
      <div className="text-xs font-semibold text-slate-900">{title}</div>
      {items.length === 0 ? (
        <div className="py-4 text-center text-[11px] text-slate-400">No data in selected window.</div>
      ) : (
        <div className="space-y-1.5">
          {items.slice(0, 6).map((row) => {
            const pct = Math.min(100, Math.round(((Number(row.value) || 0) / max) * 100));
            return (
              <div key={row.label} className="space-y-0.5 text-[11px]">
                <div className="flex justify-between text-slate-600">
                  <span className="truncate pr-2">{row.label}</span>
                  <span className="font-mono font-medium text-slate-900">
                    {unitPrefix}
                    {Number(row.value).toFixed(2)}
                    {row.sub ? ` (vs ${Number(row.sub).toFixed(1)})` : ""}
                  </span>
                </div>
                <div className="h-1.5 w-full rounded-full bg-slate-100">
                  <div className="h-1.5 rounded-full bg-slate-800" style={{ width: `${pct}%` }} />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export function OwnerDashboardPage() {
  const [filters, setFilters] = useState<ReportFilterParams>({ preset: "last_30_days" });
  const [data, setData] = useState<OwnerDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await api.ownerDashboard(filters));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load owner dashboard.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters.preset, filters.date_from, filters.date_to]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Owner Executive Dashboard</h2>
          <p className="text-xs text-slate-500">
            Live database performance across sales, GST, purchasing, manufacturing cost, and receivables.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <select
            value={filters.preset ?? "last_30_days"}
            onChange={(e) => setFilters({ preset: e.target.value })}
            className="rounded-lg border border-slate-300 bg-white px-2.5 py-1.5"
          >
            {PRESET_OPTIONS.map((p) => (
              <option key={p.value} value={p.value}>
                {p.label}
              </option>
            ))}
          </select>
          <input
            type="date"
            value={filters.date_from ?? ""}
            onChange={(e) => setFilters({ ...filters, date_from: e.target.value || undefined, preset: "custom" })}
            className="rounded-lg border border-slate-300 px-2.5 py-1.5"
          />
          <input
            type="date"
            value={filters.date_to ?? ""}
            onChange={(e) => setFilters({ ...filters, date_to: e.target.value || undefined, preset: "custom" })}
            className="rounded-lg border border-slate-300 px-2.5 py-1.5"
          />
          <button
            type="button"
            onClick={() => void load()}
            className="inline-flex items-center gap-1 rounded-lg bg-slate-900 px-3 py-1.5 font-medium text-white"
          >
            <RefreshCw className="h-3.5 w-3.5" /> Refresh
          </button>
        </div>
      </div>

      <StatusNotice error={error} />

      {loading ? (
        <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-xs text-slate-500">
          Aggregating executive metrics...
        </div>
      ) : data ? (
        <>
          <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5">
            {[
              { label: "Today's Orders", val: String(data.todays_orders) },
              { label: "Pending Orders", val: String(data.pending_orders) },
              { label: "Today's Sales", val: `Rs ${Number(data.todays_sales).toFixed(2)}` },
              { label: "Period Sales (Incl GST)", val: `Rs ${Number(data.monthly_sales).toFixed(2)}` },
              { label: "Taxable Revenue", val: `Rs ${Number(data.monthly_taxable_revenue).toFixed(2)}` },
              { label: "Total GST Collected", val: `Rs ${Number(data.total_gst_collected).toFixed(2)}` },
              { label: "Purchase Value", val: `Rs ${Number(data.purchase_value).toFixed(2)}` },
              { label: "Production Output", val: `${Number(data.production_output)} pkts` },
              { label: "Finished Goods Stock", val: `${Number(data.finished_goods_stock)} pkts` },
              { label: "Raw Material Stock Value", val: `Rs ${Number(data.raw_material_stock_value).toFixed(2)}` },
              { label: "Total Production Cost", val: `Rs ${Number(data.total_production_cost).toFixed(2)}` },
              { label: "Avg Cost / Packet", val: `Rs ${Number(data.average_cost_per_packet).toFixed(2)}` },
              { label: "Gross Margin", val: `${Number(data.gross_margin_pct).toFixed(2)}%` },
              { label: "Customer Receivables", val: `Rs ${Number(data.total_customer_receivables).toFixed(2)}` },
              { label: "Overdue Receivables", val: `Rs ${Number(data.overdue_receivables).toFixed(2)}` },
            ].map((c) => (
              <div key={c.label} className="rounded-xl border border-slate-200 bg-white p-3.5 shadow-sm">
                <div className="text-[11px] text-slate-500">{c.label}</div>
                <div className="mt-1 font-mono text-base font-semibold text-slate-900">{c.val}</div>
              </div>
            ))}
          </div>

          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            <MiniTrendCard title="1. Daily Sales Trend" items={data.daily_sales_trend} />
            <MiniTrendCard title="2. Monthly Revenue (Taxable)" items={data.monthly_revenue_trend} />
            <MiniTrendCard title="3. Product-wise Sales" items={data.product_wise_sales.map((p) => ({ label: p.name, value: p.value }))} />
            <MiniTrendCard title="4. Customer-wise Sales" items={data.customer_wise_sales.map((c) => ({ label: c.name, value: c.value }))} />
            <MiniTrendCard title="5. Purchase vs Sales" items={data.purchase_vs_sales_trend.map((p) => ({ label: p.label, value: p.value, sub: p.secondary_value }))} />
            <MiniTrendCard title="6. Production Actual vs Planned" unitPrefix="" items={data.production_planned_vs_actual.map((p) => ({ label: p.label, value: p.value, sub: p.secondary_value }))} />
            <MiniTrendCard title="7. Material Consumption" unitPrefix="" items={data.material_consumption_comparison.map((m) => ({ label: m.name, value: m.value, sub: m.quantity }))} />
            <MiniTrendCard title="8. Production Wastage" unitPrefix="" items={data.production_wastage.map((w) => ({ label: w.name, value: w.value }))} />
            <MiniTrendCard title="9. Cost Per Packet Trend" items={data.cost_per_packet_trend} />
            <MiniTrendCard title="10. Outstanding Receivables Trend" items={data.outstanding_receivables_trend} />
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm space-y-2">
            <div className="flex items-center justify-between">
              <div className="text-sm font-semibold text-slate-900">Operational & Financial Alerts</div>
              <Link to="/reports/exports" className="text-xs font-medium text-sky-700 hover:underline">
                Open Report Export Center
              </Link>
            </div>
            {data.alerts.length === 0 ? (
              <div className="text-xs text-slate-400">No active alerts.</div>
            ) : (
              data.alerts.map((al, i) => (
                <div
                  key={`${al.category}-${i}`}
                  className={`flex items-start gap-2 rounded-lg border p-2.5 text-xs ${
                    al.severity === "HIGH"
                      ? "border-rose-200 bg-rose-50 text-rose-900"
                      : "border-amber-200 bg-amber-50 text-amber-900"
                  }`}
                >
                  <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                  <div>
                    <strong>{al.category}:</strong> {al.message}
                  </div>
                </div>
              ))
            )}
          </div>
        </>
      ) : null}
    </div>
  );
}
