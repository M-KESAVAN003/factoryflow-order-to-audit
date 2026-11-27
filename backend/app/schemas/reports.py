from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List

from pydantic import BaseModel

from app.schemas.costing_payment import InvoicePaymentStatusRow, ReceivablesAgeingReportOut


class DateRangeMeta(BaseModel):
    preset: str
    date_from: date
    date_to: date


class TrendPoint(BaseModel):
    label: str
    value: Decimal
    secondary_value: Decimal | None = None


class CategoryValuePoint(BaseModel):
    name: str
    value: Decimal
    quantity: Decimal | None = None


class OwnerAlertItem(BaseModel):
    severity: str  # HIGH | MEDIUM
    category: str
    message: str
    reference_id: str | None = None


class OwnerDashboardOut(BaseModel):
    date_range: DateRangeMeta
    todays_orders: int
    pending_orders: int
    todays_sales: Decimal
    monthly_sales: Decimal
    monthly_taxable_revenue: Decimal
    total_gst_collected: Decimal
    purchase_value: Decimal
    production_output: Decimal
    finished_goods_stock: Decimal
    raw_material_stock_value: Decimal
    total_production_cost: Decimal
    average_cost_per_packet: Decimal
    gross_margin_pct: Decimal
    total_customer_receivables: Decimal
    overdue_receivables: Decimal
    daily_sales_trend: List[TrendPoint]
    monthly_revenue_trend: List[TrendPoint]
    product_wise_sales: List[CategoryValuePoint]
    customer_wise_sales: List[CategoryValuePoint]
    purchase_vs_sales_trend: List[TrendPoint]
    production_planned_vs_actual: List[TrendPoint]
    material_consumption_comparison: List[CategoryValuePoint]
    production_wastage: List[CategoryValuePoint]
    cost_per_packet_trend: List[TrendPoint]
    outstanding_receivables_trend: List[TrendPoint]
    alerts: List[OwnerAlertItem]


class DomainDashboardOut(BaseModel):
    domain: str
    date_range: DateRangeMeta
    metrics: Dict[str, Any]


class SalesRegisterRow(BaseModel):
    invoice_id: str
    invoice_number: str
    invoice_date: date
    customer_name: str
    customer_gstin: str
    state: str
    product_name: str
    hsn_code: str
    quantity: Decimal
    taxable_value: Decimal
    cgst: Decimal
    sgst: Decimal
    igst: Decimal
    invoice_total: Decimal
    payment_status: str


class SalesRegisterReportOut(BaseModel):
    date_range: DateRangeMeta
    total: int
    page: int
    page_size: int
    rows: List[SalesRegisterRow]
    total_taxable: Decimal
    total_cgst: Decimal
    total_sgst: Decimal
    total_igst: Decimal
    total_invoice_value: Decimal
    credit_notes_total: Decimal
    draft_orders_count: int
    rejected_or_cancelled_orders_count: int
    reconciled_with_invoices: bool


class CustomerSalesReportRow(BaseModel):
    customer_id: str
    customer_name: str
    customer_gstin: str
    state: str
    total_orders: int
    total_invoices: int
    total_taxable_sales: Decimal
    total_gst: Decimal
    total_invoice_value: Decimal
    amount_collected: Decimal
    outstanding_amount: Decimal


class CustomerSalesReportOut(BaseModel):
    date_range: DateRangeMeta
    rows: List[CustomerSalesReportRow]
    total_invoice_value: Decimal
    total_collected: Decimal
    total_outstanding: Decimal


class ProductSalesReportRow(BaseModel):
    product_id: str
    product_name: str
    sku: str
    total_packets_sold: Decimal
    sales_value: Decimal
    average_selling_price: Decimal
    tax_amount: Decimal
    revenue_contribution_pct: Decimal


class ProductSalesReportOut(BaseModel):
    date_range: DateRangeMeta
    rows: List[ProductSalesReportRow]
    total_taxable_sales: Decimal
    total_tax: Decimal


class SalesmanPerformanceRow(BaseModel):
    salesman_id: str
    salesman_name: str
    salesman_email: str
    orders_count: int
    approved_orders: int
    dispatched_orders: int
    sales_value: Decimal


class SalesmanPerformanceReportOut(BaseModel):
    date_range: DateRangeMeta
    rows: List[SalesmanPerformanceRow]
    total_sales_value: Decimal


class GstRateSummaryRow(BaseModel):
    gst_rate: Decimal
    taxable_value: Decimal
    cgst_amount: Decimal
    sgst_amount: Decimal
    igst_amount: Decimal
    total_tax: Decimal


class GstSupplyTypeSummary(BaseModel):
    supply_bucket: str  # B2B | B2C
    invoices_count: int
    taxable_value: Decimal
    total_tax: Decimal
    invoice_total: Decimal


class GstOutwardSupplyReportOut(BaseModel):
    date_range: DateRangeMeta
    disclaimer: str
    gstr1_summary: Dict[str, Any]
    gstr3b_summary: Dict[str, Any]
    total_taxable_outward: Decimal
    intra_state_taxable: Decimal
    inter_state_taxable: Decimal
    total_cgst: Decimal
    total_sgst: Decimal
    total_igst: Decimal
    credit_note_adjustments: Decimal
    by_rate: List[GstRateSummaryRow]
    b2b_b2c_breakdown: List[GstSupplyTypeSummary]
    reconciled_with_invoices: bool


