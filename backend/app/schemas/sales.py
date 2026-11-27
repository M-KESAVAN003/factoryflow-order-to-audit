from datetime import date, datetime
from decimal import Decimal
from typing import List

from pydantic import BaseModel, ConfigDict, Field

from app.models.sales import InvoiceStatus, SalesOrderStatus, TaxType


class SalesOrderItemCreate(BaseModel):
    product_id: str
    quantity: Decimal = Field(gt=Decimal("0"), max_digits=18, decimal_places=6)


class SalesOrderCreate(BaseModel):
    order_number: str | None = Field(default=None, min_length=3, max_length=64)
    customer_id: str
    order_date: date | None = None
    notes: str | None = Field(default=None, max_length=1000)
    items: List[SalesOrderItemCreate] = Field(min_length=1)


class SalesOrderItemUpdate(BaseModel):
    product_id: str
    quantity: Decimal = Field(gt=Decimal("0"), max_digits=18, decimal_places=6)
    unit_price: Decimal | None = Field(default=None, gt=Decimal("0"), max_digits=14, decimal_places=2)


class SalesOrderUpdate(BaseModel):
    status: SalesOrderStatus | None = None
    notes: str | None = Field(default=None, max_length=1000)
    items: List[SalesOrderItemUpdate] | None = Field(default=None, min_length=1)


class SalesOrderApproveRequest(BaseModel):
    hold_if_insufficient: bool = False
    allow_partial: bool = False
    notes: str | None = Field(default=None, max_length=500)


class SalesOrderRejectRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


class SalesOrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    product_id: str
    product_name: str
    sku: str
    pack_size: str
    hsn_code: str
    unit_symbol: str
    requested_quantity: Decimal
    approved_quantity: Decimal
    dispatched_quantity: Decimal
    unit_price: Decimal
    submitted_unit_price: Decimal | None = None
    gst_rate: Decimal
    taxable_value: Decimal
    cgst_rate: Decimal
    sgst_rate: Decimal
    igst_rate: Decimal
    cgst_amount: Decimal
    sgst_amount: Decimal
    igst_amount: Decimal
    line_total: Decimal
    available_stock: Decimal
    shortage_quantity: Decimal


class SalesOrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    order_number: str
    customer_id: str
    customer_name: str
    customer_type: str
    customer_gstin: str
    salesman_id: str
    salesman_name: str
    salesman_email: str
    order_date: date
    status: SalesOrderStatus
    factory_state: str
    customer_state: str
    place_of_supply: str
    tax_type: TaxType
    subtotal: Decimal
    cgst_amount: Decimal
    sgst_amount: Decimal
    igst_amount: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    has_stock_shortage: bool
    shortage_notes: str | None = None
    notes: str | None = None
    rejection_reason: str | None = None
    invoice_id: str | None = None
    invoice_number: str | None = None
    dispatch_id: str | None = None
    dispatch_number: str | None = None
    idempotency_key: str | None = None
    local_order_id: str | None = None
    is_offline_order: bool = False
    offline_created_at: datetime | None = None
    synced_at: datetime | None = None
    price_review_required: bool = False
    price_conflict_notes: str | None = None
    created_at: datetime
    updated_at: datetime
    items: List[SalesOrderItemOut]


class StockCheckLineOut(BaseModel):
    product_id: str
    product_name: str
    sku: str
    unit_symbol: str
    requested_quantity: Decimal
    available_stock: Decimal
    committed_stock: Decimal
    net_available_stock: Decimal
    shortage_quantity: Decimal
    sufficient: bool


class SalesOrderStockCheckOut(BaseModel):
    sales_order_id: str
    order_number: str
    status: SalesOrderStatus
    tax_type: TaxType
    all_available: bool
    recommended_action: str
    subtotal_preview: Decimal
    cgst_preview: Decimal
    sgst_preview: Decimal
    igst_preview: Decimal
    total_preview: Decimal
    lines: List[StockCheckLineOut]


class InvoiceCreate(BaseModel):
    sales_order_id: str
    invoice_date: date | None = None


class CreditNoteCreate(BaseModel):
    reason: str = Field(min_length=3, max_length=500)
    amount: Decimal | None = Field(default=None, gt=Decimal("0"), max_digits=18, decimal_places=2)
    credit_date: date | None = None


class CreditNoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    credit_note_number: str
    invoice_id: str
    financial_year: str
    credit_date: date
    reason: str
    amount: Decimal
    created_by_email: str
    created_at: datetime


class InvoiceItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    product_id: str
    product_name: str
    sku: str
    pack_size: str
    hsn_code: str
    unit_symbol: str
    quantity: Decimal
    unit_price: Decimal
    gst_rate: Decimal
    taxable_value: Decimal
    cgst_rate: Decimal
    sgst_rate: Decimal
    igst_rate: Decimal
    cgst_amount: Decimal
    sgst_amount: Decimal
    igst_amount: Decimal
    line_total: Decimal


class InvoiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    invoice_number: str
    financial_year: str
    sequence_number: int
    sales_order_id: str
    order_number: str
    customer_id: str
    invoice_date: date
    status: InvoiceStatus
    factory_name: str
    factory_address: str
    factory_gstin: str
    factory_state: str
    factory_state_code: str
    customer_name: str
    customer_gstin: str
    billing_address: str
    customer_state: str
    place_of_supply: str
    tax_type: TaxType
    subtotal: Decimal
    cgst_amount: Decimal
    sgst_amount: Decimal
    igst_amount: Decimal
    tax_amount: Decimal
    grand_total: Decimal
    amount_in_words: str
    created_by_email: str
    created_at: datetime
    dispatch_id: str | None = None
    dispatch_number: str | None = None
    items: List[InvoiceItemOut]
    credit_notes: List[CreditNoteOut] = []


class DispatchCreate(BaseModel):
    sales_order_id: str
    dispatch_date: date | None = None
    vehicle_number: str | None = Field(default=None, max_length=64)
    transporter_name: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=500)


class DispatchItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    product_id: str
    product_name: str
    sku: str
    stock_item_id: str
    quantity: Decimal
    stock_ledger_id: str


class DispatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    dispatch_number: str
    sales_order_id: str
    order_number: str
    invoice_id: str
    invoice_number: str
    customer_name: str
    dispatch_date: date
    vehicle_number: str | None = None
    transporter_name: str | None = None
    notes: str | None = None
    dispatched_by_email: str
    created_at: datetime
    items: List[DispatchItemOut]


class CustomerSalesSummaryRow(BaseModel):
    customer_id: str
    customer_name: str
    customer_type: str
    customer_state: str
    orders_count: int
    dispatched_count: int
    total_order_value: Decimal
    invoiced_value: Decimal


class SalesOverviewOut(BaseModel):
    total_orders: int
    pending_review: int
    awaiting_stock: int
    invoiced_count: int
    dispatched_count: int
    total_sales_value: Decimal
    total_gst_collected: Decimal
    customer_summary: List[CustomerSalesSummaryRow]


class SalesOrderSyncLineIn(BaseModel):
    product_id: str
    product_name_snapshot: str | None = Field(default=None, max_length=200)
    quantity: Decimal = Field(gt=Decimal("0"), max_digits=18, decimal_places=6)
    cached_unit_price: Decimal = Field(gt=Decimal("0"), max_digits=14, decimal_places=2)
    cached_price_timestamp: datetime


class SalesOrderSyncRequest(BaseModel):
    local_order_id: str = Field(min_length=3, max_length=128)
    idempotency_key: str = Field(min_length=8, max_length=128)
    customer_id: str
    order_date: date | None = None
    offline_created_at: datetime
    notes: str | None = Field(default=None, max_length=1000)
    items: List[SalesOrderSyncLineIn] = Field(min_length=1, max_length=50)


class PriceConflictLineOut(BaseModel):
    product_id: str
    product_name: str
    submitted_unit_price: Decimal
    current_server_price: Decimal
    difference: Decimal


class SalesOrderSyncResponse(BaseModel):
    local_order_id: str
    idempotency_key: str
    server_order_id: str
    server_order_number: str
    server_status: SalesOrderStatus
    sync_status: str
    duplicate: bool
    price_review_required: bool
    price_conflict_notes: str | None = None
    price_conflicts: List[PriceConflictLineOut] = []
    synced_at: datetime
    order: SalesOrderOut
