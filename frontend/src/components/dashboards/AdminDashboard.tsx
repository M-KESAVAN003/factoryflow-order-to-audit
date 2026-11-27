import { Link } from "react-router-dom";
import { ScrollText, ShieldAlert, Users } from "lucide-react";
import { RoleDashboardResponse } from "../../types/dashboard";
import { formatRoleLabel } from "../../lib/permissions";
import { ModuleAccessList, RecentActivityTable, StatGrid } from "./DashboardPrimitives";

export function AdminDashboard({ data }: { data: RoleDashboardResponse }) {
  const totalUsers = Object.values(data.role_distribution).reduce((a, b) => a + b, 0);

  return (
    <div className="space-y-6" data-testid="dashboard-admin">
      <div className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-indigo-200 bg-indigo-50/70 p-5">
        <div>
          <h2 className="text-base font-semibold text-slate-900">
            Platform Governance & Identity Control
          </h2>
          <p className="mt-1 text-xs text-slate-600">
            Manage all five FactoryFlow operational roles, inspect Neon PostgreSQL health, and monitor security audit events.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link
            to="/users"
            className="inline-flex items-center gap-1.5 rounded-lg bg-slate-900 px-3.5 py-2 text-xs font-semibold text-white hover:bg-slate-800"
          >
            <Users className="h-3.5 w-3.5" />
            Manage Users
          </Link>
          <Link
            to="/audit-logs"
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50"
          >
            <ScrollText className="h-3.5 w-3.5" />
            Inspect Audit Trail
          </Link>
        </div>
      </div>

      <StatGrid stats={data.stats} />

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm lg:col-span-1">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-900">
              Personnel by Role
            </h3>
            <ShieldAlert className="h-4 w-4 text-indigo-600" />
          </div>
          <div className="space-y-3">
            {Object.entries(data.role_distribution).map(([roleKey, count]) => {
              const pct = totalUsers > 0 ? Math.round((count / totalUsers) * 100) : 0;
              return (
                <div key={roleKey}>
                  <div className="flex justify-between text-xs">
                    <span className="font-medium text-slate-700">
                      {formatRoleLabel(roleKey)}
                    </span>
                    <span className="font-mono text-slate-600">{count}</span>
                  </div>
                  <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
                    <div
                      className="h-full rounded-full bg-indigo-600"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="lg:col-span-2">
          <ModuleAccessList modules={data.modules} />
        </div>
      </div>

      <RecentActivityTable
        items={data.recent_activity}
        title="Global Security & Provisioning Audit Feed"
        emptyMessage="No audit events recorded yet."
      />
    </div>
  );
}
