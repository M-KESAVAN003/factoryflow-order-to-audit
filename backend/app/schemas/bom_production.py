from datetime import date, datetime
from decimal import Decimal
from typing import List

from pydantic import BaseModel, ConfigDict, Field

from app.models.bom import BomStatus
from app.models.production import ProductionStatus
from app.models.stock_item import StockItemType


class BomLineInput(BaseModel):
    stock_item_id: str
    standard_quantity: Decimal = Field(gt=Decimal("0"), max_digits=18, decimal_places=6)
    unit_id: str


class BomCreate(BaseModel):
    product_id: str
    batch_size: Decimal = Field(default=Decimal("1"), gt=Decimal("0"), max_digits=18, decimal_places=6)
    expected_output: Decimal = Field(gt=Decimal("0"), max_digits=18, decimal_places=6)
    output_unit_id: str
    effective_date: date
    notes: str | None = Field(default=None, max_length=1000)
    activate: bool = False
    lines: List[BomLineInput] = Field(min_length=1)


class BomUpdate(BaseModel):
    batch_size: Decimal | None = Field(default=None, gt=Decimal("0"), max_digits=18, decimal_places=6)
    expected_output: Decimal | None = Field(default=None, gt=Decimal("0"), max_digits=18, decimal_places=6)
    output_unit_id: str | None = None
    effective_date: date | None = None
    notes: str | None = Field(default=None, max_length=1000)
    status: BomStatus | None = None
    lines: List[BomLineInput] | None = Field(default=None, min_length=1)


class BomLineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    stock_item_id: str
    stock_item_name: str
    stock_item_sku: str
    input_category: StockItemType
    standard_quantity: Decimal
    unit_id: str
    unit_symbol: str
    base_quantity: Decimal
    base_unit_symbol: str
    available_stock: Decimal


class BomOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    product_id: str
    product_name: str
    product_sku: str
    version_number: int
    batch_size: Decimal
    expected_output: Decimal
    output_unit_id: str
    output_unit_symbol: str
    effective_date: date
    status: BomStatus
    is_active: bool
    notes: str | None = None
    created_by_email: str
    created_at: datetime
    updated_at: datetime
    lines: List[BomLineOut]


class ProductionRunCreate(BaseModel):
    order_number: str = Field(min_length=3, max_length=64)
    product_id: str
    bom_id: str | None = None
    batch_number: str = Field(min_length=2, max_length=64)
    production_date: date
    planned_batches: Decimal = Field(default=Decimal("1"), gt=Decimal("0"), max_digits=18, decimal_places=6)
    variance_tolerance_pct: Decimal = Field(default=Decimal("3.00"), ge=Decimal("0"), max_digits=5, decimal_places=2)
    notes: str | None = Field(default=None, max_length=1000)


class ProductionRunUpdate(BaseModel):
    batch_number: str | None = Field(default=None, min_length=2, max_length=64)
    production_date: date | None = None
    planned_batches: Decimal | None = Field(default=None, gt=Decimal("0"), max_digits=18, decimal_places=6)
    status: ProductionStatus | None = None
    notes: str | None = Field(default=None, max_length=1000)


class MaterialConsumptionInput(BaseModel):
    stock_item_id: str
    actual_quantity: Decimal = Field(ge=Decimal("0"), max_digits=18, decimal_places=6)
    damaged_quantity: Decimal = Field(default=Decimal("0"), ge=Decimal("0"), max_digits=18, decimal_places=6)


class ProductionConsumeRequest(BaseModel):
    materials: List[MaterialConsumptionInput] = Field(min_length=1)


class ProductionOutputInput(BaseModel):
    good_quantity: Decimal = Field(ge=Decimal("0"), max_digits=18, decimal_places=6)
    damaged_packets: Decimal = Field(default=Decimal("0"), ge=Decimal("0"), max_digits=18, decimal_places=6)
    cartons_used: Decimal | None = Field(default=None, ge=Decimal("0"), max_digits=18, decimal_places=6)


class ProductionWastageInput(BaseModel):
    stock_item_id: str | None = None
    wastage_type: str = Field(min_length=2, max_length=40)
    quantity: Decimal = Field(gt=Decimal("0"), max_digits=18, decimal_places=6)
    unit_id: str | None = None
    reason: str = Field(min_length=2, max_length=250)
    notes: str | None = Field(default=None, max_length=1000)


class ProductionCancelRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


class ProductionMaterialOut(BaseModel):
    id: str
    stock_item_id: str
    stock_item_name: str
    stock_item_sku: str
    input_category: StockItemType
    unit_id: str
    unit_symbol: str
    base_unit_symbol: str
    planned_quantity: Decimal
    planned_base_quantity: Decimal
    actual_quantity: Decimal
    damaged_quantity: Decimal
    total_consumed_base_qty: Decimal
    available_stock: Decimal
    insufficient_stock: bool
    difference_qty: Decimal
    variance_pct: Decimal | None = None
    variance_status: str | None = None
    exceeds_tolerance: bool


class ProductionOutputOut(BaseModel):
    id: str
    product_id: str
    unit_symbol: str
    expected_quantity: Decimal
    good_quantity: Decimal
    damaged_packets: Decimal
    cartons_used: Decimal
    carton_capacity_packets: Decimal
    unpacked_packets: Decimal
    packaging_warning: str | None = None
    recorded_by_email: str
    recorded_at: datetime


class ProductionWastageOut(BaseModel):
    id: str
    stock_item_id: str | None = None
    stock_item_name: str | None = None
    wastage_type: str
    quantity: Decimal
    unit_symbol: str | None = None
    reason: str
    notes: str | None = None
    recorded_by_email: str
    created_at: datetime


class ProductionRunOut(BaseModel):
    id: str
    order_number: str
    product_id: str
    product_name: str
    product_sku: str
    bom_id: str
    bom_version_snapshot: int
    batch_number: str
    production_date: date
    planned_batches: Decimal
    expected_output: Decimal
    actual_good_output: Decimal
    damaged_packets: Decimal
    damaged_pouches: Decimal
    scrap_quantity: Decimal
    yield_variance_pct: Decimal | None = None
    yield_status: str
    yield_exceeds_tolerance: bool
    variance_tolerance_pct: Decimal
    packaging_warning: str | None = None
    supervisor_id: str
    supervisor_email: str
    notes: str | None = None
    status: ProductionStatus
    started_at: datetime | None = None
    completed_at: datetime | None = None
    posted_at: datetime | None = None
    created_at: datetime
    materials: List[ProductionMaterialOut]
    outputs: List[ProductionOutputOut]
    wastages: List[ProductionWastageOut]


class MaterialVarianceRow(BaseModel):
    stock_item_id: str
    material_name: str
    sku: str
    input_category: StockItemType
    unit_symbol: str
    planned_consumption: Decimal
    actual_consumption: Decimal
    damaged_quantity: Decimal
    difference: Decimal
    variance_pct: Decimal
    status: str
    exceeds_tolerance: bool


class RunVarianceReportOut(BaseModel):
    production_run_id: str
    order_number: str
    product_name: str
    tolerance_pct: Decimal
    expected_output: Decimal
    actual_good_output: Decimal
    yield_variance_pct: Decimal
    yield_status: str
    yield_exceeds_tolerance: bool
    packaging_warning: str | None = None
    materials: List[MaterialVarianceRow]


class VarianceSummaryItem(BaseModel):
    production_run_id: str
    order_number: str
    product_name: str
    production_date: date
    status: ProductionStatus
    expected_output: Decimal
    actual_good_output: Decimal
    yield_variance_pct: Decimal
    yield_status: str
    flagged_material_count: int


class VarianceSummaryOut(BaseModel):
    total_runs: int
    flagged_runs: int
    avg_yield_variance_pct: Decimal
    runs: List[VarianceSummaryItem]


class DailyProductionPoint(BaseModel):
    date: str
    planned_output: Decimal
    actual_output: Decimal
    wastage: Decimal


class ProductYieldPoint(BaseModel):
    product_name: str
    runs_count: int
    expected_output: Decimal
    actual_output: Decimal
    yield_pct: Decimal


class ProductionDashboardOut(BaseModel):
    todays_runs: int
    planned_output: Decimal
    actual_output: Decimal
    total_wastage: Decimal
    overall_yield_variance_pct: Decimal
    pending_runs: int
    active_boms: int
    daily_trend: List[DailyProductionPoint]
    product_yield: List[ProductYieldPoint]
    recent_runs: List[ProductionRunOut]
    variance_alerts: List[VarianceSummaryItem]
