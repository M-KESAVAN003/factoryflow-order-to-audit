from datetime import date, datetime
from decimal import Decimal
from typing import List

from pydantic import BaseModel, ConfigDict, Field

from app.models.costing_payment import (
    CustomerPaymentMethod,
    CustomerPaymentStatus,
    ExpenseCategory,
    ExpenseStatus,
)


class ProductionExpenseCreate(BaseModel):
    category: ExpenseCategory
    description: str = Field(min_length=2, max_length=250)
    amount: Decimal = Field(gt=Decimal("0"), max_digits=18, decimal_places=2)
    expense_date: date | None = None
    auto_post: bool = False


class ProductionExpenseUpdate(BaseModel):
    category: ExpenseCategory | None = None
    description: str | None = Field(default=None, min_length=2, max_length=250)
    amount: Decimal | None = Field(default=None, gt=Decimal("0"), max_digits=18, decimal_places=2)
    expense_date: date | None = None


class ProductionExpenseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    expense_number: str
    production_run_id: str
    order_number: str
    category: ExpenseCategory
    description: str
    amount: Decimal
    expense_date: date
    status: ExpenseStatus
    reversal_of_id: str | None = None
    recorded_by_email: str
    posted_at: datetime | None = None
    created_at: datetime


class MaterialCostLineOut(BaseModel):
    stock_item_id: str
    stock_item_name: str
    sku: str
    category: str
    actual_quantity: Decimal
    damaged_quantity: Decimal
    total_consumed_qty: Decimal
    unit_symbol: str
    weighted_avg_rate: Decimal
    total_cost: Decimal


class RunCostingOut(BaseModel):
    production_run_id: str
    order_number: str
    batch_number: str
    product_id: str
    product_name: str
    product_sku: str
    production_date: date
    status: str
    actual_good_output: Decimal
    unit_symbol: str
    raw_material_cost: Decimal
    packaging_cost: Decimal
    material_and_packaging_cost: Decimal
    labour_cost: Decimal
    gas_and_power_cost: Decimal
    other_overhead_cost: Decimal
    total_overhead_cost: Decimal
    total_production_cost: Decimal
    cost_per_packet_exact: Decimal
    cost_per_packet_display: Decimal
    selling_price_before_gst: Decimal
    gross_profit_per_packet: Decimal
    gross_margin_pct: Decimal
    materials: List[MaterialCostLineOut]
    expenses: List[ProductionExpenseOut]


class ProductCostSummaryOut(BaseModel):
    product_id: str
    product_name: str
    product_sku: str
    runs_count: int
    total_good_output: Decimal
    total_material_cost: Decimal
    total_expense_cost: Decimal
    total_production_cost: Decimal
    avg_cost_per_packet: Decimal
    selling_price_before_gst: Decimal
    gross_profit_per_packet: Decimal
    gross_margin_pct: Decimal
    runs: List[RunCostingOut]


class ProductionCostDashboardOut(BaseModel):
    total_runs_costed: int
    total_good_output: Decimal
    total_raw_material_cost: Decimal
    total_packaging_cost: Decimal
    total_labour_cost: Decimal
    total_gas_and_power_cost: Decimal
    total_other_overhead_cost: Decimal
    total_production_cost: Decimal
    avg_cost_per_packet: Decimal
    avg_gross_margin_pct: Decimal
    products: List[ProductCostSummaryOut]
    runs: List[RunCostingOut]


class PaymentAllocationInput(BaseModel):
    invoice_id: str
    amount: Decimal = Field(gt=Decimal("0"), max_digits=18, decimal_places=2)
    notes: str | None = Field(default=None, max_length=300)


class PaymentCreate(BaseModel):
    payment_reference: str | None = Field(default=None, min_length=3, max_length=64)
    customer_id: str
    payment_date: date | None = None
    payment_method: CustomerPaymentMethod
    amount_received: Decimal = Field(gt=Decimal("0"), max_digits=18, decimal_places=2)
    transaction_reference: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=1000)
    allocations: List[PaymentAllocationInput] = []


class PaymentAllocateRequest(BaseModel):
    allocation_date: date | None = None
    allocations: List[PaymentAllocationInput] = Field(min_length=1)


class PaymentAllocationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    payment_id: str
    payment_reference: str
    invoice_id: str
    invoice_number: str
    allocated_amount: Decimal
    allocation_date: date
    notes: str | None = None
    allocated_by_email: str
    created_at: datetime


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    payment_reference: str
    customer_id: str
    customer_name: str
    payment_date: date
    payment_method: CustomerPaymentMethod
    amount_received: Decimal
    allocated_amount: Decimal
    unallocated_advance: Decimal
    transaction_reference: str | None = None
    notes: str | None = None
    status: CustomerPaymentStatus
    recorded_by_email: str
    created_at: datetime
    allocations: List[PaymentAllocationOut]


class InvoicePaymentStatusRow(BaseModel):
    invoice_id: str
    invoice_number: str
    customer_id: str
    customer_name: str
    invoice_date: date
    due_date: date
    invoice_amount: Decimal
    paid_amount: Decimal
    credit_note_amount: Decimal
    outstanding_amount: Decimal
    payment_status: str  # UNPAID | PARTIAL | PAID
    days_overdue: int
    ageing_category: str


class InvoicePaymentsDetailOut(BaseModel):
    invoice: InvoicePaymentStatusRow
    allocations: List[PaymentAllocationOut]


class CustomerReceivableSummary(BaseModel):
    customer_id: str
    customer_name: str
    customer_state: str
    invoices_count: int
    total_invoiced: Decimal
    total_paid: Decimal
    unallocated_advance: Decimal
    total_outstanding: Decimal
    net_receivable: Decimal


class ReceivablesReportOut(BaseModel):
    total_invoiced: Decimal
    total_collected: Decimal
    total_unallocated_advances: Decimal
    total_outstanding: Decimal
    default_payment_term_days: int
    customers: List[CustomerReceivableSummary]
    invoices: List[InvoicePaymentStatusRow]


class AgeingBucketSummary(BaseModel):
    category: str
    invoices_count: int
    outstanding_amount: Decimal


class ReceivablesAgeingReportOut(BaseModel):
    as_of_date: date
    default_payment_term_days: int
    total_outstanding: Decimal
    buckets: List[AgeingBucketSummary]
    rows: List[InvoicePaymentStatusRow]


class CustomerLedgerEntryOut(BaseModel):
    entry_date: date
    doc_type: str  # INVOICE | PAYMENT | CREDIT_NOTE
    reference_number: str
    description: str
    debit_amount: Decimal
    credit_amount: Decimal
    running_balance: Decimal


class CustomerLedgerOut(BaseModel):
    customer_id: str
    customer_name: str
    customer_gstin: str
    customer_state: str
    total_invoiced: Decimal
    total_paid: Decimal
    unallocated_advance: Decimal
    closing_outstanding: Decimal
    entries: List[CustomerLedgerEntryOut]


class CustomerStatementOut(BaseModel):
    customer_id: str
    customer_name: str
    customer_gstin: str
    billing_address: str
    from_date: date | None = None
    to_date: date | None = None
    opening_balance: Decimal
    period_debits: Decimal
    period_credits: Decimal
    closing_balance: Decimal
    unallocated_advance: Decimal
    invoices: List[InvoicePaymentStatusRow]
    entries: List[CustomerLedgerEntryOut]
