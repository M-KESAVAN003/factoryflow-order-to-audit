import { Link } from "react-router-dom";
import { BarChart3, FileSpreadsheet } from "lucide-react";
import { RoleDashboardResponse, WorkspaceCheckResponse } from "../../types/dashboard";
import {
  ModuleAccessList,
  RecentActivityTable,
  StatGrid,
  WorkspaceVerificationCard,
} from "./DashboardPrimitives";

export function OwnerRoleDashboard({
  data,
  checks,
}: {
  data: RoleDashboardResponse;
  checks: WorkspaceCheckResponse[];
}) {
  return (
    <div className="space-y-6" data-testid="dashboard-owner">
      <div className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-purple-200 bg-purple-50/70 p-5">
        <div>
          <h2 className="text-base font-semibold text-slate-900">
            Executive Owner Oversight & Business Intelligence
          </h2>
          <p className="mt-1 text-xs text-slate-600">
            Read-only live visibility across sales, GST summaries, production cost & margin, inventory valuation, and customer receivables.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link
            to="/owner"
            className="inline-flex items-center gap-1.5 rounded-lg bg-slate-900 px-3.5 py-2 text-xs font-semibold text-white hover:bg-slate-800"
          >
            <BarChart3 className="h-3.5 w-3.5" />
            Owner KPI Dashboard
          </Link>
          <Link
            to="/reports/exports"
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50"
          >
            <FileSpreadsheet className="h-3.5 w-3.5" />
            Audit & Tax Reports
          </Link>
        </div>
      </div>

      <StatGrid stats={data.stats} />

      <div className="grid gap-6 lg:grid-cols-2">
        <WorkspaceVerificationCard
          checks={checks}
          databaseConnected={data.database_connected}
        />
        <ModuleAccessList modules={data.modules} />
      </div>

      <RecentActivityTable
        items={data.recent_activity}
        title="Compliance & Operational Audit Activity"
        emptyMessage="No audit events recorded yet."
      />
    </div>
  );
}
