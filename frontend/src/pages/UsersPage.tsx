import React, { useEffect, useState } from "react";
import { AlertCircle, Plus, UserCheck, UserX } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { api, ApiError } from "../lib/api";
import { ROLE_META } from "../lib/permissions";
import { Role, UserProfile } from "../types/auth";
import { RoleBadge } from "../components/RoleBadge";

const ALL_ROLES: Role[] = [
  "admin",
  "order_manager",
  "floor_supervisor",
  "qa_inspector",
  "auditor",
];

export function UsersPage() {
  const { user: currentUser } = useAuth();
  const [users, setUsers] = useState<UserProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);

  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [department, setDepartment] = useState("Manufacturing Operations");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<Role>("floor_supervisor");
  const [submitting, setSubmitting] = useState(false);

  const fetchUsers = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.listUsers();
      setUsers(res.items);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load users.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void fetchUsers();
  }, []);

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await api.createUser({
        email: email.trim(),
        full_name: fullName.trim(),
        department: department.trim(),
        password,
        role,
      });
      setEmail("");
      setFullName("");
      setPassword("");
      setShowCreate(false);
      await fetchUsers();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to create user.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleRoleChange = async (targetUser: UserProfile, nextRole: Role) => {
    setError(null);
    try {
      await api.updateUser(targetUser.id, { role: nextRole });
      await fetchUsers();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to update role.");
    }
  };

  const handleToggleActive = async (targetUser: UserProfile) => {
    setError(null);
    try {
      await api.updateUser(targetUser.id, { is_active: !targetUser.is_active });
      await fetchUsers();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to update user status.");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">
            Users & Role Provisioning
          </h2>
          <p className="text-xs text-slate-500">
            Assign personnel to one of the five FactoryFlow roles. Every change is audited.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setShowCreate((prev) => !prev)}
          className="inline-flex items-center gap-1.5 rounded-lg bg-slate-900 px-3.5 py-2 text-xs font-semibold text-white hover:bg-slate-800"
        >
          <Plus className="h-3.5 w-3.5" />
          {showCreate ? "Close Form" : "Provision User"}
        </button>
      </div>

      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-xs text-rose-700">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {showCreate && (
        <form
          onSubmit={handleCreateUser}
          className="grid gap-4 rounded-xl border border-slate-200 bg-white p-5 shadow-sm sm:grid-cols-2 lg:grid-cols-3"
        >
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">
              Full Name
            </label>
            <input
              type="text"
              required
              minLength={2}
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-xs focus:border-slate-900 focus:outline-none"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">
              Work Email
            </label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-xs focus:border-slate-900 focus:outline-none"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">
              Department
            </label>
            <input
              type="text"
              required
              value={department}
              onChange={(e) => setDepartment(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-xs focus:border-slate-900 focus:outline-none"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">
              Role
            </label>
            <select
              value={role}
              onChange={(e) => setRole(e.target.value as Role)}
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs focus:border-slate-900 focus:outline-none"
            >
              {ALL_ROLES.map((r) => (
                <option key={r} value={r}>
                  {ROLE_META[r].label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">
              Initial Password (min 8 chars)
            </label>
            <input
              type="password"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-xs focus:border-slate-900 focus:outline-none"
            />
          </div>
          <div className="flex items-end">
            <button
              type="submit"
              disabled={submitting}
              className="w-full rounded-lg bg-slate-900 px-4 py-2 text-xs font-semibold text-white hover:bg-slate-800 disabled:opacity-50"
            >
              {submitting ? "Creating..." : "Create Account"}
            </button>
          </div>
        </form>
      )}

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        {loading ? (
          <div className="p-8 text-center text-xs text-slate-500">
            Loading user directory...
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-[11px] uppercase tracking-wider text-slate-500">
                <tr>
                  <th className="px-5 py-3 font-medium">User</th>
                  <th className="px-5 py-3 font-medium">Department</th>
                  <th className="px-5 py-3 font-medium">Assigned Role</th>
                  <th className="px-5 py-3 font-medium">Status</th>
                  <th className="px-5 py-3 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {users.map((u) => {
                  const isSelf = currentUser?.id === u.id;
                  return (
                    <tr key={u.id} className="hover:bg-slate-50/70">
                      <td className="px-5 py-3.5">
                        <div className="font-medium text-slate-900">{u.full_name}</div>
                        <div className="text-[11px] text-slate-500">{u.email}</div>
                      </td>
                      <td className="px-5 py-3.5 text-slate-600">{u.department}</td>
                      <td className="px-5 py-3.5">
                        <div className="flex items-center gap-2">
                          <RoleBadge role={u.role} />
                          <select
                            aria-label={`Change role for ${u.email}`}
                            value={u.role}
                            onChange={(e) =>
                              void handleRoleChange(u, e.target.value as Role)
                            }
                            className="rounded border border-slate-200 bg-white px-2 py-1 text-[11px] text-slate-700"
                          >
                            {ALL_ROLES.map((r) => (
                              <option key={r} value={r}>
                                {ROLE_META[r].shortLabel}
                              </option>
                            ))}
                          </select>
                        </div>
                      </td>
                      <td className="px-5 py-3.5">
                        <span
                          className={`inline-flex rounded-full px-2 py-0.5 text-[11px] font-medium ${
                            u.is_active
                              ? "bg-emerald-50 text-emerald-700"
                              : "bg-slate-100 text-slate-500"
                          }`}
                        >
                          {u.is_active ? "Active" : "Deactivated"}
                        </span>
                      </td>
                      <td className="px-5 py-3.5">
                        <button
                          type="button"
                          disabled={isSelf && u.is_active}
                          onClick={() => void handleToggleActive(u)}
                          className="inline-flex items-center gap-1 rounded-md border border-slate-200 px-2.5 py-1 text-[11px] font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
                        >
                          {u.is_active ? (
                            <>
                              <UserX className="h-3 w-3" /> Deactivate
                            </>
                          ) : (
                            <>
                              <UserCheck className="h-3 w-3" /> Reactivate
                            </>
                          )}
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