class HsnSummaryRow(BaseModel):
    hsn_code: str
    description: str
    uqc: str
    total_quantity: Decimal
    taxable_value: Decimal
    cgst_amount: Decimal
    sgst_amount: Decimal
    igst_amount: Decimal
    total_tax: Decimal
    total_value: Decimal


class GstHsnSummaryReportOut(BaseModel):
    date_range: DateRangeMeta
    disclaimer: str
    rows: List[HsnSummaryRow]
    total_taxable_value: Decimal
    total_tax: Decimal


class PurchaseRegisterRow(BaseModel):
    purchase_id: str
    reference_number: str
    purchase_date: date
    supplier_name: str
    supplier_gstin: str
    item_name: str
    quantity: Decimal
    unit_symbol: str
    purchase_rate: Decimal
    taxable_amount: Decimal
    gst_amount: Decimal
    total_purchase_amount: Decimal
    status: str


class PurchaseRegisterReportOut(BaseModel):
    date_range: DateRangeMeta
    total: int
    page: int
    page_size: int
    rows: List[PurchaseRegisterRow]
    posted_total: Decimal
    draft_or_reviewed_total: Decimal
    cancelled_total: Decimal
    reconciled_with_purchases: bool


class StockSummaryReportRow(BaseModel):
    stock_item_id: str
    item_name: str
    sku: str
    category: str
    opening_stock: Decimal
    total_receipts: Decimal
    total_issues: Decimal
    adjustments: Decimal
    closing_stock: Decimal
    base_unit: str
    weighted_average_rate: Decimal
    stock_valuation: Decimal
    reorder_level: Decimal
    stock_status: str


class StockSummaryReportOut(BaseModel):
    date_range: DateRangeMeta
    as_of_date: date
    category_filter: str
    rows: List[StockSummaryReportRow]
    total_valuation: Decimal
    reconciled_with_ledger: bool


class StockLedgerReportRow(BaseModel):
    id: str
    transaction_date: datetime
    stock_item_id: str
    item_name: str
    sku: str
    category: str
    movement_type: str
    source_document: str
    source_document_id: str
    quantity_in: Decimal
    quantity_out: Decimal
    running_balance: Decimal
    unit_valuation: Decimal
    movement_value: Decimal
    created_by_email: str


class StockLedgerReportOut(BaseModel):
    date_range: DateRangeMeta
    total: int
    page: int
    page_size: int
    rows: List[StockLedgerReportRow]
    total_quantity_in: Decimal
    total_quantity_out: Decimal


class ProductionRegisterRow(BaseModel):
    production_run_id: str
    order_number: str
    product_name: str
    batch_number: str
    production_date: date
    bom_version: int
    planned_output: Decimal
    actual_good_output: Decimal
    wastage: Decimal
    supervisor_email: str
    total_production_cost: Decimal
    cost_per_packet: Decimal
    status: str


class ProductionRegisterReportOut(BaseModel):
    date_range: DateRangeMeta
    rows: List[ProductionRegisterRow]
    total_good_output: Decimal
    total_production_cost: Decimal
    reconciled_with_runs: bool


class ProductionVarianceMaterialLine(BaseModel):
    order_number: str
    product_name: str
    material_name: str
    unit_symbol: str
    planned_quantity: Decimal
    actual_quantity: Decimal
    difference: Decimal
    variance_pct: Decimal
    status: str
    exceeds_tolerance: bool


class ProductionYieldRow(BaseModel):
    order_number: str
    product_name: str
    expected_yield: Decimal
    actual_output: Decimal
    yield_pct: Decimal
    yield_variance_pct: Decimal
    tolerance_status: str
    exceeds_tolerance: bool
    damaged_pouches: Decimal
    wastage_quantity: Decimal
    packaging_warning: str | None = None


class ProductionVarianceReportOut(BaseModel):
    date_range: DateRangeMeta
    yield_rows: List[ProductionYieldRow]
    material_rows: List[ProductionVarianceMaterialLine]
    flagged_count: int


class ProductionCostReportOut(BaseModel):
    date_range: DateRangeMeta
    rows: List[Dict[str, Any]]
    total_material_cost: Decimal
    total_packaging_cost: Decimal
    total_expense_cost: Decimal
    total_production_cost: Decimal
    reconciled_with_expenses_and_ledger: bool


class PaymentRegisterRow(BaseModel):
    payment_id: str
    payment_reference: str
    customer_name: str
    payment_date: date
    payment_method: str
    payment_amount: Decimal
    allocated_amount: Decimal
    unallocated_amount: Decimal
    status: str


class PaymentRegisterReportOut(BaseModel):
    date_range: DateRangeMeta
    total: int
    page: int
    page_size: int
    rows: List[PaymentRegisterRow]
    total_received: Decimal
    total_allocated: Decimal
    total_unallocated: Decimal
    reconciled_with_payments: bool


class ReceivablesReportSummaryOut(BaseModel):
    as_of_date: date
    rows: List[InvoicePaymentStatusRow]
    customers: List[Dict[str, Any]]
    total_invoiced: Decimal
    total_paid: Decimal
    total_outstanding: Decimal
    reconciled_with_invoices: bool


class ReceivablesAgeingAuditOut(ReceivablesAgeingReportOut):
    reconciled_with_outstanding: bool
