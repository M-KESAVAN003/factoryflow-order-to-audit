from datetime import date, datetime
from decimal import Decimal
from typing import List

from pydantic import BaseModel, ConfigDict, Field

from app.models.inventory import AdjustmentStatus, MovementType
from app.models.purchase import PaymentStatus, PurchaseStatus
from app.models.stock_item import StockItemType


class PurchaseItemInput(BaseModel):
    stock_item_id: str
    unit_id: str
    quantity: Decimal = Field(gt=Decimal("0"), max_digits=18, decimal_places=6)
    unit_rate: Decimal = Field(ge=Decimal("0"), max_digits=18, decimal_places=6)
    tax_rate: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0"), le=Decimal("28"), max_digits=5, decimal_places=2)


class PurchaseCreate(BaseModel):
    reference_number: str = Field(min_length=3, max_length=64)
    supplier_id: str
    purchase_date: date
    payment_status: PaymentStatus = PaymentStatus.UNPAID
    notes: str | None = Field(default=None, max_length=1000)
    items: List[PurchaseItemInput] = Field(min_length=1)


class PurchaseUpdate(BaseModel):
    supplier_id: str | None = None
    purchase_date: date | None = None
    payment_status: PaymentStatus | None = None
    status: PurchaseStatus | None = None
    notes: str | None = Field(default=None, max_length=1000)
    items: List[PurchaseItemInput] | None = Field(default=None, min_length=1)


class PurchaseCancelRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


class PurchaseItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    stock_item_id: str
    stock_item_name: str
    stock_item_sku: str
    unit_id: str
    unit_symbol: str
    base_unit_symbol: str
    quantity: Decimal
    base_quantity: Decimal
    unit_rate: Decimal
    tax_rate: Decimal
    tax_amount: Decimal
    line_subtotal: Decimal
    line_total: Decimal


class PurchaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    reference_number: str
    supplier_id: str
    supplier_name: str
    purchase_date: date
    status: PurchaseStatus
    payment_status: PaymentStatus
    subtotal: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    notes: str | None = None
    created_by: str
    created_by_email: str
    posted_by: str | None = None
    posted_at: datetime | None = None
    cancelled_at: datetime | None = None
    cancel_reason: str | None = None
    created_at: datetime
    updated_at: datetime
    items: List[PurchaseItemOut]


class InventoryItemRow(BaseModel):
    stock_item_id: str
    name: str
    sku: str
    item_type: StockItemType
    category_label: str
    base_unit_id: str
    base_unit_symbol: str
    available_quantity: Decimal
    average_cost: Decimal
    stock_value: Decimal
    reorder_level: Decimal
    shortage_quantity: Decimal
    stock_status: str  # GREEN | ORANGE | RED
    is_active: bool
    last_movement_at: datetime | None = None


class StockLedgerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    stock_item_id: str
    stock_item_name: str
    stock_item_sku: str
    movement_type: MovementType
    quantity_in: Decimal
    quantity_out: Decimal
    base_unit_symbol: str
    reference_doc_type: str
    reference_doc_id: str
    transaction_date: datetime
    unit_cost: Decimal
    total_value: Decimal
    balance_qty_after: Decimal
    avg_cost_after: Decimal
    balance_value_after: Decimal
    notes: str | None = None
    created_by_email: str | None = None
    created_at: datetime


class InventoryItemDetailOut(BaseModel):
    item: InventoryItemRow
    ledger_sum_quantity: Decimal
    reconciled: bool
    recent_movements: List[StockLedgerOut]


class CategorySummary(BaseModel):
    item_type: StockItemType
    label: str
    item_count: int
    total_quantity: Decimal
    total_value: Decimal
    low_stock_count: int


class InventorySummaryOut(BaseModel):
    total_items: int
    total_stock_value: Decimal
    low_stock_red_count: int
    approaching_orange_count: int
    categories: List[CategorySummary]
    recent_movements: List[StockLedgerOut]


class StockAdjustmentCreate(BaseModel):
    stock_item_id: str
    physical_count: Decimal = Field(ge=Decimal("0"), max_digits=18, decimal_places=6)
    reason: str = Field(min_length=3, max_length=200)
    supporting_notes: str | None = Field(default=None, max_length=1000)
    adjustment_date: date


class StockAdjustmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    stock_item_id: str
    stock_item_name: str
    stock_item_sku: str
    base_unit_symbol: str
    current_balance: Decimal
    physical_count: Decimal
    difference: Decimal
    reason: str
    supporting_notes: str | None = None
    status: AdjustmentStatus
    adjustment_date: date
    created_by_email: str
    approved_by_email: str | None = None
    approved_at: datetime | None = None
    created_at: datetime


class ReconciliationItemOut(BaseModel):
    stock_item_id: str
    sku: str
    name: str
    balance_quantity: Decimal
    ledger_quantity: Decimal
    discrepancy: Decimal
    reconciled: bool


class ReconciliationReportOut(BaseModel):
    all_reconciled: bool
    checked_items: int
    items: List[ReconciliationItemOut]
