import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { FileSpreadsheet, ShieldCheck } from "lucide-react";
import { api, ApiError } from "../lib/api";
import { DomainDashboard } from "../types/reports";
import { StatusNotice } from "../components/MasterDataControls";

const AUDITOR_LINKS = [
  { to: "/reports/sales", label: "Sales Register" },
  { to: "/reports/sales/customers", label: "Customer Sales Report" },
  { to: "/reports/sales/products", label: "Product Sales Report" },
  { to: "/reports/gst", label: "GST Outward Summary" },
  { to: "/reports/gst/hsn", label: "HSN Summary" },
  { to: "/reports/purchases", label: "Purchase Register" },
  { to: "/reports/stock/raw-materials", label: "Raw Material Stock" },
  { to: "/reports/stock/packaging", label: "Packaging Stock" },
  { to: "/reports/stock/finished-goods", label: "Finished Goods Stock" },
  { to: "/reports/stock/ledger", label: "Stock Ledger" },
  { to: "/reports/production", label: "Production Register" },
  { to: "/reports/production/variance", label: "Production Variance" },
  { to: "/reports/production/costing", label: "Production Cost Report" },
  { to: "/reports/payments", label: "Payment Register" },
  { to: "/reports/receivables", label: "Receivables Report" },
  { to: "/reports/receivables/ageing", label: "Receivables Ageing" },
  { to: "/reports/exports", label: "Report Export Center" },
];

export function AuditorDashboardPage() {
  const [fin, setFin] = useState<DomainDashboard | null>(null);
  const [inv, setInv] = useState<DomainDashboard | null>(null);
  const [prod, setProd] = useState<DomainDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const [f, i, p] = await Promise.all([
          api.domainDashboard("finance"),
          api.domainDashboard("inventory"),
          api.domainDashboard("production"),
        ]);
        setFin(f);
        setInv(i);
        setProd(p);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Failed to load auditor dashboard.");
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, []);

  if (loading) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-xs text-slate-500">
        Loading read-only Accountant & Auditor portal...
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-semibold text-slate-900">Accountant & Auditor Dashboard</h2>
            <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2.5 py-0.5 text-[10px] font-medium text-slate-700">
              <ShieldCheck className="h-3 w-3" /> Read-Only Access
            </span>
          </div>
          <p className="text-xs text-slate-500">
            End-to-end financial, GST, stock ledger, variance, costing, and receivables audit reports.
          </p>
        </div>
        <Link
          to="/reports/exports"
          className="inline-flex items-center gap-1.5 rounded-lg bg-slate-900 px-3 py-2 text-xs font-medium text-white"
        >
          <FileSpreadsheet className="h-4 w-4" /> Export Center
        </Link>
      </div>

      <StatusNotice error={error} />

      <div className="grid gap-4 sm:grid-cols-3">
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm text-xs space-y-1">
          <div className="font-semibold text-slate-900">Receivables & Collections</div>
          <div>Invoiced: Rs {fin?.metrics.total_invoiced ?? "0.00"}</div>
          <div>Collected: Rs {fin?.metrics.total_collected ?? "0.00"}</div>
          <div className="font-semibold text-amber-700">Outstanding: Rs {fin?.metrics.total_outstanding ?? "0.00"}</div>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm text-xs space-y-1">
          <div className="font-semibold text-slate-900">Stock Valuation & Ledger</div>
          <div>Tracked Items: {inv?.metrics.tracked_items ?? 0}</div>
          <div>Ledger Entries: {inv?.metrics.ledger_movements ?? 0}</div>
          <div className="font-semibold text-slate-900">Total Value: Rs {inv?.metrics.total_valuation ?? "0.00"}</div>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm text-xs space-y-1">
          <div className="font-semibold text-slate-900">Manufacturing Costing</div>
          <div>Runs: {prod?.metrics.runs_count ?? 0}</div>
          <div>Good Output: {prod?.metrics.good_output ?? 0} pkts</div>
          <div className="font-semibold text-sky-700">Total Cost: Rs {prod?.metrics.total_cost ?? "0.00"}</div>
        </div>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm space-y-3">
        <div className="text-sm font-semibold text-slate-900">Audit Reports Directory</div>
        <div className="grid gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
          {AUDITOR_LINKS.map((item) => (
            <Link
              key={item.to}
              to={item.to}
              className="rounded-lg border border-slate-200 px-3.5 py-2.5 text-xs font-medium text-slate-800 hover:bg-slate-50"
            >
              {item.label}
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
