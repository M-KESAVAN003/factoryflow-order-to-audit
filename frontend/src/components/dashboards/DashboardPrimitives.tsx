import { Link } from "react-router-dom";
import { CheckCircle2, Lock, ArrowRight, Database } from "lucide-react";
import { AuditLogItem, DashboardModule, DashboardStat, WorkspaceCheckResponse } from "../../types/dashboard";
import { formatRoleLabel } from "../../lib/permissions";

export function StatGrid({ stats }: { stats: DashboardStat[] }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {stats.map((stat) => (
        <div
          key={stat.key}
          className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"
        >
          <p className="text-xs font-medium uppercase tracking-wider text-slate-500">
            {stat.label}
          </p>
          <p className="mt-2 text-2xl font-semibold tracking-tight text-slate-900 tabular-nums">
            {stat.value}
          </p>
          <p className="mt-1 text-xs text-slate-500">{stat.caption}</p>
        </div>
      ))}
    </div>
  );
}

export function ModuleAccessList({ modules }: { modules: DashboardModule[] }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-slate-900">
            Authorized Platform Capabilities
          </h3>
          <p className="text-xs text-slate-500">
            Enforced by FastAPI RBAC dependencies on every endpoint
          </p>
        </div>
        <Link
          to="/permissions"
          className="text-xs font-medium text-sky-700 hover:text-sky-800"
        >
          View full matrix
        </Link>
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        {modules.map((mod) => (
          <div
            key={mod.key}
            className={`rounded-lg border p-3.5 ${
              mod.enabled
                ? "border-slate-200 bg-slate-50/70"
                : "border-slate-100 bg-slate-50/30 opacity-65"
            }`}
          >
            <div className="flex items-start justify-between gap-2">
              <div className="flex items-center gap-2">
                {mod.enabled ? (
                  <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-600" />
                ) : (
                  <Lock className="h-4 w-4 shrink-0 text-slate-400" />
                )}
                <span className="text-sm font-medium text-slate-900">{mod.title}</span>
              </div>
              <span className="rounded bg-white px-2 py-0.5 font-mono text-[10px] text-slate-600 ring-1 ring-slate-200">
                {mod.status}
              </span>
            </div>
            <p className="mt-1.5 text-xs text-slate-600">{mod.description}</p>
            <div className="mt-2 flex items-center justify-between text-[11px]">
              <span className="font-mono text-slate-500">{mod.required_permission}</span>
              {mod.enabled && mod.status === "Live" && (
                <Link
                  to={mod.route}
                  className="inline-flex items-center gap-1 font-medium text-sky-700 hover:text-sky-800"
                >
                  Open <ArrowRight className="h-3 w-3" />
                </Link>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function RecentActivityTable({
  items,
  title,
  emptyMessage,
}: {
  items: AuditLogItem[];
  title: string;
  emptyMessage: string;
}) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-slate-200 px-5 py-4">
        <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
      </div>
      {items.length === 0 ? (
        <div className="p-6 text-center text-xs text-slate-500">{emptyMessage}</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-[11px] uppercase tracking-wider text-slate-500">
              <tr>
                <th className="px-5 py-3 font-medium">Action</th>
                <th className="px-5 py-3 font-medium">Actor</th>
                <th className="px-5 py-3 font-medium">Role</th>
                <th className="px-5 py-3 font-medium">Status</th>
                <th className="px-5 py-3 font-medium">Timestamp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {items.map((item) => (
                <tr key={item.id} className="hover:bg-slate-50/70">
                  <td className="px-5 py-3 font-mono font-medium text-slate-800">
                    {item.action}
                  </td>
                  <td className="px-5 py-3 text-slate-600">{item.actor_email}</td>
                  <td className="px-5 py-3 text-slate-600">
                    {formatRoleLabel(item.actor_role)}
                  </td>
                  <td className="px-5 py-3">
                    <span
                      className={`inline-flex rounded-full px-2 py-0.5 text-[11px] font-medium ${
                        item.status === "success"
                          ? "bg-emerald-50 text-emerald-700"
                          : "bg-rose-50 text-rose-700"
                      }`}
                    >
                      {item.status}
                    </span>
                  </td>
                  <td className="px-5 py-3 font-mono text-[11px] text-slate-500">
                    {new Date(item.created_at).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export function WorkspaceVerificationCard({
  checks,
  databaseConnected,
}: {
  checks: WorkspaceCheckResponse[];
  databaseConnected: boolean;
}) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-900">
          Backend Endpoint Authorization Checks
        </h3>
        <span className="inline-flex items-center gap-1.5 text-xs text-slate-600">
          <Database className="h-3.5 w-3.5 text-sky-600" />
          {databaseConnected ? "Neon PostgreSQL Ready" : "DB Offline"}
        </span>
      </div>
      <div className="space-y-2.5">
        {checks.map((check) => (
          <div
            key={check.workspace}
            className="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 px-3.5 py-2.5 text-xs"
          >
            <div>
              <span className="font-mono font-medium text-slate-900">
                /api/v1/workspaces/{check.workspace}
              </span>
              <span className="ml-2 text-slate-500">({check.phase})</span>
            </div>
            <span
              className={`rounded-md px-2 py-0.5 font-medium ${
                check.can_manage
                  ? "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200"
                  : "bg-sky-50 text-sky-700 ring-1 ring-sky-200"
              }`}
            >
              {check.can_manage ? "Read & Write" : "Read Only"}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
