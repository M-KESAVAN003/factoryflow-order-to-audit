import { Wrench } from "lucide-react";
import { RoleDashboardResponse, WorkspaceCheckResponse } from "../../types/dashboard";
import {
  ModuleAccessList,
  RecentActivityTable,
  StatGrid,
  WorkspaceVerificationCard,
} from "./DashboardPrimitives";

export function FloorSupervisorDashboard({
  data,
  checks,
}: {
  data: RoleDashboardResponse;
  checks: WorkspaceCheckResponse[];
}) {
  return (
    <div className="space-y-6" data-testid="dashboard-floor_supervisor">
      <div className="flex items-start justify-between gap-4 rounded-xl border border-amber-200 bg-amber-50/70 p-5">
        <div>
          <h2 className="text-base font-semibold text-slate-900">
            Shop Floor Execution & Line Supervision
          </h2>
          <p className="mt-1 text-xs text-slate-600">
            Authorized to manage active shop-floor work orders, record line progress, and view released orders & QA hold status.
          </p>
        </div>
        <Wrench className="h-6 w-6 shrink-0 text-amber-700" />
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
        title="Your Shift & Work-Order Session Log"
        emptyMessage="No shift session activity recorded yet."
      />
    </div>
  );
}
