import { useState } from "react";
import { Download } from "lucide-react";
import { PRESET_OPTIONS, triggerReportDownload } from "../components/ReportScaffold";
import { ReportFilterParams } from "../types/reports";
import { StatusNotice } from "../components/MasterDataControls";

const EXPORTABLE_REPORTS = [
  { key: "sales", label: "Sales Register" },
  { key: "sales_customers", label: "Customer-wise Sales" },
  { key: "sales_products", label: "Product-wise Sales" },
  { key: "sales_salesmen", label: "Salesman Performance" },
  { key: "gst_outward", label: "GST Outward Supplies (Indicative)" },
  { key: "gst_hsn", label: "GST HSN Summary" },
  { key: "purchases", label: "Purchase Register" },
  { key: "stock_summary", label: "Consolidated Stock Summary" },
  { key: "stock_ledger", label: "Stock Ledger" },
  { key: "production", label: "Production Register" },
  { key: "production_variance", label: "Production Variance" },
  { key: "production_costing", label: "Production Costing" },
  { key: "payments", label: "Customer Payment Register" },
  { key: "receivables", label: "Receivables Outstanding" },
  { key: "receivables_ageing", label: "Receivables Ageing" },
];

export function ReportExportCenterPage() {
  const [filters, setFilters] = useState<ReportFilterParams>({ preset: "last_30_days" });
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const exportOne = async (fmt: "excel" | "csv" | "pdf", key: string) => {
    setError(null);
    setSuccess(null);
    try {
      await triggerReportDownload(fmt, key, filters);
      setSuccess(`Downloaded ${key} as ${fmt.toUpperCase()}.`);
    } catch {
      setError(`Failed to export ${key}.`);
    }
  };

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-lg font-semibold text-slate-900">Report Export Center</h2>
        <p className="text-xs text-slate-500">
          Download reconciled Excel (.xlsx), CSV, and paginated PDF audit packs with consistent period cut-offs.
        </p>
      </div>

      <StatusNotice error={error} success={success} />

      <div className="flex flex-wrap gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm text-xs">
        <select
          value={filters.preset ?? "last_30_days"}
          onChange={(e) => setFilters({ ...filters, preset: e.target.value, date_from: undefined, date_to: undefined })}
          className="rounded-lg border border-slate-300 bg-white px-3 py-1.5"
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
          className="rounded-lg border border-slate-300 px-3 py-1.5"
        />
        <input
          type="date"
          value={filters.date_to ?? ""}
          onChange={(e) => setFilters({ ...filters, date_to: e.target.value || undefined, preset: "custom" })}
          className="rounded-lg border border-slate-300 px-3 py-1.5"
        />
      </div>

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-50 text-[11px] uppercase tracking-wider text-slate-500">
            <tr>
              <th className="px-4 py-3 font-medium">Audit Report</th>
              <th className="px-4 py-3 font-medium">Downloads</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {EXPORTABLE_REPORTS.map((r) => (
              <tr key={r.key}>
                <td className="px-4 py-3 font-medium text-slate-900">{r.label}</td>
                <td className="px-4 py-3 space-x-2">
                  <button
                    type="button"
                    onClick={() => exportOne("excel", r.key)}
                    className="inline-flex items-center gap-1 rounded border border-slate-300 px-2.5 py-1 hover:bg-slate-50"
                  >
                    <Download className="h-3 w-3" /> .xlsx
                  </button>
                  <button
                    type="button"
                    onClick={() => exportOne("csv", r.key)}
                    className="inline-flex items-center gap-1 rounded border border-slate-300 px-2.5 py-1 hover:bg-slate-50"
                  >
                    <Download className="h-3 w-3" /> .csv
                  </button>
                  <button
                    type="button"
                    onClick={() => exportOne("pdf", r.key)}
                    className="inline-flex items-center gap-1 rounded bg-slate-900 px-2.5 py-1 text-white"
                  >
                    <Download className="h-3 w-3" /> .pdf
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
