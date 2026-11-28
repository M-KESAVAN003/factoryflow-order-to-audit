import { Role, UserProfile } from "../types/auth";

export const ROLE_META: Record<
  Role,
  {
    label: string;
    shortLabel: string;
    badgeClasses: string;
    accentClasses: string;
    description: string;
  }
> = {
  admin: {
    label: "System Administrator",
    shortLabel: "Admin",
    badgeClasses: "bg-indigo-50 text-indigo-700 border-indigo-200",
    accentClasses: "bg-indigo-600",
    description: "Full platform governance, provisioning, and audit oversight.",
  },
  order_manager: {
    label: "Order & Production Manager",
    shortLabel: "Order Manager",
    badgeClasses: "bg-sky-50 text-sky-700 border-sky-200",
    accentClasses: "bg-sky-600",
    description: "Customer order intake, scheduling, and batch release.",
  },
  floor_supervisor: {
    label: "Shop Floor Supervisor",
    shortLabel: "Floor Supervisor",
    badgeClasses: "bg-amber-50 text-amber-800 border-amber-200",
    accentClasses: "bg-amber-600",
    description: "Work-order execution, line routing, and stage handoffs.",
  },
  qa_inspector: {
    label: "Quality Assurance Inspector",
    shortLabel: "QA Inspector",
    badgeClasses: "bg-emerald-50 text-emerald-700 border-emerald-200",
    accentClasses: "bg-emerald-600",
    description: "In-process checks, non-conformance holds, and release sign-off.",
  },
  auditor: {
    label: "Compliance Auditor",
    shortLabel: "Auditor",
    badgeClasses: "bg-slate-100 text-slate-800 border-slate-300",
    accentClasses: "bg-slate-700",
    description: "Read-only end-to-end traceability and immutable audit trail.",
  },
  owner: {
    label: "Factory Owner",
    shortLabel: "Owner",
    badgeClasses: "bg-purple-50 text-purple-800 border-purple-200",
    accentClasses: "bg-purple-700",
    description: "Executive read-only oversight across KPIs, margins, GST, and receivables.",
  },
};

export function hasPermission(user: UserProfile | null, permission: string): boolean {
  if (!user) return false;
  return user.permissions.includes(permission);
}

export function formatRoleLabel(role: string): string {
  return ROLE_META[role as Role]?.label ?? role;
}
