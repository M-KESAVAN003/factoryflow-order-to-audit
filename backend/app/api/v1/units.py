from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_client_ip, require_permissions
from app.core.database import get_db
from app.core.permissions import Permission
from app.models.customer import Customer
from app.models.product import Product
from app.models.stock_item import StockItem, StockItemType
from app.models.supplier import Supplier
from app.models.unit import Unit, UnitConversion
from app.models.user import User
from app.schemas.master_data import (
    MasterDataSummaryOut,
    PaginatedResponse,
    UnitConversionCreate,
    UnitConversionOut,
    UnitConvertRequest,
    UnitConvertResponse,
    UnitCreate,
    UnitOut,
)
from app.services.unit_service import (
    convert_quantity,
    create_unit,
    create_unit_conversion,
    list_unit_conversions,
    list_units,
    to_conversion_out,
)

router = APIRouter(tags=["units"])


@router.get("/units", response_model=PaginatedResponse[UnitOut])
def get_units(
    search: str | None = Query(default=None),
    dimension: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    sort_by: str = Query(default="symbol", pattern="^(symbol|name|dimension|created_at)$"),
    sort_dir: str = Query(default="asc", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    _: User = Depends(require_permissions(Permission.UNITS_READ)),
    db: Session = Depends(get_db),
) -> PaginatedResponse[UnitOut]:
    items, total = list_units(
        db,
        search=search,
        dimension=dimension,
        is_active=is_active,
        sort_by=sort_by,
        sort_dir=sort_dir,
        page=page,
        page_size=page_size,
    )
    return PaginatedResponse(
        items=[UnitOut.model_validate(u) for u in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/units", response_model=UnitOut, status_code=status.HTTP_201_CREATED)
def post_unit(
    payload: UnitCreate,
    request: Request,
    actor: User = Depends(require_permissions(Permission.UNITS_MANAGE)),
    db: Session = Depends(get_db),
) -> UnitOut:
    unit = create_unit(db, payload, actor=actor, ip_address=get_client_ip(request))
    return UnitOut.model_validate(unit)


@router.get("/unit-conversions", response_model=PaginatedResponse[UnitConversionOut])
def get_unit_conversions(
    product_id: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    _: User = Depends(require_permissions(Permission.UNITS_READ)),
    db: Session = Depends(get_db),
) -> PaginatedResponse[UnitConversionOut]:
    items, total = list_unit_conversions(
        db, product_id=product_id, page=page, page_size=page_size
    )
    return PaginatedResponse(
        items=[to_conversion_out(c) for c in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/unit-conversions",
    response_model=UnitConversionOut,
    status_code=status.HTTP_201_CREATED,
)
def post_unit_conversion(
    payload: UnitConversionCreate,
    request: Request,
    actor: User = Depends(require_permissions(Permission.UNITS_MANAGE)),
    db: Session = Depends(get_db),
) -> UnitConversionOut:
    conv = create_unit_conversion(
        db, payload, actor=actor, ip_address=get_client_ip(request)
    )
    return to_conversion_out(conv)


@router.post("/unit-conversions/convert", response_model=UnitConvertResponse)
def post_convert_quantity(
    payload: UnitConvertRequest,
    _: User = Depends(require_permissions(Permission.UNITS_READ)),
    db: Session = Depends(get_db),
) -> UnitConvertResponse:
    """Validate and convert a quantity using Decimal arithmetic."""
    return convert_quantity(
        db,
        quantity=payload.quantity,
        from_unit_id=payload.from_unit_id,
        to_unit_id=payload.to_unit_id,
        product_id=payload.product_id,
    )


@router.get("/master-data/summary", response_model=MasterDataSummaryOut)
def get_master_data_summary(
    _: User = Depends(require_permissions(Permission.DASHBOARD_VIEW)),
    db: Session = Depends(get_db),
) -> MasterDataSummaryOut:
    """Return live database counts for the Master Data Dashboard."""
    return MasterDataSummaryOut(
        products_total=int(db.scalar(select(func.count(Product.id))) or 0),
        products_active=int(
            db.scalar(select(func.count(Product.id)).where(Product.is_active.is_(True))) or 0
        ),
        raw_materials_total=int(
            db.scalar(
                select(func.count(StockItem.id)).where(
                    StockItem.item_type == StockItemType.RAW_MATERIAL
                )
            )
            or 0
        ),
        packaging_materials_total=int(
            db.scalar(
                select(func.count(StockItem.id)).where(
                    StockItem.item_type == StockItemType.PACKAGING
                )
            )
            or 0
        ),
        suppliers_total=int(db.scalar(select(func.count(Supplier.id))) or 0),
        customers_total=int(db.scalar(select(func.count(Customer.id))) or 0),
        units_total=int(db.scalar(select(func.count(Unit.id))) or 0),
        conversions_total=int(db.scalar(select(func.count(UnitConversion.id))) or 0),
    )
