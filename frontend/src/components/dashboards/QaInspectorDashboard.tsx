import { CheckSquare } from "lucide-react";
import { RoleDashboardResponse, WorkspaceCheckResponse } from "../../types/dashboard";
import {
  ModuleAccessList,
  RecentActivityTable,
  StatGrid,
  WorkspaceVerificationCard,
} from "./DashboardPrimitives";

export function QaInspectorDashboard({
  data,
  checks,
}: {
  data: RoleDashboardResponse;
  checks: WorkspaceCheckResponse[];
}) {
  return (
    <div className="space-y-6" data-testid="dashboard-qa_inspector">
      <div className="flex items-start justify-between gap-4 rounded-xl border border-emerald-200 bg-emerald-50/70 p-5">
        <div>
          <h2 className="text-base font-semibold text-slate-900">
            Quality Assurance & Batch Release Gate
          </h2>
          <p className="mt-1 text-xs text-slate-600">
            Independent quality authority to inspect production lots, place non-conformance holds, and approve batch release without order-creation conflicts.
          </p>
        </div>
        <CheckSquare className="h-6 w-6 shrink-0 text-emerald-700" />
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
        title="Your QA Inspector Activity History"
        emptyMessage="No QA session events recorded yet."
      />
    </div>
  );
}
