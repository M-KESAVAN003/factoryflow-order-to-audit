import { ROLE_META } from "../lib/permissions";
import { Role } from "../types/auth";

export function RoleBadge({ role }: { role: Role | string }) {
  const meta = ROLE_META[role as Role];
  return (
    <span
      className={`inline-flex items-center rounded-md border px-2.5 py-0.5 text-xs font-medium ${
        meta?.badgeClasses ?? "bg-slate-100 text-slate-700 border-slate-200"
      }`}
    >
      {meta?.label ?? role}
    </span>
  );
}
