import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AppRoutes } from "../App";
import { AuthProvider } from "../context/AuthContext";
import { api, setStoredToken } from "../lib/api";

describe("Phase 5 Sales Order & GST Billing Pages", () => {
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
        "sales_orders:read",
        "sales_orders:create",
        "sales_orders:approve",
        "invoices:read",
        "invoices:manage",
        "dispatches:read",
        "dispatches:manage",
        "products:read",
        "customers:read",
      ],
      created_at: new Date().toISOString(),
      last_login_at: null,
    });
  });

  it("renders Mobile Order Entry with live Tamil Nadu CGST+SGST benchmark preview", async () => {
    vi.spyOn(api, "listCustomers").mockResolvedValue({
      items: [
        {
          id: "cust-ret-a",
          name: "Retailer A",
          customer_type: "Retailer",
          gstin: "33RETLA0001A1Z5",
          phone: "+91-44-0000-0201",
          address: "12 Market Road",
          city: "Chennai",
          state: "Tamil Nadu",
          state_code: "33",
          assigned_salesman_id: "sales-1",
          assigned_salesman_name: "Alex Morgan",
          credit_limit: "50000.00",
          is_active: true,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
      ],
      total: 1,
      page: 1,
      page_size: 100,
    });
    vi.spyOn(api, "listProducts").mockResolvedValue({
      items: [
        {
          id: "prod-mur",
          name: "Murukku 200 g",
          sku: "MUR-200",
          category: "Savory Snacks",
          description: "Murukku",
          pack_size: "200 g",
          selling_price: "50.00",
          gst_rate: "5.00",
          hsn_code: "19059090",
          unit_id: "u-pkt",
          unit_symbol: "packet",
          stock_item_id: "si-mur",
          stock_item_sku: "MUR-200",
          stock_item_type: "FINISHED_GOOD",
          pouch_stock_item_id: "si-pouch",
          pouch_stock_item_name: "200 g pouch",
          carton_stock_item_id: "si-carton",
          carton_stock_item_name: "Carton",
          packets_per_carton: 20,
          is_active: true,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
      ],
      total: 1,
      page: 1,
      page_size: 100,
    });

    render(
      <MemoryRouter initialEntries={["/sales/mobile-order"]}>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </MemoryRouter>
    );

    expect(
      await screen.findByRole("heading", { name: "Mobile Order Entry" })
    ).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText("Rs 7500.00")).toBeInTheDocument();
      expect(screen.getAllByText("Rs 187.50").length).toBe(2);
      expect(screen.getByText("Rs 7875.00")).toBeInTheDocument();
    });
  });

  it("renders Admin Order Dashboard with Distributor B shortage alert", async () => {
    vi.spyOn(api, "salesOverview").mockResolvedValue({
      total_orders: 2,
      pending_review: 1,
      awaiting_stock: 1,
      invoiced_count: 1,
      dispatched_count: 1,
      total_sales_value: "14175.00",
      total_gst_collected: "375.00",
      customer_summary: [],
    });
    vi.spyOn(api, "listSalesOrders").mockResolvedValue({
      items: [
        {
          id: "so-dist-b",
          order_number: "SO-BENCH-DIST-B",
          customer_id: "cust-b",
          customer_name: "Distributor B",
          customer_type: "Distributor",
          customer_gstin: "29DISTB0002B1Z5",
          salesman_id: "sales-1",
          salesman_name: "Alex Morgan",
          salesman_email: "orders@factoryflow.io",
          order_date: "2026-11-26",
          status: "AWAITING_STOCK",
          factory_state: "Tamil Nadu",
          customer_state: "Karnataka",
          place_of_supply: "Karnataka (29)",
          tax_type: "INTER_STATE",
          subtotal: "6000.00",
          cgst_amount: "0.00",
          sgst_amount: "0.00",
          igst_amount: "300.00",
          tax_amount: "300.00",
          total_amount: "6300.00",
          has_stock_shortage: true,
          shortage_notes: "Requested 120, available 88, shortage 32",
          notes: null,
          rejection_reason: null,
          invoice_id: null,
          invoice_number: null,
          dispatch_id: null,
          dispatch_number: null,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          items: [
            {
              id: "item-1",
              product_id: "prod-mur",
              product_name: "Murukku 200 g",
              sku: "MUR-200",
              pack_size: "200 g",
              hsn_code: "19059090",
              unit_symbol: "packet",
              requested_quantity: "120",
              approved_quantity: "120",
              dispatched_quantity: "0",
              unit_price: "50.00",
              gst_rate: "5.00",
              taxable_value: "6000.00",
              cgst_rate: "0.00",
              sgst_rate: "0.00",
              igst_rate: "5.00",
              cgst_amount: "0.00",
              sgst_amount: "0.00",
              igst_amount: "300.00",
              line_total: "6300.00",
              available_stock: "88",
              shortage_quantity: "32",
            },
          ],
        },
      ],
      total: 1,
      page: 1,
      page_size: 50,
    });

    render(
      <MemoryRouter initialEntries={["/sales/admin"]}>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </MemoryRouter>
    );

    expect(await screen.findByText("SO-BENCH-DIST-B")).toBeInTheDocument();
    expect(screen.getByText("Distributor B")).toBeInTheDocument();
    expect(screen.getByText("AWAITING_STOCK")).toBeInTheDocument();
    expect(screen.getByText(/Rs 300\.00 \(IGST\)/)).toBeInTheDocument();
  });
});
