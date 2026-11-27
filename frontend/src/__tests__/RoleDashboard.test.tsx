import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AppRoutes } from "../App";
import { AuthProvider } from "../context/AuthContext";
import { api, setStoredToken } from "../lib/api";
import { Role, UserProfile } from "../types/auth";

function buildUser(role: Role, permissions: string[]): UserProfile {
  return {
    id: `user-${role}`,
    email: `${role}@factoryflow.io`,
    full_name: `Test ${role}`,
    department: "Operations",
    role,
    role_display_name: role,
    is_active: true,
    permissions,
    created_at: new Date().toISOString(),
    last_login_at: null,
  };
}

describe("Role-based dashboards & route guards", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it.each<[Role, string[]]>([
    ["admin", ["dashboard:view", "roles:read", "users:read", "users:manage", "audit:read", "orders:read", "production:read", "qa:read"]],
    ["order_manager", ["dashboard:view", "roles:read", "orders:read", "orders:manage", "production:read"]],
    ["floor_supervisor", ["dashboard:view", "roles:read", "orders:read", "production:read", "production:manage", "qa:read"]],
    ["qa_inspector", ["dashboard:view", "roles:read", "orders:read", "production:read", "qa:read", "qa:manage"]],
    ["auditor", ["dashboard:view", "roles:read", "audit:read", "orders:read", "production:read", "qa:read"]],
  ])("renders dedicated dashboard layout for %s", async (role, permissions) => {
    setStoredToken("valid-jwt");
    vi.spyOn(api, "me").mockResolvedValue(buildUser(role, permissions));
    vi.spyOn(api, "dashboard").mockResolvedValue({
      role,
      role_display_name: role,
      department: "Operations",
      database_connected: true,
      stats: [{ key: "s1", label: "Status", value: "OK", caption: "Verified" }],
      modules: [],
      role_distribution: { [role]: 1 },
      recent_activity: [],
      permissions,
    });
    vi.spyOn(api, "workspaceCheck").mockImplementation(async (ws) => ({
      workspace: ws,
      role,
      can_manage: false,
      phase: "phase_1_rbac_verified",
    }));

    render(
      <MemoryRouter initialEntries={["/dashboard"]}>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByTestId(`dashboard-${role}`)).toBeInTheDocument();
    });
  });

  it("blocks non-admin user from /users route", async () => {
    setStoredToken("valid-jwt");
    vi.spyOn(api, "me").mockResolvedValue(
      buildUser("qa_inspector", ["dashboard:view", "roles:read", "qa:read", "qa:manage"])
    );

    render(
      <MemoryRouter initialEntries={["/users"]}>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </MemoryRouter>
    );

    expect(
      await screen.findByText(/access restricted by role policy/i)
    ).toBeInTheDocument();
  });
});
