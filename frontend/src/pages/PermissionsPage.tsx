import { useEffect, useState } from "react";
import { AlertCircle, Check, Minus } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { api, ApiError } from "../lib/api";
import { RoleMatrixResponse } from "../types/auth";
import { RoleBadge } from "../components/RoleBadge";

export function PermissionsPage() {
  const { user } = useAuth();
  const [matrix, setMatrix] = useState<RoleMatrixResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const res = await api.roleMatrix();
        setMatrix(res);
      } catch (err) {
        setError(
          err instanceof ApiError ? err.message : "Failed to load role matrix."
        );
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, []);

  if (loading) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-xs text-slate-500">
        Loading five-role permission matrix...
      </div>
    );
  }

  if (error || !matrix) {
    return (
      <div className="flex items-center gap-2 rounded-xl border border-rose-200 bg-rose-50 p-4 text-xs text-rose-700">
        <AlertCircle className="h-4 w-4" />
        <span>{error ?? "Unable to load permissions matrix."}</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-slate-900">
          Five-Role Access Control Matrix
        </h2>
        <p className="text-xs text-slate-500">
          Live permission definitions served directly from the FastAPI RBAC registry.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        {matrix.roles.map((r) => {
          const isCurrent = user?.role === r.role;
          return (
            <div
              key={r.role}
              className={`rounded-xl border p-4 shadow-sm ${
                isCurrent
                  ? "border-slate-900 bg-white ring-1 ring-slate-900"
                  : "border-slate-200 bg-white"
              }`}
            >
              <div className="flex items-center justify-between gap-2">
                <RoleBadge role={r.role} />
                {isCurrent && (
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-900">
                    Your Role
                  </span>
                )}
              </div>
              <p className="mt-2.5 text-xs leading-relaxed text-slate-600">
                {r.description}
              </p>
              <p className="mt-3 font-mono text-[11px] text-slate-500">
                {r.permissions.length} permissions
              </p>
            </div>
          );
        })}
      </div>

      <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-50 text-[11px] uppercase tracking-wider text-slate-500">
            <tr>
              <th className="px-4 py-3 font-medium">Permission</th>
              {matrix.roles.map((r) => (
                <th key={r.role} className="px-4 py-3 text-center font-medium">
                  {r.display_name}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {matrix.all_permissions.map((perm) => (
              <tr key={perm} className="hover:bg-slate-50/60">
                <td className="px-4 py-2.5 font-mono text-slate-800">{perm}</td>
                {matrix.roles.map((r) => {
                  const granted = r.permissions.includes(perm);
                  return (
                    <td key={`${r.role}-${perm}`} className="px-4 py-2.5 text-center">
                      {granted ? (
                        <Check className="mx-auto h-4 w-4 text-emerald-600" />
                      ) : (
                        <Minus className="mx-auto h-4 w-4 text-slate-300" />
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
