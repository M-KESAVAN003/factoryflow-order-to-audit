from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_client_ip, require_permissions
from app.core.database import get_db
from app.core.permissions import Permission
from app.models.stock_item import StockItemType
from app.models.user import User
from app.schemas.master_data import (
    PaginatedResponse,
    StockItemCreate,
    StockItemOut,
    StockItemUpdate,
)
from app.services.stock_item_service import (
    create_stock_item,
    get_stock_item_or_404,
    list_stock_items,
    to_stock_item_out,
    update_stock_item,
)

router = APIRouter(tags=["stock-items"])


def _query_stock_items(
    db: Session,
    *,
    item_type: StockItemType | None,
    search: str | None,
    is_active: bool | None,
    sort_by: str,
    sort_dir: str,
    page: int,
    page_size: int,
) -> PaginatedResponse[StockItemOut]:
    items, total = list_stock_items(
        db,
        item_type=item_type,
        search=search,
        is_active=is_active,
        sort_by=sort_by,
        sort_dir=sort_dir,
        page=page,
        page_size=page_size,
    )
    return PaginatedResponse(
        items=[to_stock_item_out(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/stock-items", response_model=PaginatedResponse[StockItemOut])
def get_stock_items(
    item_type: StockItemType | None = Query(default=None),
    search: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    sort_by: str = Query(default="name", pattern="^(name|sku|purchase_rate|created_at)$"),
    sort_dir: str = Query(default="asc", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _: User = Depends(require_permissions(Permission.STOCK_ITEMS_READ)),
    db: Session = Depends(get_db),
) -> PaginatedResponse[StockItemOut]:
    return _query_stock_items(
        db,
        item_type=item_type,
        search=search,
        is_active=is_active,
        sort_by=sort_by,
        sort_dir=sort_dir,
        page=page,
        page_size=page_size,
    )


@router.post("/stock-items", response_model=StockItemOut, status_code=status.HTTP_201_CREATED)
def post_stock_item(
    payload: StockItemCreate,
    request: Request,
    actor: User = Depends(require_permissions(Permission.STOCK_ITEMS_MANAGE)),
    db: Session = Depends(get_db),
) -> StockItemOut:
    item = create_stock_item(db, payload, actor=actor, ip_address=get_client_ip(request))
    return to_stock_item_out(item)


@router.get("/stock-items/{item_id}", response_model=StockItemOut)
def get_stock_item(
    item_id: str,
    _: User = Depends(require_permissions(Permission.STOCK_ITEMS_READ)),
    db: Session = Depends(get_db),
) -> StockItemOut:
    return to_stock_item_out(get_stock_item_or_404(db, item_id))


@router.put("/stock-items/{item_id}", response_model=StockItemOut)
def put_stock_item(
    item_id: str,
    payload: StockItemUpdate,
    request: Request,
    actor: User = Depends(require_permissions(Permission.STOCK_ITEMS_MANAGE)),
    db: Session = Depends(get_db),
) -> StockItemOut:
    item = update_stock_item(
        db, item_id, payload, actor=actor, ip_address=get_client_ip(request)
    )
    return to_stock_item_out(item)


@router.get("/raw-materials", response_model=PaginatedResponse[StockItemOut])
def get_raw_materials(
    search: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    sort_by: str = Query(default="name", pattern="^(name|sku|purchase_rate|created_at)$"),
    sort_dir: str = Query(default="asc", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _: User = Depends(require_permissions(Permission.STOCK_ITEMS_READ)),
    db: Session = Depends(get_db),
) -> PaginatedResponse[StockItemOut]:
    """Dedicated raw materials view over the shared StockItem master."""
    return _query_stock_items(
        db,
        item_type=StockItemType.RAW_MATERIAL,
        search=search,
        is_active=is_active,
        sort_by=sort_by,
        sort_dir=sort_dir,
        page=page,
        page_size=page_size,
    )


@router.get("/packaging-materials", response_model=PaginatedResponse[StockItemOut])
def get_packaging_materials(
    search: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    sort_by: str = Query(default="name", pattern="^(name|sku|purchase_rate|created_at)$"),
    sort_dir: str = Query(default="asc", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _: User = Depends(require_permissions(Permission.STOCK_ITEMS_READ)),
    db: Session = Depends(get_db),
) -> PaginatedResponse[StockItemOut]:
    """Dedicated packaging materials view over the shared StockItem master."""
    return _query_stock_items(
        db,
        item_type=StockItemType.PACKAGING,
        search=search,
        is_active=is_active,
        sort_by=sort_by,
        sort_dir=sort_dir,
        page=page,
        page_size=page_size,
    )
