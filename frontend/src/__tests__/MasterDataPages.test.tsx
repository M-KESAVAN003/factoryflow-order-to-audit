import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AppRoutes } from "../App";
import { AuthProvider } from "../context/AuthContext";
import { api, setStoredToken } from "../lib/api";

describe("Phase 2 Master Data Pages", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    setStoredToken("valid-admin-jwt");
    vi.spyOn(api, "me").mockResolvedValue({
      id: "admin-1",
      email: "admin@factoryflow.io",
      full_name: "Elena Vance",
      department: "Platform & Governance",
      role: "admin",
      role_display_name: "System Administrator",
      is_active: true,
      permissions: [
        "dashboard:view",
        "roles:read",
        "products:read",
        "products:manage",
        "stock_items:read",
        "stock_items:manage",
        "suppliers:read",
        "suppliers:manage",
        "customers:read",
        "customers:manage",
        "units:read",
        "units:manage",
      ],
      created_at: new Date().toISOString(),
      last_login_at: null,
    });
  });

  it("renders Master Data Hub with live summary counts", async () => {
    vi.spyOn(api, "masterDataSummary").mockResolvedValue({
      products_total: 1,
      products_active: 1,
      raw_materials_total: 3,
      packaging_materials_total: 2,
      suppliers_total: 1,
      customers_total: 2,
      units_total: 7,
      conversions_total: 3,
    });

    render(
      <MemoryRouter initialEntries={["/master-data"]}>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </MemoryRouter>
    );

    expect(await screen.findByText("Master Data Management")).toBeInTheDocument();
    expect(await screen.findByText("Finished Products")).toBeInTheDocument();
    expect(screen.getByText("1 active SKUs")).toBeInTheDocument();
  });

  it("renders Products page with benchmark Murukku 200 g", async () => {
    vi.spyOn(api, "listProducts").mockResolvedValue({
      items: [
        {
          id: "prod-1",
          name: "Murukku 200 g",
          sku: "MUR-200",
          category: "Savory Snacks",
          description: "Crispy snack",
          pack_size: "200 g",
          selling_price: "50.00",
          gst_rate: "5.00",
          hsn_code: "19059090",
          unit_id: "u-pkt",
          unit_symbol: "packet",
          stock_item_id: "si-1",
          stock_item_sku: "MUR-200",
          stock_item_type: "FINISHED_GOOD",
          pouch_stock_item_id: null,
          pouch_stock_item_name: null,
          carton_stock_item_id: null,
          carton_stock_item_name: null,
          packets_per_carton: 20,
          is_active: true,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
      ],
      total: 1,
      page: 1,
      page_size: 10,
    });

    render(
      <MemoryRouter initialEntries={["/products"]}>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("Murukku 200 g")).toBeInTheDocument();
      expect(screen.getByText("MUR-200")).toBeInTheDocument();
      expect(screen.getByText("20 pkts/carton")).toBeInTheDocument();
    });
  });

  it("renders Unit Conversions page with live rules", async () => {
    vi.spyOn(api, "listUnitConversions").mockResolvedValue({
      items: [
        {
          id: "conv-1",
          from_unit_id: "u-kg",
          from_unit_symbol: "kg",
          from_unit_dimension: "mass",
          to_unit_id: "u-g",
          to_unit_symbol: "g",
          to_unit_dimension: "mass",
          product_id: null,
          product_name: null,
          conversion_factor: "1000.000000",
          is_active: true,
          created_at: new Date().toISOString(),
        },
      ],
      total: 1,
      page: 1,
      page_size: 100,
    });
    vi.spyOn(api, "listUnits").mockResolvedValue({
      items: [
        {
          id: "u-kg",
          name: "Kilogram",
          symbol: "kg",
          dimension: "mass",
          is_base: true,
          is_active: true,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
        {
          id: "u-g",
          name: "Gram",
          symbol: "g",
          dimension: "mass",
          is_base: false,
          is_active: true,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
      ],
      total: 2,
      page: 1,
      page_size: 100,
    });
    vi.spyOn(api, "listProducts").mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 100,
    });

    render(
      <MemoryRouter initialEntries={["/unit-conversions"]}>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </MemoryRouter>
    );

    expect(await screen.findByText("1 kg = 1000 g")).toBeInTheDocument();
  });
});
