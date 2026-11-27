import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AppRoutes } from "../App";
import { AuthProvider } from "../context/AuthContext";
import { api, setStoredToken } from "../lib/api";

describe("Phase 6 Costing & Payment Pages", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    setStoredToken("valid-admin-jwt");
    vi.spyOn(api, "me").mockResolvedValue({
      id: "admin-1",
      email: "admin@factoryflow.io",
      full_name: "System Administrator",
      department: "Platform & Governance",
      role: "admin",
      role_display_name: "System Administrator",
      is_active: true,
      permissions: [
        "dashboard:view",
        "roles:read",
        "costing:read",
        "expenses:manage",
        "payments:read",
        "payments:manage",
        "receivables:read",
      ],
      created_at: new Date().toISOString(),
      last_login_at: null,
    });
  });

  it("renders Production Costing Dashboard with benchmark Rs 5,855 total cost and 37.71% margin", async () => {
    vi.spyOn(api, "productionCostDashboard").mockResolvedValue({
      total_runs_costed: 1,
      total_good_output: "188.000000",
      total_raw_material_cost: "3435.00",
      total_packaging_cost: "620.00",
      total_labour_cost: "1200.00",
      total_gas_and_power_cost: "600.00",
      total_other_overhead_cost: "0.00",
      total_production_cost: "5855.00",
      avg_cost_per_packet: "31.14",
      avg_gross_margin_pct: "37.71",
      products: [],
      runs: [
        {
          production_run_id: "run-1",
          order_number: "PRD-P6-BASE",
          batch_number: "B-P6",
          product_id: "prod-1",
          product_name: "Murukku 200 g",
          product_sku: "MUR-200",
          production_date: "2026-11-01",
          status: "POSTED",
          actual_good_output: "188.000000",
          unit_symbol: "packet",
          raw_material_cost: "3435.00",
          packaging_cost: "620.00",
          material_and_packaging_cost: "4055.00",
          labour_cost: "1200.00",
          gas_and_power_cost: "600.00",
          other_overhead_cost: "0.00",
          total_overhead_cost: "1800.00",
          total_production_cost: "5855.00",
          cost_per_packet_exact: "31.143617",
          cost_per_packet_display: "31.14",
          selling_price_before_gst: "50.00",
          gross_profit_per_packet: "18.86",
          gross_margin_pct: "37.71",
          materials: [],
          expenses: [],
        },
      ],
    });

    render(
      <MemoryRouter initialEntries={["/costing"]}>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </MemoryRouter>
    );

    expect(
      await screen.findByRole("heading", { name: "Production Costing Dashboard" })
    ).toBeInTheDocument();
    expect(await screen.findByText("PRD-P6-BASE")).toBeInTheDocument();
    expect(screen.getAllByText("Rs 31.14").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("37.71%").length).toBeGreaterThanOrEqual(1);
  });

  it("renders Payment Dashboard with Retailer A partial payment & Rs 3,875 outstanding", async () => {
    vi.spyOn(api, "receivablesReport").mockResolvedValue({
      total_invoiced: "7875.00",
      total_collected: "4000.00",
      total_unallocated_advances: "0.00",
      total_outstanding: "3875.00",
      default_payment_term_days: 30,
      customers: [],
      invoices: [],
    });
    vi.spyOn(api, "listPayments").mockResolvedValue({
      items: [
        {
          id: "pay-1",
          payment_reference: "PAY-BENCH-001",
          customer_id: "cust-a",
          customer_name: "Retailer A",
          payment_date: "2026-11-10",
          payment_method: "UPI",
          amount_received: "4000.00",
          allocated_amount: "4000.00",
          unallocated_advance: "0.00",
          transaction_reference: "UTR-RET-A-4000",
          notes: null,
          status: "POSTED",
          recorded_by_email: "admin@factoryflow.io",
          created_at: new Date().toISOString(),
          allocations: [],
        },
      ],
      total: 1,
      page: 1,
      page_size: 8,
    });

    render(
      <MemoryRouter initialEntries={["/payments"]}>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </MemoryRouter>
    );

    expect(await screen.findByText("PAY-BENCH-001")).toBeInTheDocument();
    expect(screen.getByText("Rs 3875.00")).toBeInTheDocument();
  });
});
