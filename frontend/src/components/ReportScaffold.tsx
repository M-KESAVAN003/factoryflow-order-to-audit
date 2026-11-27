import React from "react";
import { Download, RefreshCw, ShieldCheck } from "lucide-react";
import { api } from "../lib/api";
import { DatePreset, ReportFilterParams } from "../types/reports";
import { StatusNotice } from "./MasterDataControls";

export const PRESET_OPTIONS: { value: DatePreset; label: string }[] = [
  { value: "today", label: "Today" },
  { value: "yesterday", label: "Yesterday" },
  { value: "last_7_days", label: "Last 7 Days" },
  { value: "last_30_days", label: "Last 30 Days" },
  { value: "current_month", label: "Current Month" },
  { value: "previous_month", label: "Previous Month" },
  { value: "financial_year", label: "Financial Year" },
  { value: "all", label: "All Time" },
];

export async function triggerReportDownload(
  format: "excel" | "csv" | "pdf",
  reportType: string,
  params?: ReportFilterParams
) {
  const blob = await api.exportReport(format, reportType, params);
  const url = URL.createObjectURL(blob);
  const ext = format === "excel" ? "xlsx" : format;
  const a = document.createElement("a");
  a.href = url;
  a.download = `${reportType}-report.${ext}`;
  a.click();
  URL.revokeObjectURL(url);
}

interface ReportScaffoldProps {
  title: string;
  subtitle: string;
  reportType: string;
  filters: ReportFilterParams;
  onFiltersChange: (next: ReportFilterParams) => void;
  onRefresh: () => void;
  showAsOfDate?: boolean;
  reconciled?: boolean;
  disclaimer?: string;
  loading: boolean;
  error: string | null;
  children: React.ReactNode;
}

export function ReportScaffold({
  title,
  subtitle,
  reportType,
  filters,
  onFiltersChange,
  onRefresh,
  showAsOfDate = false,
  reconciled,
  disclaimer,
  loading,
  error,
  children,
}: ReportScaffoldProps) {
  const handleDownload = async (fmt: "excel" | "csv" | "pdf") => {
    try {
      await triggerReportDownload(fmt, reportType, filters);
    } catch {
      /* handled by parent if needed */
    }
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-semibold text-slate-900">{title}</h2>
            {reconciled && (
              <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-0.5 text-[10px] font-medium text-emerald-700">
                <ShieldCheck className="h-3 w-3" /> Source Reconciled
              </span>
            )}
          </div>
          <p className="text-xs text-slate-500">{subtitle}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => handleDownload("excel")}
            className="inline-flex items-center gap-1 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
          >
            <Download className="h-3.5 w-3.5" /> Excel (.xlsx)
          </button>
          <button
            type="button"
            onClick={() => handleDownload("csv")}
            className="inline-flex items-center gap-1 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
          >
            <Download className="h-3.5 w-3.5" /> CSV
          </button>
          <button
            type="button"
            onClick={() => handleDownload("pdf")}
            className="inline-flex items-center gap-1 rounded-lg bg-slate-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-slate-800"
          >
            <Download className="h-3.5 w-3.5" /> PDF
          </button>
        </div>
      </div>

      {disclaimer && (
        <div className="rounded-xl border border-amber-300 bg-amber-50 p-3.5 text-xs text-amber-900">
          {disclaimer}
        </div>
      )}

      <div className="flex flex-wrap items-end gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm text-xs">
        <div>
          <label className="mb-1 block font-medium text-slate-600">Period Preset</label>
          <select
            value={filters.preset ?? "last_30_days"}
            onChange={(e) =>
              onFiltersChange({
                ...filters,
                preset: e.target.value,
                date_from: undefined,
                date_to: undefined,
              })
            }
            className="rounded-lg border border-slate-300 bg-white px-2.5 py-1.5"
          >
            {PRESET_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="mb-1 block font-medium text-slate-600">From Date</label>
          <input
            type="date"
            value={filters.date_from ?? ""}
            onChange={(e) =>
              onFiltersChange({ ...filters, date_from: e.target.value || undefined, preset: "custom" })
            }
            className="rounded-lg border border-slate-300 px-2.5 py-1.5"
          />
        </div>
        <div>
          <label className="mb-1 block font-medium text-slate-600">To Date</label>
          <input
            type="date"
            value={filters.date_to ?? ""}
            onChange={(e) =>
              onFiltersChange({ ...filters, date_to: e.target.value || undefined, preset: "custom" })
            }
            className="rounded-lg border border-slate-300 px-2.5 py-1.5"
          />
        </div>
        {showAsOfDate && (
          <div>
            <label className="mb-1 block font-medium text-slate-600">As of Cut-off Date</label>
            <input
              type="date"
              value={filters.as_of_date ?? ""}
              onChange={(e) =>
                onFiltersChange({ ...filters, as_of_date: e.target.value || undefined })
              }
              className="rounded-lg border border-slate-300 px-2.5 py-1.5"
            />
          </div>
        )}
        <button
          type="button"
          onClick={onRefresh}
          className="inline-flex items-center gap-1 rounded-lg border border-slate-300 bg-slate-50 px-3 py-1.5 font-medium text-slate-700 hover:bg-slate-100"
        >
          <RefreshCw className="h-3.5 w-3.5" /> Apply
        </button>
      </div>

      <StatusNotice error={error} />

      {loading ? (
        <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-xs text-slate-500">
          Compiling reconciled audit report from database records...
        </div>
      ) : (
        children
      )}
    </div>
  );
}
