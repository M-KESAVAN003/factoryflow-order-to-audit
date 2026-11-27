import { useEffect, useState } from "react";
import { api, ApiError } from "../lib/api";
import { ReportScaffold } from "../components/ReportScaffold";
import { ReportFilterParams } from "../types/reports";

export type AuditReportMode =
  | "sales"
  | "sales_customers"
  | "sales_products"
  | "gst_outward"
  | "gst_hsn"
  | "purchases"
  | "stock_raw"
  | "stock_packaging"
  | "stock_finished"
  | "stock_ledger"
  | "production"
  | "production_variance"
  | "production_costing"
  | "payments"
  | "receivables"
  | "receivables_ageing";

interface ColumnDef {
  key: string;
  label: string;
  mono?: boolean;
  prefix?: string;
}

interface ReportSpec {
  title: string;
  subtitle: string;
  endpoint: string;
  exportKey: string;
  rowsField: string;
  showAsOf?: boolean;
  reconciledField?: string;
  disclaimerField?: string;
  fixedParams?: Record<string, string>;
  columns: ColumnDef[];
  summaryBuilder?: (data: Record<string, unknown>) => string[];
}

const REPORT_SPECS: Record<AuditReportMode, ReportSpec> = {
  sales: {
    title: "Sales Register",
    subtitle: "Invoice line-level register reconciled against posted GST invoices.",
    endpoint: "sales",
    exportKey: "sales",
    rowsField: "rows",
    reconciledField: "reconciled_with_invoices",
    columns: [
      { key: "invoice_number", label: "Invoice #", mono: true },
      { key: "invoice_date", label: "Date" },
      { key: "customer_name", label: "Customer" },
      { key: "customer_gstin", label: "GSTIN", mono: true },
      { key: "product_name", label: "Product" },
      { key: "hsn_code", label: "HSN", mono: true },
      { key: "quantity", label: "Qty", mono: true },
      { key: "taxable_value", label: "Taxable", mono: true, prefix: "Rs " },
      { key: "cgst", label: "CGST", mono: true, prefix: "Rs " },
      { key: "sgst", label: "SGST", mono: true, prefix: "Rs " },
      { key: "igst", label: "IGST", mono: true, prefix: "Rs " },
      { key: "invoice_total", label: "Total", mono: true, prefix: "Rs " },
      { key: "payment_status", label: "Pay Status" },
    ],
    summaryBuilder: (d) => [
      `Taxable: Rs ${d.total_taxable}`,
      `CGST: Rs ${d.total_cgst}`,
      `SGST: Rs ${d.total_sgst}`,
      `IGST: Rs ${d.total_igst}`,
      `Invoice Total: Rs ${d.total_invoice_value}`,
    ],
  },
  sales_customers: {
    title: "Customer Sales Report",
    subtitle: "Customer-wise order volume, GST billing, collections, and outstanding balances.",
    endpoint: "sales/customers",
    exportKey: "sales_customers",
    rowsField: "rows",
    columns: [
      { key: "customer_name", label: "Customer" },
      { key: "state", label: "State" },
      { key: "total_orders", label: "Orders", mono: true },
      { key: "total_invoices", label: "Invoices", mono: true },
      { key: "total_taxable_sales", label: "Taxable", mono: true, prefix: "Rs " },
      { key: "total_gst", label: "GST", mono: true, prefix: "Rs " },
      { key: "total_invoice_value", label: "Invoiced", mono: true, prefix: "Rs " },
      { key: "amount_collected", label: "Collected", mono: true, prefix: "Rs " },
      { key: "outstanding_amount", label: "Outstanding", mono: true, prefix: "Rs " },
    ],
    summaryBuilder: (d) => [
      `Total Invoiced: Rs ${d.total_invoice_value}`,
      `Collected: Rs ${d.total_collected}`,
      `Outstanding: Rs ${d.total_outstanding}`,
    ],
  },
  sales_products: {
    title: "Product Sales Report",
    subtitle: "Packets sold, pre-GST sales contribution, and average realized price.",
    endpoint: "sales/products",
    exportKey: "sales_products",
    rowsField: "rows",
    columns: [
      { key: "product_name", label: "Product" },
      { key: "sku", label: "SKU", mono: true },
      { key: "total_packets_sold", label: "Packets Sold", mono: true },
      { key: "sales_value", label: "Taxable Sales", mono: true, prefix: "Rs " },
      { key: "average_selling_price", label: "Avg Price", mono: true, prefix: "Rs " },
      { key: "tax_amount", label: "GST Tax", mono: true, prefix: "Rs " },
      { key: "revenue_contribution_pct", label: "Share %", mono: true },
    ],
    summaryBuilder: (d) => [
      `Taxable Sales: Rs ${d.total_taxable_sales}`,
      `Total Tax: Rs ${d.total_tax}`,
    ],
  },
  gst_outward: {
    title: "GST Outward Supply Summary",
    subtitle: "Indicative GSTR-1 / GSTR-3B tax rate and intra/interstate outward breakdown.",
    endpoint: "gst/outward-supplies",
    exportKey: "gst_outward",
    rowsField: "by_rate",
    reconciledField: "reconciled_with_invoices",
    disclaimerField: "disclaimer",
    columns: [
      { key: "gst_rate", label: "GST Rate %", mono: true },
      { key: "taxable_value", label: "Taxable Supply", mono: true, prefix: "Rs " },
      { key: "cgst_amount", label: "CGST", mono: true, prefix: "Rs " },
      { key: "sgst_amount", label: "SGST", mono: true, prefix: "Rs " },
      { key: "igst_amount", label: "IGST", mono: true, prefix: "Rs " },
      { key: "total_tax", label: "Total Tax", mono: true, prefix: "Rs " },
    ],
    summaryBuilder: (d) => [
      `Taxable Outward: Rs ${d.total_taxable_outward}`,
      `Intra-state: Rs ${d.intra_state_taxable}`,
      `Inter-state: Rs ${d.inter_state_taxable}`,
      `CGST: Rs ${d.total_cgst}`,
      `SGST: Rs ${d.total_sgst}`,
      `IGST: Rs ${d.total_igst}`,
    ],
  },
  gst_hsn: {
    title: "GST HSN Summary",
    subtitle: "HSN-wise quantity, taxable value, and GST tax liability breakdown.",
    endpoint: "gst/hsn-summary",
    exportKey: "gst_hsn",
    rowsField: "rows",
    disclaimerField: "disclaimer",
    columns: [
      { key: "hsn_code", label: "HSN Code", mono: true },
      { key: "description", label: "Description" },
      { key: "uqc", label: "UQC" },
      { key: "total_quantity", label: "Total Qty", mono: true },
      { key: "taxable_value", label: "Taxable", mono: true, prefix: "Rs " },
      { key: "cgst_amount", label: "CGST", mono: true, prefix: "Rs " },
      { key: "sgst_amount", label: "SGST", mono: true, prefix: "Rs " },
      { key: "igst_amount", label: "IGST", mono: true, prefix: "Rs " },
      { key: "total_value", label: "Total Value", mono: true, prefix: "Rs " },
    ],
    summaryBuilder: (d) => [
      `Taxable Value: Rs ${d.total_taxable_value}`,
      `Total Tax: Rs ${d.total_tax}`,
    ],
  },
  purchases: {
    title: "Purchase Register",
    subtitle: "Supplier purchase lines distinguishing posted vs draft vs cancelled purchases.",
    endpoint: "purchases",
    exportKey: "purchases",
    rowsField: "rows",
    reconciledField: "reconciled_with_purchases",
    columns: [
      { key: "reference_number", label: "Ref #", mono: true },
      { key: "purchase_date", label: "Date" },
      { key: "supplier_name", label: "Supplier" },
      { key: "item_name", label: "Item" },
      { key: "quantity", label: "Qty", mono: true },
      { key: "unit_symbol", label: "Unit" },
      { key: "purchase_rate", label: "Rate", mono: true, prefix: "Rs " },
      { key: "taxable_amount", label: "Taxable", mono: true, prefix: "Rs " },
      { key: "total_purchase_amount", label: "Total", mono: true, prefix: "Rs " },
      { key: "status", label: "Status" },
    ],
    summaryBuilder: (d) => [
      `Posted Total: Rs ${d.posted_total}`,
      `Draft/Reviewed: Rs ${d.draft_or_reviewed_total}`,
      `Cancelled: Rs ${d.cancelled_total}`,
    ],
  },
  stock_raw: {
    title: "Raw Material Stock Report",
    subtitle: "Historical or cut-off RAW_MATERIAL balances reconstructed directly from StockLedger.",
    endpoint: "stock/summary",
    exportKey: "stock_summary",
    rowsField: "rows",
    showAsOf: true,
    reconciledField: "reconciled_with_ledger",
    fixedParams: { category: "RAW_MATERIAL" },
    columns: [
      { key: "item_name", label: "Item" },
      { key: "sku", label: "SKU", mono: true },
      { key: "opening_stock", label: "Opening", mono: true },
      { key: "total_receipts", label: "Receipts", mono: true },
      { key: "total_issues", label: "Issues", mono: true },
      { key: "closing_stock", label: "Closing", mono: true },
      { key: "base_unit", label: "Unit" },
      { key: "weighted_average_rate", label: "Avg Rate", mono: true, prefix: "Rs " },
      { key: "stock_valuation", label: "Valuation", mono: true, prefix: "Rs " },
      { key: "stock_status", label: "Status" },
    ],
    summaryBuilder: (d) => [`As of ${d.as_of_date}`, `Total Valuation: Rs ${d.total_valuation}`],
  },
  stock_packaging: {
    title: "Packaging Stock Report",
    subtitle: "Historical or cut-off PACKAGING balances reconstructed from StockLedger.",
    endpoint: "stock/summary",
    exportKey: "stock_summary",
    rowsField: "rows",
    showAsOf: true,
    reconciledField: "reconciled_with_ledger",
    fixedParams: { category: "PACKAGING" },
    columns: [
      { key: "item_name", label: "Item" },
      { key: "sku", label: "SKU", mono: true },
      { key: "opening_stock", label: "Opening", mono: true },
      { key: "total_receipts", label: "Receipts", mono: true },
      { key: "total_issues", label: "Issues", mono: true },
      { key: "closing_stock", label: "Closing", mono: true },
      { key: "base_unit", label: "Unit" },
      { key: "weighted_average_rate", label: "Avg Rate", mono: true, prefix: "Rs " },
      { key: "stock_valuation", label: "Valuation", mono: true, prefix: "Rs " },
      { key: "stock_status", label: "Status" },
    ],
    summaryBuilder: (d) => [`As of ${d.as_of_date}`, `Total Valuation: Rs ${d.total_valuation}`],
  },
  stock_finished: {
    title: "Finished Goods Stock Report",
    subtitle: "Historical or cut-off FINISHED_GOOD stock reconstructed directly from StockLedger.",
    endpoint: "stock/summary",
    exportKey: "stock_summary",
    rowsField: "rows",
    showAsOf: true,
    reconciledField: "reconciled_with_ledger",
    fixedParams: { category: "FINISHED_GOOD" },
    columns: [
      { key: "item_name", label: "Item" },
      { key: "sku", label: "SKU", mono: true },
      { key: "opening_stock", label: "Opening", mono: true },
      { key: "total_receipts", label: "Receipts", mono: true },
      { key: "total_issues", label: "Issues", mono: true },
      { key: "closing_stock", label: "Closing", mono: true },
      { key: "base_unit", label: "Unit" },
      { key: "weighted_average_rate", label: "Avg Rate", mono: true, prefix: "Rs " },
      { key: "stock_valuation", label: "Valuation", mono: true, prefix: "Rs " },
      { key: "stock_status", label: "Status" },
    ],
    summaryBuilder: (d) => [`As of ${d.as_of_date}`, `Total Valuation: Rs ${d.total_valuation}`],
  },
  stock_ledger: {
    title: "Audit Stock Ledger",
    subtitle: "Chronological append-only movements traceable to purchases, production, dispatch & adjustments.",
    endpoint: "stock/ledger",
    exportKey: "stock_ledger",
    rowsField: "rows",
    columns: [
      { key: "item_name", label: "Item" },
      { key: "movement_type", label: "Type" },
      { key: "source_document", label: "Source" },
      { key: "source_document_id", label: "Doc ID", mono: true },
      { key: "quantity_in", label: "Qty In", mono: true },
      { key: "quantity_out", label: "Qty Out", mono: true },
      { key: "running_balance", label: "Running Bal", mono: true },
      { key: "unit_valuation", label: "Unit Cost", mono: true, prefix: "Rs " },
      { key: "movement_value", label: "Value", mono: true, prefix: "Rs " },
      { key: "created_by_email", label: "Actor" },
    ],
    summaryBuilder: (d) => [
      `Total In: ${d.total_quantity_in}`,
      `Total Out: ${d.total_quantity_out}`,
    ],
  },
  production: {
    title: "Production Register",
    subtitle: "Completed and posted production batches with BOM version, wastage, and unit cost.",
    endpoint: "production",
    exportKey: "production",
    rowsField: "rows",
    reconciledField: "reconciled_with_runs",
    columns: [
      { key: "order_number", label: "Run ID", mono: true },
      { key: "product_name", label: "Product" },
      { key: "batch_number", label: "Batch", mono: true },
      { key: "production_date", label: "Date" },
      { key: "bom_version", label: "BOM v", mono: true },
      { key: "planned_output", label: "Planned", mono: true },
      { key: "actual_good_output", label: "Good Out", mono: true },
      { key: "wastage", label: "Wastage", mono: true },
      { key: "total_production_cost", label: "Cost", mono: true, prefix: "Rs " },
      { key: "cost_per_packet", label: "Cost/Pkt", mono: true, prefix: "Rs " },
      { key: "status", label: "Status" },
    ],
    summaryBuilder: (d) => [
      `Good Output: ${d.total_good_output}`,
      `Total Cost: Rs ${d.total_production_cost}`,
    ],
  },
  production_variance: {
    title: "Audit Production Variance Report",
    subtitle: "Planned vs actual material variances exceeding configured tolerance threshold.",
    endpoint: "production/variance",
    exportKey: "production_variance",
    rowsField: "material_rows",
    columns: [
      { key: "order_number", label: "Run", mono: true },
      { key: "product_name", label: "Product" },
      { key: "material_name", label: "Material" },
      { key: "planned_quantity", label: "Planned", mono: true },
      { key: "actual_quantity", label: "Actual", mono: true },
      { key: "difference", label: "Diff", mono: true },
      { key: "variance_pct", label: "Var %", mono: true },
      { key: "status", label: "Alert" },
    ],
    summaryBuilder: (d) => [`Flagged Over-Tolerance Count: ${d.flagged_count}`],
  },
  production_costing: {
    title: "Audit Production Cost Report",
    subtitle: "Run costing reconciled against actual StockLedger issues and posted ProductionExpense rows.",
    endpoint: "production/costing",
    exportKey: "production_costing",
    rowsField: "rows",
    reconciledField: "reconciled_with_expenses_and_ledger",
    columns: [
      { key: "order_number", label: "Run", mono: true },
      { key: "product_name", label: "Product" },
      { key: "actual_good_output", label: "Good Out", mono: true },
      { key: "raw_material_cost", label: "Raw Mat", mono: true, prefix: "Rs " },
      { key: "packaging_cost", label: "Packaging", mono: true, prefix: "Rs " },
      { key: "total_overhead_cost", label: "Overhead", mono: true, prefix: "Rs " },
      { key: "total_production_cost", label: "Total Cost", mono: true, prefix: "Rs " },
      { key: "cost_per_packet_display", label: "Cost/Pkt", mono: true, prefix: "Rs " },
      { key: "gross_margin_pct", label: "Margin %", mono: true },
    ],
    summaryBuilder: (d) => [
      `Raw Mat: Rs ${d.total_material_cost}`,
      `Pkg: Rs ${d.total_packaging_cost}`,
      `Expenses: Rs ${d.total_expense_cost}`,
      `Total Cost: Rs ${d.total_production_cost}`,
    ],
  },
  payments: {
    title: "Payment Register",
    subtitle: "Customer payment register reconciled against posted Payment and Allocation records.",
    endpoint: "payments",
    exportKey: "payments",
    rowsField: "rows",
    reconciledField: "reconciled_with_payments",
    columns: [
      { key: "payment_reference", label: "Ref #", mono: true },
      { key: "customer_name", label: "Customer" },
      { key: "payment_date", label: "Date" },
      { key: "payment_method", label: "Method" },
      { key: "payment_amount", label: "Amount", mono: true, prefix: "Rs " },
      { key: "allocated_amount", label: "Allocated", mono: true, prefix: "Rs " },
      { key: "unallocated_amount", label: "Unallocated", mono: true, prefix: "Rs " },
      { key: "status", label: "Status" },
    ],
    summaryBuilder: (d) => [
      `Received: Rs ${d.total_received}`,
      `Allocated: Rs ${d.total_allocated}`,
      `Unallocated: Rs ${d.total_unallocated}`,
    ],
  },
  receivables: {
    title: "Audit Receivables Report",
    subtitle: "Invoice-wise receivables reconciled directly from invoices minus credit notes & allocations.",
    endpoint: "receivables",
    exportKey: "receivables",
    rowsField: "rows",
    showAsOf: true,
    reconciledField: "reconciled_with_invoices",
    columns: [
      { key: "customer_name", label: "Customer" },
      { key: "invoice_number", label: "Invoice #", mono: true },
      { key: "invoice_date", label: "Inv Date" },
      { key: "due_date", label: "Due Date" },
      { key: "invoice_amount", label: "Total", mono: true, prefix: "Rs " },
      { key: "paid_amount", label: "Paid", mono: true, prefix: "Rs " },
      { key: "outstanding_amount", label: "Outstanding", mono: true, prefix: "Rs " },
      { key: "payment_status", label: "Status" },
    ],
    summaryBuilder: (d) => [
      `Invoiced: Rs ${d.total_invoiced}`,
      `Paid: Rs ${d.total_paid}`,
      `Outstanding: Rs ${d.total_outstanding}`,
    ],
  },
  receivables_ageing: {
    title: "Audit Receivables Ageing",
    subtitle: "Overdue receivables bucketed across Current, 1-30, 31-60, 61-90, and >90 days.",
    endpoint: "receivables/ageing",
    exportKey: "receivables_ageing",
    rowsField: "rows",
    showAsOf: true,
    reconciledField: "reconciled_with_outstanding",
    columns: [
      { key: "customer_name", label: "Customer" },
      { key: "invoice_number", label: "Invoice #", mono: true },
      { key: "invoice_date", label: "Inv Date" },
      { key: "due_date", label: "Due Date" },
      { key: "invoice_amount", label: "Total", mono: true, prefix: "Rs " },
      { key: "paid_amount", label: "Paid", mono: true, prefix: "Rs " },
      { key: "outstanding_amount", label: "Outstanding", mono: true, prefix: "Rs " },
      { key: "days_overdue", label: "Days Overdue", mono: true },
      { key: "ageing_category", label: "Bucket" },
    ],
    summaryBuilder: (d) => [`Total Outstanding: Rs ${d.total_outstanding}`],
  },
};

