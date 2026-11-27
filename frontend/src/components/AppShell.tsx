import React, { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import {
  AlertTriangle,
  BarChart3,
  Boxes,
  Building2,
  ClipboardCheck,
  ClipboardList,
  CloudOff,
  CreditCard,
  Database,
  Factory,
  FileSpreadsheet,
  History,
  IndianRupee,
  KeyRound,
  Layers,
  LayoutDashboard,
  LogOut,
  Package,
  PlayCircle,
  PlusCircle,
  Receipt,
  RefreshCw,
  Ruler,
  Scale,
  ScrollText,
  ShieldCheck,
  ShoppingBag,
  ShoppingCart,
  SlidersHorizontal,
  Truck,
  Users,
  Users2,
  Wallet,
  Warehouse,
  X,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { api, ApiError } from "../lib/api";
import { hasPermission } from "../lib/permissions";
import { NetworkStatusBanner } from "./NetworkStatusBanner";
import { RoleBadge } from "./RoleBadge";

interface NavItem {
  to: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  permission: string;
}

const CORE_NAV_ITEMS: NavItem[] = [
  { to: "/dashboard", label: "Role Workspace", icon: LayoutDashboard, permission: "dashboard:view" },
  { to: "/users", label: "Users & Roles", icon: Users, permission: "users:read" },
  { to: "/audit-logs", label: "Audit Trail", icon: ScrollText, permission: "audit:read" },
  { to: "/permissions", label: "RBAC Matrix", icon: ShieldCheck, permission: "roles:read" },
];

const INVENTORY_PURCHASE_NAV_ITEMS: NavItem[] = [
  { to: "/inventory", label: "Inventory Overview", icon: Warehouse, permission: "inventory:read" },
  { to: "/inventory/raw-materials", label: "Raw Stock", icon: Boxes, permission: "inventory:read" },
  { to: "/inventory/packaging", label: "Packaging Stock", icon: Package, permission: "inventory:read" },
  { to: "/inventory/finished-goods", label: "Finished Stock", icon: ShoppingBag, permission: "inventory:read" },
  { to: "/inventory/ledger", label: "Stock Ledger", icon: ClipboardCheck, permission: "inventory:read" },
  { to: "/inventory/adjustments", label: "Stock Adjustments", icon: SlidersHorizontal, permission: "inventory:read" },
  { to: "/inventory/alerts", label: "Low Stock Alerts", icon: AlertTriangle, permission: "inventory:read" },
  { to: "/purchases", label: "Purchases", icon: Receipt, permission: "purchases:read" },
];

const PRODUCTION_NAV_ITEMS: NavItem[] = [
  { to: "/production", label: "Production Hub", icon: PlayCircle, permission: "production_runs:read" },
  { to: "/production/runs", label: "Production Runs", icon: ClipboardList, permission: "production_runs:read" },
  { to: "/production/variance", label: "Variance Report", icon: BarChart3, permission: "production_runs:read" },
  { to: "/boms", label: "BOMs", icon: Layers, permission: "bom:read" },
];

const SALES_BILLING_NAV_ITEMS: NavItem[] = [
  { to: "/sales/dashboard", label: "Sales Dashboard", icon: ShoppingCart, permission: "sales_orders:read" },
  { to: "/sales/mobile-order", label: "Mobile Order", icon: PlusCircle, permission: "sales_orders:create" },
  { to: "/sales/offline-order", label: "Offline Order (PWA)", icon: CloudOff, permission: "sales_orders:create" },
  { to: "/sales/pending-sync", label: "Pending Sync Queue", icon: RefreshCw, permission: "sales_orders:create" },
  { to: "/sales/failed-orders", label: "Failed & Conflicts", icon: AlertTriangle, permission: "sales_orders:create" },
  { to: "/sales/sync-history", label: "Sync History", icon: History, permission: "sales_orders:create" },
  { to: "/sales/my-orders", label: "My Orders", icon: ClipboardList, permission: "sales_orders:read" },
  { to: "/sales/customers", label: "Customer Sales", icon: Users2, permission: "sales_orders:read" },
  { to: "/sales/admin", label: "Order Approval Queue", icon: ShieldCheck, permission: "sales_orders:approve" },
  { to: "/invoices", label: "GST Invoices", icon: FileSpreadsheet, permission: "invoices:read" },
  { to: "/dispatches", label: "Dispatches", icon: Truck, permission: "dispatches:read" },
];

const COSTING_PAYMENT_NAV_ITEMS: NavItem[] = [
  { to: "/costing", label: "Costing Dashboard", icon: IndianRupee, permission: "costing:read" },
  { to: "/costing/expenses", label: "Run Expenses", icon: Receipt, permission: "costing:read" },
  { to: "/payments", label: "Payment Dashboard", icon: Wallet, permission: "payments:read" },
  { to: "/payments/history", label: "Payment History", icon: CreditCard, permission: "payments:read" },
  { to: "/receivables", label: "Receivables", icon: BarChart3, permission: "receivables:read" },
  { to: "/receivables/ageing", label: "Ageing Report", icon: ClipboardCheck, permission: "receivables:read" },
];

const REPORTS_AUDIT_NAV_ITEMS: NavItem[] = [
  { to: "/owner", label: "Owner Dashboard", icon: BarChart3, permission: "owner_dashboard:view" },
  { to: "/auditor", label: "Auditor Portal", icon: ShieldCheck, permission: "reports:view" },
  { to: "/reports/sales", label: "Sales Register", icon: FileSpreadsheet, permission: "reports:view" },
  { to: "/reports/gst", label: "GST Summary", icon: Receipt, permission: "reports:view" },
  { to: "/reports/purchases", label: "Purchase Register", icon: ClipboardList, permission: "reports:view" },
  { to: "/reports/stock/raw-materials", label: "Stock Reports", icon: Warehouse, permission: "reports:view" },
  { to: "/reports/stock/ledger", label: "Stock Ledger Report", icon: ClipboardCheck, permission: "reports:view" },
  { to: "/reports/production", label: "Production Register", icon: Factory, permission: "reports:view" },
  { to: "/reports/payments", label: "Payment & Ageing Audit", icon: Wallet, permission: "reports:view" },
  { to: "/reports/exports", label: "Report Export Center", icon: ScrollText, permission: "reports:export" },
];

const MASTER_DATA_NAV_ITEMS: NavItem[] = [
  { to: "/master-data", label: "Master Data Hub", icon: Database, permission: "dashboard:view" },
  { to: "/products", label: "Products", icon: ShoppingBag, permission: "products:read" },
  { to: "/raw-materials", label: "Raw Materials", icon: Boxes, permission: "stock_items:read" },
  { to: "/packaging-materials", label: "Packaging", icon: Package, permission: "stock_items:read" },
  { to: "/suppliers", label: "Suppliers", icon: Building2, permission: "suppliers:read" },
  { to: "/customers", label: "Customers", icon: Users2, permission: "customers:read" },
  { to: "/units", label: "Units", icon: Ruler, permission: "units:read" },
  { to: "/unit-conversions", label: "Unit Conversions", icon: Scale, permission: "units:read" },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  const [passwordModalOpen, setPasswordModalOpen] = useState(false);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [passwordMessage, setPasswordMessage] = useState<string | null>(null);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [savingPassword, setSavingPassword] = useState(false);

  if (!user) return null;

  const visibleCoreNav = CORE_NAV_ITEMS.filter((item) => hasPermission(user, item.permission));
  const visibleInvNav = INVENTORY_PURCHASE_NAV_ITEMS.filter((item) =>
    hasPermission(user, item.permission)
  );
  const visibleProdNav = PRODUCTION_NAV_ITEMS.filter((item) =>
    hasPermission(user, item.permission)
  );
  const visibleSalesNav = SALES_BILLING_NAV_ITEMS.filter((item) =>
    hasPermission(user, item.permission)
  );
  const visibleCostingPayNav = COSTING_PAYMENT_NAV_ITEMS.filter((item) =>
    hasPermission(user, item.permission)
  );
  const visibleReportsNav = REPORTS_AUDIT_NAV_ITEMS.filter((item) =>
    hasPermission(user, item.permission)
  );
  const visibleMasterNav = MASTER_DATA_NAV_ITEMS.filter((item) =>
    hasPermission(user, item.permission)
  );

  const handleLogout = async () => {
    await logout();
    navigate("/login", { replace: true });
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setPasswordError(null);
    setPasswordMessage(null);
    setSavingPassword(true);
    try {
      const res = await api.changePassword(currentPassword, newPassword);
      setPasswordMessage(res.message);
      setCurrentPassword("");
      setNewPassword("");
    } catch (err) {
      setPasswordError(err instanceof ApiError ? err.message : "Failed to update password.");
    } finally {
      setSavingPassword(false);
    }
  };

  const renderNavSection = (title: string, items: NavItem[]) => {
    if (items.length === 0) return null;
    return (
      <div className="space-y-1">
        <div className="px-3 pt-2 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
          {title}
        </div>
        {items.map((item) => {
          const Icon = item.icon;
          const active =
            location.pathname === item.to ||
            (item.to !== "/dashboard" &&
              item.to !== "/master-data" &&
              item.to !== "/inventory" &&
              location.pathname.startsWith(`${item.to}/`));
          return (
            <Link
              key={item.to}
              to={item.to}
              className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                active
                  ? "bg-slate-800 text-white"
                  : "text-slate-300 hover:bg-slate-900 hover:text-white"
              }`}
            >
              <Icon className="h-4 w-4 shrink-0" />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 lg:flex">
      <aside className="flex w-full flex-col justify-between border-b border-slate-800 bg-slate-950 text-slate-100 lg:min-h-screen lg:w-64 lg:border-b-0 lg:border-r">
        <div>
          <div className="flex items-center gap-3 border-b border-slate-800 px-5 py-4">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-sky-500/15 text-sky-400 ring-1 ring-sky-500/30">
              <Factory className="h-5 w-5" />
            </div>
            <div>
              <div className="text-sm font-semibold tracking-tight text-white">FactoryFlow</div>
              <div className="text-[11px] uppercase tracking-wider text-slate-400">
                Order-to-Audit
              </div>
            </div>
          </div>

          <nav className="space-y-3 p-3" aria-label="Primary navigation">
            {renderNavSection("Platform", visibleCoreNav)}
            {renderNavSection("Owner & Audit Reports", visibleReportsNav)}
            {renderNavSection("Sales & GST Billing", visibleSalesNav)}
            {renderNavSection("Costing & Payments", visibleCostingPayNav)}
            {renderNavSection("Production & BOM", visibleProdNav)}
            {renderNavSection("Inventory & Purchases", visibleInvNav)}
            {renderNavSection("Master Data", visibleMasterNav)}
          </nav>
        </div>

        <div className="border-t border-slate-800 p-4">
          <div className="mb-3 rounded-lg bg-slate-900/90 p-3">
            <div className="text-xs font-medium text-white">{user.full_name}</div>
            <div className="truncate text-[11px] text-slate-400">{user.email}</div>
            <div className="mt-2">
              <RoleBadge role={user.role} />
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => {
                setPasswordMessage(null);
                setPasswordError(null);
                setPasswordModalOpen(true);
              }}
              className="flex flex-1 items-center justify-center gap-1.5 rounded-md border border-slate-700 px-2.5 py-1.5 text-xs font-medium text-slate-200 hover:bg-slate-800"
            >
              <KeyRound className="h-3.5 w-3.5" /> Password
            </button>
            <button
              type="button"
              onClick={handleLogout}
              className="flex flex-1 items-center justify-center gap-1.5 rounded-md border border-slate-700 px-2.5 py-1.5 text-xs font-medium text-slate-200 hover:bg-rose-950/60 hover:text-rose-200"
            >
              <LogOut className="h-3.5 w-3.5" /> Sign out
            </button>
          </div>
        </div>
      </aside>

      <div className="flex-1">
        <header className="border-b border-slate-200 bg-white px-6 py-4">
          <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-xs font-medium uppercase tracking-wider text-slate-500">
                {user.department}
              </p>
              <h1 className="text-lg font-semibold text-slate-900">
                {user.role_display_name} Console
              </h1>
            </div>
            <div className="flex flex-wrap items-center gap-3 text-xs text-slate-600">
              <NetworkStatusBanner />
              <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1 font-medium text-emerald-700">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                RBAC Verified
              </span>
              <span className="hidden sm:inline text-slate-400">|</span>
              <span className="hidden sm:inline font-mono text-[11px] text-slate-500">
                {user.permissions.length} permissions active
              </span>
            </div>
          </div>
        </header>

        <main className="mx-auto max-w-7xl p-6">{children}</main>
      </div>

      {passwordModalOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="password-modal-title"
        >
          <div className="w-full max-w-md rounded-xl border border-slate-200 bg-white p-6 shadow-xl">
            <div className="mb-4 flex items-center justify-between">
              <h2 id="password-modal-title" className="text-base font-semibold text-slate-900">
                Change Account Password
              </h2>
              <button
                type="button"
                onClick={() => setPasswordModalOpen(false)}
                className="rounded-md p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
                aria-label="Close modal"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <form onSubmit={handleChangePassword} className="space-y-4">
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-700">
                  Current Password
                </label>
                <input
                  type="password"
                  required
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                />
              </div>

              <div>
                <label className="mb-1 block text-xs font-medium text-slate-700">
                  New Password (min 8 characters)
                </label>
                <input
                  type="password"
                  required
                  minLength={8}
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                />
              </div>

              {passwordError && (
                <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-700">
                  {passwordError}
                </div>
              )}

              {passwordMessage && (
                <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs text-emerald-700">
                  {passwordMessage}
                </div>
              )}

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setPasswordModalOpen(false)}
                  className="rounded-lg border border-slate-300 px-3.5 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={savingPassword}
                  className="rounded-lg bg-slate-900 px-4 py-2 text-xs font-semibold text-white hover:bg-slate-800 disabled:opacity-50"
                >
                  {savingPassword ? "Updating..." : "Update Password"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
