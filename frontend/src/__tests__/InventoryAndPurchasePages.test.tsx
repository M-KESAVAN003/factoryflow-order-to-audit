import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AppRoutes } from "../App";
import { AuthProvider } from "../context/AuthContext";
import { api, setStoredToken } from "../lib/api";

describe("Phase 3 Inventory & Purchase Pages", () => {
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
        "inventory:read",
        "inventory:manage",
        "purchases:read",
        "purchases:manage",
        "products:read",
        "stock_items:read",
        "suppliers:read",
        "units:read",
      ],
      created_at: new Date().toISOString(),
      last_login_at: null,
    });
  });

  it("renders Inventory Overview with benchmark valuation and reconciliation", async () => {
    vi.spyOn(api, "inventorySummary").mockResolvedValue({
      total_items: 6,
      total_stock_value: "14250.0000",
      low_stock_red_count: 0,
      approaching_orange_count: 0,
      categories: [
        {
          item_type: "RAW_MATERIAL",
          label: "Raw Materials",
          item_count: 3,
          total_quantity: "195.000000",
          total_value: "12100.0000",
          low_stock_count: 0,
        },
      ],
      recent_movements: [],
    });
    vi.spyOn(api, "reconcileInventory").mockResolvedValue({
      all_reconciled: true,
      checked_items: 6,
      items: [],
    });

    render(
      <MemoryRouter initialEntries={["/inventory"]}>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </MemoryRouter>
    );

    expect(
      await screen.findByRole("heading", { name: "Inventory Overview" })
    ).toBeInTheDocument();
    expect(await screen.findByText("100% Reconciled")).toBeInTheDocument();
    expect(screen.getByText("3 SKUs")).toBeInTheDocument();
  });

  it("renders Purchase Register with BENCHMARK-FLOUR-001", async () => {
    vi.spyOn(api, "listPurchases").mockResolvedValue({
      items: [
        {
          id: "pur-1",
          reference_number: "BENCHMARK-FLOUR-001",
          supplier_id: "sup-1",
          supplier_name: "Benchmark Supplier",
          purchase_date: "2026-11-26",
          status: "POSTED",
          payment_status: "PAID",
          subtotal: "2700.0000",
          tax_amount: "0.0000",
          total_amount: "2700.0000",
          notes: "Benchmark flour purchase",
          created_by: "admin-1",
          created_by_email: "admin@factoryflow.io",
          posted_by: "admin-1",
          posted_at: new Date().toISOString(),
          cancelled_at: null,
          cancel_reason: null,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          items: [
            {
              id: "pi-1",
              stock_item_id: "si-flour",
              stock_item_name: "Flour",
              stock_item_sku: "RM-FLOUR",
              unit_id: "u-kg",
              unit_symbol: "kg",
              base_unit_symbol: "kg",
              quantity: "60.000000",
              base_quantity: "60.000000",
              unit_rate: "45.000000",
              tax_rate: "0.00",
              tax_amount: "0.0000",
              line_subtotal: "2700.0000",
              line_total: "2700.0000",
            },
          ],
        },
      ],
      total: 1,
      page: 1,
      page_size: 15,
    });
    vi.spyOn(api, "listSuppliers").mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 100,
    });

    render(
      <MemoryRouter initialEntries={["/purchases"]}>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("BENCHMARK-FLOUR-001")).toBeInTheDocument();
      expect(screen.getByText("Benchmark Supplier")).toBeInTheDocument();
      expect(screen.getByText("POSTED")).toBeInTheDocument();
    });
  });
});