export function AuditReportPage({ mode }: { mode: AuditReportMode }) {
  const spec = REPORT_SPECS[mode];
  const [filters, setFilters] = useState<ReportFilterParams>({
    preset: "last_30_days",
    ...(spec.fixedParams ?? {}),
  });
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const mergedFilters: ReportFilterParams = {
    ...filters,
    ...(spec.fixedParams ?? {}),
  };

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await api.fetchReport<Record<string, unknown>>(spec.endpoint, mergedFilters));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load report.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setFilters({ preset: "last_30_days", ...(spec.fixedParams ?? {}) });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode]);

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, filters.preset, filters.date_from, filters.date_to, filters.as_of_date]);

  const rows = ((data?.[spec.rowsField] as Record<string, unknown>[] | undefined) ?? []);
  const summaryChips = data && spec.summaryBuilder ? spec.summaryBuilder(data) : [];

  return (
    <ReportScaffold
      title={spec.title}
      subtitle={spec.subtitle}
      reportType={spec.exportKey}
      filters={mergedFilters}
      onFiltersChange={setFilters}
      onRefresh={() => void load()}
      showAsOfDate={spec.showAsOf}
      reconciled={spec.reconciledField ? Boolean(data?.[spec.reconciledField]) : undefined}
      disclaimer={spec.disclaimerField ? (data?.[spec.disclaimerField] as string | undefined) : undefined}
      loading={loading}
      error={error}
    >
      {summaryChips.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {summaryChips.map((chip) => (
            <span
              key={chip}
              className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 font-mono text-xs font-semibold text-slate-900 shadow-sm"
            >
              {chip}
            </span>
          ))}
        </div>
      )}

      <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-50 text-[11px] uppercase tracking-wider text-slate-500">
            <tr>
              {spec.columns.map((c) => (
                <th key={c.key} className="px-3 py-3 font-medium">
                  {c.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {rows.map((row, idx) => (
              <tr key={idx} className="hover:bg-slate-50">
                {spec.columns.map((c) => (
                  <td key={c.key} className={`px-3 py-2.5 ${c.mono ? "font-mono" : ""}`}>
                    {c.prefix ?? ""}
                    {String(row[c.key] ?? "—")}
                  </td>
                ))}
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td colSpan={spec.columns.length} className="px-4 py-8 text-center text-slate-400">
                  No records match the selected reporting filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </ReportScaffold>
  );
}
