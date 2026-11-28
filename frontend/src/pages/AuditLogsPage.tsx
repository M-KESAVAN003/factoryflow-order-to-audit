import React, { useEffect, useState } from "react";
import { AlertCircle, Search } from "lucide-react";
import { api, ApiError } from "../lib/api";
import { formatRoleLabel } from "../lib/permissions";
import { AuditLogItem } from "../types/dashboard";

export function AuditLogsPage() {
  const [logs, setLogs] = useState<AuditLogItem[]>([]);
  const [total, setTotal] = useState(0);
  const [actionFilter, setActionFilter] = useState("");
  const [roleFilter, setRoleFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadLogs = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.listAuditLogs({
        action: actionFilter || undefined,
        actor_role: roleFilter || undefined,
        status: statusFilter || undefined,
        limit: 100,
      });
      setLogs(res.items);
      setTotal(res.total);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load audit logs.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadLogs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleFilterSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    void loadLogs();
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">
            Immutable Security & Compliance Audit Trail
          </h2>
          <p className="text-xs text-slate-500">
            Showing {logs.length} of {total} recorded audit events.
          </p>
        </div>
      </div>

      <form
        onSubmit={handleFilterSubmit}
        className="grid gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:grid-cols-4"
      >
        <input
          type="text"
          placeholder="Filter action (e.g. auth., user.)"
          value={actionFilter}
          onChange={(e) => setActionFilter(e.target.value)}
          className="rounded-lg border border-slate-300 px-3 py-2 text-xs focus:border-slate-900 focus:outline-none"
        />
        <select
          value={roleFilter}
          onChange={(e) => setRoleFilter(e.target.value)}
          className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs focus:border-slate-900 focus:outline-none"
        >
          <option value="">All roles</option>
          <option value="admin">System Administrator</option>
          <option value="order_manager">Order Manager</option>
          <option value="floor_supervisor">Floor Supervisor</option>
          <option value="qa_inspector">QA Inspector</option>
          <option value="auditor">Compliance Auditor</option>
          <option value="owner">Factory Owner</option>
          <option value="anonymous">Anonymous</option>
        </select>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs focus:border-slate-900 focus:outline-none"
        >
          <option value="">All statuses</option>
          <option value="success">Success</option>
          <option value="failure">Failure / Denied</option>
        </select>
        <button
          type="submit"
          className="inline-flex items-center justify-center gap-1.5 rounded-lg bg-slate-900 px-4 py-2 text-xs font-semibold text-white hover:bg-slate-800"
        >
          <Search className="h-3.5 w-3.5" />
          Apply Filters
        </button>
      </form>

      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-xs text-rose-700">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        {loading ? (
          <div className="p-8 text-center text-xs text-slate-500">
            Querying audit ledger...
          </div>
        ) : logs.length === 0 ? (
          <div className="p-8 text-center text-xs text-slate-500">
            No audit events matched the selected filters.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-[11px] uppercase tracking-wider text-slate-500">
                <tr>
                  <th className="px-4 py-3 font-medium">Timestamp</th>
                  <th className="px-4 py-3 font-medium">Action</th>
                  <th className="px-4 py-3 font-medium">Actor</th>
                  <th className="px-4 py-3 font-medium">Role</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {logs.map((entry) => (
                  <tr key={entry.id} className="hover:bg-slate-50/70">
                    <td className="whitespace-nowrap px-4 py-3 font-mono text-[11px] text-slate-500">
                      {new Date(entry.created_at).toLocaleString()}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 font-mono font-medium text-slate-900">
                      {entry.action}
                    </td>
                    <td className="px-4 py-3 text-slate-700">{entry.actor_email}</td>
                    <td className="px-4 py-3 text-slate-600">
                      {formatRoleLabel(entry.actor_role)}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex rounded-full px-2 py-0.5 text-[11px] font-medium ${
                          entry.status === "success"
                            ? "bg-emerald-50 text-emerald-700"
                            : "bg-rose-50 text-rose-700"
                        }`}
                      >
                        {entry.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-600">
                      {entry.details ?? "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
