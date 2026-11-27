import { Link } from "react-router-dom";
import { FileSearch } from "lucide-react";
import { RoleDashboardResponse, WorkspaceCheckResponse } from "../../types/dashboard";
import {
  ModuleAccessList,
  RecentActivityTable,
  StatGrid,
  WorkspaceVerificationCard,
} from "./DashboardPrimitives";

export function AuditorDashboard({
  data,
  checks,
}: {
  data: RoleDashboardResponse;
  checks: WorkspaceCheckResponse[];
}) {
  return (
    <div className="space-y-6" data-testid="dashboard-auditor">
      <div className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-slate-300 bg-slate-100 p-5">
        <div>
          <h2 className="text-base font-semibold text-slate-900">
            Compliance & End-to-End Traceability Console
          </h2>
          <p className="mt-1 text-xs text-slate-600">
            Immutable read-only oversight across orders, shop-floor execution, QA records, and platform security audit logs.
          </p>
        </div>
        <Link
          to="/audit-logs"
          className="inline-flex items-center gap-1.5 rounded-lg bg-slate-900 px-3.5 py-2 text-xs font-semibold text-white hover:bg-slate-800"
        >
          <FileSearch className="h-3.5 w-3.5" />
          Open Audit Explorer
        </Link>
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
        title="Platform-Wide Immutable Audit Stream"
        emptyMessage="No audit events recorded yet."
      />
    </div>
  );
}
