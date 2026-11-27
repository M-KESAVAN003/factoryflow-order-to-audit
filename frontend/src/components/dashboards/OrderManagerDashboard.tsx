import { ClipboardList } from "lucide-react";
import { RoleDashboardResponse, WorkspaceCheckResponse } from "../../types/dashboard";
import {
  ModuleAccessList,
  RecentActivityTable,
  StatGrid,
  WorkspaceVerificationCard,
} from "./DashboardPrimitives";

export function OrderManagerDashboard({
  data,
  checks,
}: {
  data: RoleDashboardResponse;
  checks: WorkspaceCheckResponse[];
}) {
  return (
    <div className="space-y-6" data-testid="dashboard-order_manager">
      <div className="flex items-start justify-between gap-4 rounded-xl border border-sky-200 bg-sky-50/70 p-5">
        <div>
          <h2 className="text-base font-semibold text-slate-900">
            Order Intake & Production Release Workspace
          </h2>
          <p className="mt-1 text-xs text-slate-600">
            Authorized to create customer orders, schedule production batches, and monitor shop-floor progress. QA sign-off and audit logs remain strictly segregated.
          </p>
        </div>
        <ClipboardList className="h-6 w-6 shrink-0 text-sky-700" />
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
        title="Your Recent Session & Order Gate Activity"
        emptyMessage="No session activity recorded yet."
      />
    </div>
  );
}
