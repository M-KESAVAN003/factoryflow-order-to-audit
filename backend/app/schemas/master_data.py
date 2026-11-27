from datetime import datetime
from decimal import Decimal
from typing import Generic, List, TypeVar

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.customer import CustomerType
from app.models.stock_item import StockItemType
from app.models.unit import UnitDimension

T = TypeVar("T")

GSTIN_PATTERN = r"^[0-9]{2}[A-Z0-9]{10}[0-9A-Z]{3}$"


class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    page_size: int


class UnitCreate(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    symbol: str = Field(min_length=1, max_length=20)
    dimension: UnitDimension
    is_base: bool = False
    is_active: bool = True


class UnitOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    symbol: str
    dimension: UnitDimension
    is_base: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UnitConversionCreate(BaseModel):
    from_unit_id: str
    to_unit_id: str
    product_id: str | None = None
    conversion_factor: Decimal = Field(gt=Decimal("0"), max_digits=18, decimal_places=6)
    is_active: bool = True


class UnitConversionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    from_unit_id: str
    from_unit_symbol: str
    from_unit_dimension: UnitDimension
    to_unit_id: str
    to_unit_symbol: str
    to_unit_dimension: UnitDimension
    product_id: str | None = None
    product_name: str | None = None
    conversion_factor: Decimal
    is_active: bool
    created_at: datetime


class UnitConvertRequest(BaseModel):
    quantity: Decimal = Field(gt=Decimal("0"))
    from_unit_id: str
    to_unit_id: str
    product_id: str | None = None


class UnitConvertResponse(BaseModel):
    input_quantity: Decimal
    converted_quantity: Decimal
    from_unit_symbol: str
    to_unit_symbol: str
    factor_applied: Decimal


class StockItemCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    sku: str = Field(min_length=2, max_length=64)
    item_type: StockItemType
    base_unit_id: str
    purchase_unit_id: str
    purchase_rate: Decimal = Field(ge=Decimal("0"), max_digits=14, decimal_places=4)
    reorder_level: Decimal = Field(default=Decimal("0"), ge=Decimal("0"), max_digits=14, decimal_places=4)
    description: str | None = Field(default=None, max_length=1000)
    is_active: bool = True


class StockItemUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    sku: str | None = Field(default=None, min_length=2, max_length=64)
    base_unit_id: str | None = None
    purchase_unit_id: str | None = None
    purchase_rate: Decimal | None = Field(default=None, ge=Decimal("0"), max_digits=14, decimal_places=4)
    reorder_level: Decimal | None = Field(default=None, ge=Decimal("0"), max_digits=14, decimal_places=4)
    description: str | None = Field(default=None, max_length=1000)
    is_active: bool | None = None


class StockItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    sku: str
    item_type: StockItemType
    base_unit_id: str
    base_unit_symbol: str
    purchase_unit_id: str
    purchase_unit_symbol: str
    purchase_rate: Decimal
    reorder_level: Decimal
    description: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ProductCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    sku: str = Field(min_length=2, max_length=64)
    category: str = Field(min_length=2, max_length=80)
    description: str | None = Field(default=None, max_length=1000)
    pack_size: str = Field(min_length=1, max_length=60)
    selling_price: Decimal = Field(gt=Decimal("0"), max_digits=14, decimal_places=2)
    gst_rate: Decimal = Field(ge=Decimal("0"), le=Decimal("28"), max_digits=5, decimal_places=2)
    hsn_code: str = Field(min_length=4, max_length=20)
    unit_id: str
    stock_item_id: str | None = None
    pouch_stock_item_id: str | None = None
    carton_stock_item_id: str | None = None
    packets_per_carton: int = Field(default=20, ge=1, le=10000)
    is_active: bool = True


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    sku: str | None = Field(default=None, min_length=2, max_length=64)
    category: str | None = Field(default=None, min_length=2, max_length=80)
    description: str | None = Field(default=None, max_length=1000)
    pack_size: str | None = Field(default=None, min_length=1, max_length=60)
    selling_price: Decimal | None = Field(default=None, gt=Decimal("0"), max_digits=14, decimal_places=2)
    gst_rate: Decimal | None = Field(default=None, ge=Decimal("0"), le=Decimal("28"), max_digits=5, decimal_places=2)
    hsn_code: str | None = Field(default=None, min_length=4, max_length=20)
    unit_id: str | None = None
    pouch_stock_item_id: str | None = None
    carton_stock_item_id: str | None = None
    packets_per_carton: int | None = Field(default=None, ge=1, le=10000)
    is_active: bool | None = None


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    sku: str
    category: str
    description: str | None = None
    pack_size: str
    selling_price: Decimal
    gst_rate: Decimal
    hsn_code: str
    unit_id: str
    unit_symbol: str
    stock_item_id: str
    stock_item_sku: str
    stock_item_type: StockItemType
    pouch_stock_item_id: str | None = None
    pouch_stock_item_name: str | None = None
    carton_stock_item_id: str | None = None
    carton_stock_item_name: str | None = None
    packets_per_carton: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class SupplierCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    gstin: str = Field(pattern=GSTIN_PATTERN, min_length=15, max_length=15)
    phone: str = Field(min_length=7, max_length=20)
    email: EmailStr | None = None
    address: str = Field(min_length=4, max_length=500)
    state: str = Field(min_length=2, max_length=80)
    state_code: str = Field(min_length=1, max_length=5)
    is_active: bool = True

    @field_validator("gstin", mode="before")
    @classmethod
    def normalize_gstin(cls, val: object) -> str:
        return str(val).strip().upper()


class SupplierUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    gstin: str | None = Field(default=None, pattern=GSTIN_PATTERN, min_length=15, max_length=15)
    phone: str | None = Field(default=None, min_length=7, max_length=20)
    email: EmailStr | None = None
    address: str | None = Field(default=None, min_length=4, max_length=500)
    state: str | None = Field(default=None, min_length=2, max_length=80)
    state_code: str | None = Field(default=None, min_length=1, max_length=5)
    is_active: bool | None = None

    @field_validator("gstin", mode="before")
    @classmethod
    def normalize_gstin(cls, val: object) -> str | None:
        return None if val is None else str(val).strip().upper()


class SupplierOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    gstin: str
    phone: str
    email: str | None = None
    address: str
    state: str
    state_code: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class CustomerCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    customer_type: CustomerType
    gstin: str = Field(pattern=GSTIN_PATTERN, min_length=15, max_length=15)
    phone: str = Field(min_length=7, max_length=20)
    address: str = Field(min_length=4, max_length=500)
    city: str = Field(min_length=2, max_length=80)
    state: str = Field(min_length=2, max_length=80)
    state_code: str = Field(min_length=1, max_length=5)
    assigned_salesman_id: str | None = None
    credit_limit: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0"), max_digits=14, decimal_places=2)
    is_active: bool = True

    @field_validator("gstin", mode="before")
    @classmethod
    def normalize_gstin(cls, val: object) -> str:
        return str(val).strip().upper()


class CustomerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    customer_type: CustomerType | None = None
    gstin: str | None = Field(default=None, pattern=GSTIN_PATTERN, min_length=15, max_length=15)
    phone: str | None = Field(default=None, min_length=7, max_length=20)
    address: str | None = Field(default=None, min_length=4, max_length=500)
    city: str | None = Field(default=None, min_length=2, max_length=80)
    state: str | None = Field(default=None, min_length=2, max_length=80)
    state_code: str | None = Field(default=None, min_length=1, max_length=5)
    assigned_salesman_id: str | None = None
    credit_limit: Decimal | None = Field(default=None, ge=Decimal("0"), max_digits=14, decimal_places=2)
    is_active: bool | None = None

    @field_validator("gstin", mode="before")
    @classmethod
    def normalize_gstin(cls, val: object) -> str | None:
        return None if val is None else str(val).strip().upper()


class CustomerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    customer_type: CustomerType
    gstin: str
    phone: str
    address: str
    city: str
    state: str
    state_code: str
    assigned_salesman_id: str | None = None
    assigned_salesman_name: str | None = None
    credit_limit: Decimal
    is_active: bool
    created_at: datetime
    updated_at: datetime


class MasterDataSummaryOut(BaseModel):
    products_total: int
    products_active: int
    raw_materials_total: int
    packaging_materials_total: int
    suppliers_total: int
    customers_total: int
    units_total: int
    conversions_total: int
