import { useEffect, useState } from "react";
import { AlertCircle, RefreshCw } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { api, ApiError } from "../lib/api";
import { hasPermission } from "../lib/permissions";
import { RoleDashboardResponse, WorkspaceCheckResponse } from "../types/dashboard";
import { AdminDashboard } from "../components/dashboards/AdminDashboard";
import { AuditorDashboard } from "../components/dashboards/AuditorDashboard";
import { FloorSupervisorDashboard } from "../components/dashboards/FloorSupervisorDashboard";
import { OrderManagerDashboard } from "../components/dashboards/OrderManagerDashboard";
import { QaInspectorDashboard } from "../components/dashboards/QaInspectorDashboard";

export function DashboardPage() {
  const { user } = useAuth();
  const [data, setData] = useState<RoleDashboardResponse | null>(null);
  const [checks, setChecks] = useState<WorkspaceCheckResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadDashboard = async () => {
    if (!user) return;
    setLoading(true);
    setError(null);
    try {
      const workspacePromises: Promise<WorkspaceCheckResponse>[] = [];
      if (hasPermission(user, "orders:read")) {
        workspacePromises.push(api.workspaceCheck("orders"));
      }
      if (hasPermission(user, "production:read")) {
        workspacePromises.push(api.workspaceCheck("production"));
      }
      if (hasPermission(user, "qa:read")) {
        workspacePromises.push(api.workspaceCheck("qa"));
      }

      const [dashboardData, ...workspaceResults] = await Promise.all([
        api.dashboard(),
        ...workspacePromises,
      ]);

      setData(dashboardData);
      setChecks(workspaceResults);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Failed to load role dashboard."
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadDashboard();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user?.id, user?.role]);

  if (loading) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-10 text-center text-sm text-slate-600 shadow-sm">
        Loading live role workspace...
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="rounded-xl border border-rose-200 bg-rose-50 p-6 text-sm text-rose-700">
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <AlertCircle className="h-4 w-4" />
            <span>{error ?? "Unable to load dashboard."}</span>
          </div>
          <button
            type="button"
            onClick={() => void loadDashboard()}
            className="inline-flex items-center gap-1.5 rounded-lg border border-rose-300 bg-white px-3 py-1.5 text-xs font-medium text-rose-700 hover:bg-rose-50"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            Retry
          </button>
        </div>
      </div>
    );
  }

  switch (data.role) {
    case "admin":
      return <AdminDashboard data={data} />;
    case "order_manager":
      return <OrderManagerDashboard data={data} checks={checks} />;
    case "floor_supervisor":
      return <FloorSupervisorDashboard data={data} checks={checks} />;
    case "qa_inspector":
      return <QaInspectorDashboard data={data} checks={checks} />;
    case "auditor":
      return <AuditorDashboard data={data} checks={checks} />;
    default:
      return null;
  }
}
