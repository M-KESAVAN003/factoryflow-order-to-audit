import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AppRoutes } from "../App";
import { AuthProvider } from "../context/AuthContext";
import { api, setStoredToken } from "../lib/api";

describe("Phase 7 Owner Dashboard & Audit Report Pages", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    setStoredToken("valid-owner-jwt");
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
        "owner_dashboard:view",
        "reports:view",
        "reports:export",
      ],
      created_at: new Date().toISOString(),
      last_login_at: null,
    });
  });

  it("renders Owner Executive Dashboard with benchmark KPIs and charts", async () => {
    vi.spyOn(api, "ownerDashboard").mockResolvedValue({
      date_range: { preset: "last_30_days", date_from: "2026-11-01", date_to: "2026-11-30" },
      todays_orders: 2,
      pending_orders: 1,
      todays_sales: "7875.00",
      monthly_sales: "7875.00",
      monthly_taxable_revenue: "7500.00",
      total_gst_collected: "375.00",
      purchase_value: "2700.00",
      production_output: "188",
      finished_goods_stock: "88",
      raw_material_stock_value: "8665.00",
      total_production_cost: "5855.00",
      average_cost_per_packet: "31.14",
      gross_margin_pct: "37.71",
      total_customer_receivables: "3875.00",
      overdue_receivables: "0.00",
      daily_sales_trend: [{ label: "2026-11-21", value: "7875.00", secondary_value: null }],
      monthly_revenue_trend: [{ label: "2026-11", value: "7500.00", secondary_value: null }],
      product_wise_sales: [{ name: "Murukku 200 g", value: "7500.00", quantity: "150" }],
      customer_wise_sales: [{ name: "Retailer A", value: "7875.00", quantity: null }],
      purchase_vs_sales_trend: [],
      production_planned_vs_actual: [],
      material_consumption_comparison: [],
      production_wastage: [],
      cost_per_packet_trend: [],
      outstanding_receivables_trend: [],
      alerts: [
        {
          severity: "HIGH",
          category: "Insufficient Finished Goods",
          message: "SO-P7-DISTB awaiting stock: shortage 32 packets",
          reference_id: "so-2",
        },
      ],
    });

    render(
      <MemoryRouter initialEntries={["/owner"]}>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </MemoryRouter>
    );

    expect(
      await screen.findByRole("heading", { name: "Owner Executive Dashboard" })
    ).toBeInTheDocument();
    expect((await screen.findAllByText("Rs 7500.00")).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("37.71%")).toBeInTheDocument();
    expect(screen.getByText(/shortage 32 packets/i)).toBeInTheDocument();
  });

  it("renders Sales Register audit report with reconciled status and disclaimer", async () => {
    vi.spyOn(api, "fetchReport").mockResolvedValue({
      date_range: { preset: "last_30_days", date_from: "2026-11-01", date_to: "2026-11-30" },
      total: 1,
      page: 1,
      page_size: 50,
      reconciled_with_invoices: true,
      total_taxable: "7500.00",
      total_cgst: "187.50",
      total_sgst: "187.50",
      total_igst: "0.00",
      total_invoice_value: "7875.00",
      rows: [
        {
          invoice_number: "INV/2026-27/0001",
          invoice_date: "2026-11-21",
          customer_name: "Retailer A",
          customer_gstin: "33RETLA0001A1Z5",
          product_name: "Murukku 200 g",
          hsn_code: "19059090",
          quantity: "150",
          taxable_value: "7500.00",
          cgst: "187.50",
          sgst: "187.50",
          igst: "0.00",
          invoice_total: "7875.00",
          payment_status: "PARTIAL",
        },
      ],
    });

    render(
      <MemoryRouter initialEntries={["/reports/sales"]}>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </MemoryRouter>
    );

    expect(await screen.findByRole("heading", { name: "Sales Register" })).toBeInTheDocument();
    expect(await screen.findByText("INV/2026-27/0001")).toBeInTheDocument();
    expect(screen.getByText("Source Reconciled")).toBeInTheDocument();
  });
});
