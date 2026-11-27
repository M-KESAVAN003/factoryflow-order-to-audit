import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AppRoutes } from "../App";
import { AuthProvider } from "../context/AuthContext";
import { api, setStoredToken } from "../lib/api";

describe("Phase 4 BOM & Production Pages", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    setStoredToken("valid-supervisor-jwt");
    vi.spyOn(api, "me").mockResolvedValue({
      id: "sup-1",
      email: "floor@factoryflow.io",
      full_name: "Devon Brooks",
      department: "Manufacturing Operations",
      role: "floor_supervisor",
      role_display_name: "Shop Floor Supervisor",
      is_active: true,
      permissions: [
        "dashboard:view",
        "roles:read",
        "bom:read",
        "production_runs:read",
        "production_runs:manage",
        "inventory:read",
      ],
      created_at: new Date().toISOString(),
      last_login_at: null,
    });
  });

  it("renders Production Dashboard with live yield variance and benchmark run", async () => {
    vi.spyOn(api, "productionDashboard").mockResolvedValue({
      todays_runs: 1,
      planned_output: "200.000000",
      actual_output: "188.000000",
      total_wastage: "6.000000",
      overall_yield_variance_pct: "-6.0000",
      pending_runs: 0,
      active_boms: 1,
      daily_trend: [
        {
          date: "2026-11-26",
          planned_output: "200",
          actual_output: "188",
          wastage: "6",
        },
      ],
      product_yield: [
        {
          product_name: "Murukku 200 g",
          runs_count: 1,
          expected_output: "200",
          actual_output: "188",
          yield_pct: "94.0000",
        },
      ],
      recent_runs: [],
      variance_alerts: [
        {
          production_run_id: "run-1",
          order_number: "BENCHMARK-PRD-001",
          product_name: "Murukku 200 g",
          production_date: "2026-11-26",
          status: "POSTED",
          expected_output: "200",
          actual_good_output: "188",
          yield_variance_pct: "-6.0000",
          yield_status: "RED",
          flagged_material_count: 2,
        },
      ],
    });
    vi.spyOn(api, "listBoms").mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 10,
    });
    vi.spyOn(api, "inventoryRawMaterials").mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 10,
    });

    render(
      <MemoryRouter initialEntries={["/production"]}>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </MemoryRouter>
    );

    expect(
      await screen.findByRole("heading", { name: "Production Dashboard" })
    ).toBeInTheDocument();
    expect(await screen.findByText("BENCHMARK-PRD-001")).toBeInTheDocument();
    expect(screen.getByText("-6.00%")).toBeInTheDocument();
  });

  it("renders BOM List with Murukku 200 g benchmark BOM", async () => {
    vi.spyOn(api, "listBoms").mockResolvedValue({
      items: [
        {
          id: "bom-1",
          product_id: "prod-1",
          product_name: "Murukku 200 g",
          product_sku: "MUR-200",
          version_number: 1,
          batch_size: "1.000000",
          expected_output: "200.000000",
          output_unit_id: "u-pkt",
          output_unit_symbol: "packet",
          effective_date: "2026-11-26",
          status: "ACTIVE",
          is_active: true,
          notes: "Benchmark",
          created_by_email: "admin@factoryflow.io",
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          lines: [],
        },
      ],
      total: 1,
      page: 1,
      page_size: 15,
    });

    render(
      <MemoryRouter initialEntries={["/boms"]}>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("Murukku 200 g")).toBeInTheDocument();
      expect(screen.getByText("v1")).toBeInTheDocument();
      expect(screen.getByText("200 packet / batch")).toBeInTheDocument();
    });
  });
});
