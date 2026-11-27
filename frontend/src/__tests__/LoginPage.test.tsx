import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { AuthProvider } from "../context/AuthContext";
import { AppRoutes } from "../App";
import { api, ApiError } from "../lib/api";

describe("LoginPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders login form and authenticates user to role dashboard", async () => {
    const user = userEvent.setup();
    vi.spyOn(api, "login").mockResolvedValue({
      access_token: "jwt-token-123",
      token_type: "bearer",
      expires_in: 3600,
      user: {
        id: "u-1",
        email: "orders@factoryflow.io",
        full_name: "Marcus Chen",
        department: "Planning & Orders",
        role: "order_manager",
        role_display_name: "Order & Production Manager",
        is_active: true,
        permissions: [
          "dashboard:view",
          "orders:manage",
          "orders:read",
          "production:read",
          "roles:read",
        ],
        created_at: new Date().toISOString(),
        last_login_at: null,
      },
    });
    vi.spyOn(api, "dashboard").mockResolvedValue({
      role: "order_manager",
      role_display_name: "Order & Production Manager",
      department: "Planning & Orders",
      database_connected: true,
      stats: [
        { key: "planners", label: "Order Managers", value: "1", caption: "Active" },
      ],
      modules: [],
      role_distribution: { order_manager: 1 },
      recent_activity: [],
      permissions: ["dashboard:view", "orders:read", "orders:manage", "production:read", "roles:read"],
    });
    vi.spyOn(api, "workspaceCheck").mockImplementation(async (ws) => ({
      workspace: ws,
      role: "order_manager",
      can_manage: ws === "orders",
      phase: "phase_1_rbac_verified",
    }));

    render(
      <MemoryRouter initialEntries={["/login"]}>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </MemoryRouter>
    );

    await user.type(screen.getByLabelText(/work email/i), "orders@factoryflow.io");
    await user.type(screen.getByLabelText(/password/i), "FactoryFlow!2026");
    await user.click(screen.getByRole("button", { name: /^sign in$/i }));

    await waitFor(() => {
      expect(screen.getByTestId("dashboard-order_manager")).toBeInTheDocument();
    });
  });

  it("displays API error message when credentials are invalid", async () => {
    const user = userEvent.setup();
    vi.spyOn(api, "login").mockRejectedValue(
      new ApiError(401, "Invalid email or password.")
    );

    render(
      <MemoryRouter initialEntries={["/login"]}>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </MemoryRouter>
    );

    await user.type(screen.getByLabelText(/work email/i), "bad@factoryflow.io");
    await user.type(screen.getByLabelText(/password/i), "wrongpass");
    await user.click(screen.getByRole("button", { name: /^sign in$/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Invalid email or password."
    );
  });
});
