from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_client_ip, require_permissions
from app.core.database import get_db
from app.core.permissions import Permission
from app.models.inventory import AdjustmentStatus, MovementType
from app.models.stock_item import StockItemType
from app.models.user import User
from app.schemas.inventory_purchase import (
    InventoryItemDetailOut,
    InventoryItemRow,
    InventorySummaryOut,
    ReconciliationReportOut,
    StockAdjustmentCreate,
    StockAdjustmentOut,
    StockLedgerOut,
)
from app.schemas.master_data import PaginatedResponse
from app.services.inventory_service import (
    approve_adjustment,
    create_adjustment,
    get_inventory_item_detail,
    get_inventory_summary,
    list_adjustments,
    list_inventory_items,
    list_ledger_entries,
    to_adjustment_out,
)
from app.services.ledger_service import reconcile_stock_balances, to_ledger_out

router = APIRouter(prefix="/inventory", tags=["inventory"])


def _paged_inventory(
    db: Session,
    *,
    item_type: StockItemType | None,
    search: str | None,
    stock_status: str | None,
    sort_by: str,
    sort_dir: str,
    page: int,
    page_size: int,
) -> PaginatedResponse[InventoryItemRow]:
    items, total = list_inventory_items(
        db,
        item_type=item_type,
        search=search,
        stock_status=stock_status,
        sort_by=sort_by,
        sort_dir=sort_dir,
        page=page,
        page_size=page_size,
    )
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/summary", response_model=InventorySummaryOut)
def get_summary(
    _: User = Depends(require_permissions(Permission.INVENTORY_READ)),
    db: Session = Depends(get_db),
) -> InventorySummaryOut:
    return get_inventory_summary(db)


@router.get("/raw-materials", response_model=PaginatedResponse[InventoryItemRow])
def get_raw_material_inventory(
    search: str | None = Query(default=None),
    stock_status: str | None = Query(default=None),
    sort_by: str = Query(default="name", pattern="^(name|sku|available_quantity|stock_value)$"),
    sort_dir: str = Query(default="asc", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _: User = Depends(require_permissions(Permission.INVENTORY_READ)),
    db: Session = Depends(get_db),
) -> PaginatedResponse[InventoryItemRow]:
    return _paged_inventory(
        db,
        item_type=StockItemType.RAW_MATERIAL,
        search=search,
        stock_status=stock_status,
        sort_by=sort_by,
        sort_dir=sort_dir,
        page=page,
        page_size=page_size,
    )


@router.get("/packaging", response_model=PaginatedResponse[InventoryItemRow])
def get_packaging_inventory(
    search: str | None = Query(default=None),
    stock_status: str | None = Query(default=None),
    sort_by: str = Query(default="name", pattern="^(name|sku|available_quantity|stock_value)$"),
    sort_dir: str = Query(default="asc", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _: User = Depends(require_permissions(Permission.INVENTORY_READ)),
    db: Session = Depends(get_db),
) -> PaginatedResponse[InventoryItemRow]:
    return _paged_inventory(
        db,
        item_type=StockItemType.PACKAGING,
        search=search,
        stock_status=stock_status,
        sort_by=sort_by,
        sort_dir=sort_dir,
        page=page,
        page_size=page_size,
    )


@router.get("/finished-goods", response_model=PaginatedResponse[InventoryItemRow])
def get_finished_goods_inventory(
    search: str | None = Query(default=None),
    stock_status: str | None = Query(default=None),
    sort_by: str = Query(default="name", pattern="^(name|sku|available_quantity|stock_value)$"),
    sort_dir: str = Query(default="asc", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _: User = Depends(require_permissions(Permission.INVENTORY_READ)),
    db: Session = Depends(get_db),
) -> PaginatedResponse[InventoryItemRow]:
    return _paged_inventory(
        db,
        item_type=StockItemType.FINISHED_GOOD,
        search=search,
        stock_status=stock_status,
        sort_by=sort_by,
        sort_dir=sort_dir,
        page=page,
        page_size=page_size,
    )


@router.get("/items/{item_id}", response_model=InventoryItemDetailOut)
def get_item_detail(
    item_id: str,
    _: User = Depends(require_permissions(Permission.INVENTORY_READ)),
    db: Session = Depends(get_db),
) -> InventoryItemDetailOut:
    return get_inventory_item_detail(db, item_id)


@router.get("/reconcile", response_model=ReconciliationReportOut)
def get_reconciliation(
    _: User = Depends(require_permissions(Permission.INVENTORY_READ)),
    db: Session = Depends(get_db),
) -> ReconciliationReportOut:
    """Verify every StockBalance projection equals SUM(quantity_in - quantity_out) in StockLedger."""
    return reconcile_stock_balances(db)


@router.get("/ledger", response_model=PaginatedResponse[StockLedgerOut])
def get_stock_ledger(
    stock_item_id: str | None = Query(default=None),
    movement_type: MovementType | None = Query(default=None),
    reference_doc_id: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=30, ge=1, le=200),
    _: User = Depends(require_permissions(Permission.INVENTORY_READ)),
    db: Session = Depends(get_db),
) -> PaginatedResponse[StockLedgerOut]:
    items, total = list_ledger_entries(
        db,
        stock_item_id=stock_item_id,
        movement_type=movement_type,
        reference_doc_id=reference_doc_id,
        page=page,
        page_size=page_size,
    )
    return PaginatedResponse(
        items=[to_ledger_out(e) for e in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/ledger/{item_id}", response_model=PaginatedResponse[StockLedgerOut])
def get_item_ledger(
    item_id: str,
    movement_type: MovementType | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=30, ge=1, le=200),
    _: User = Depends(require_permissions(Permission.INVENTORY_READ)),
    db: Session = Depends(get_db),
) -> PaginatedResponse[StockLedgerOut]:
    items, total = list_ledger_entries(
        db,
        stock_item_id=item_id,
        movement_type=movement_type,
        page=page,
        page_size=page_size,
    )
    return PaginatedResponse(
        items=[to_ledger_out(e) for e in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/adjustments", response_model=PaginatedResponse[StockAdjustmentOut])
def get_adjustments(
    stock_item_id: str | None = Query(default=None),
    status_filter: AdjustmentStatus | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _: User = Depends(require_permissions(Permission.INVENTORY_READ)),
    db: Session = Depends(get_db),
) -> PaginatedResponse[StockAdjustmentOut]:
    items, total = list_adjustments(
        db,
        stock_item_id=stock_item_id,
        status_filter=status_filter,
        page=page,
        page_size=page_size,
    )
    return PaginatedResponse(
        items=[to_adjustment_out(a) for a in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/adjustments",
    response_model=StockAdjustmentOut,
    status_code=status.HTTP_201_CREATED,
)
def post_adjustment(
    payload: StockAdjustmentCreate,
    request: Request,
    actor: User = Depends(require_permissions(Permission.INVENTORY_MANAGE)),
    db: Session = Depends(get_db),
) -> StockAdjustmentOut:
    adj = create_adjustment(db, payload, actor=actor, ip_address=get_client_ip(request))
    return to_adjustment_out(adj)


@router.post("/adjustments/{adjustment_id}/approve", response_model=StockAdjustmentOut)
def post_approve_adjustment(
    adjustment_id: str,
    request: Request,
    actor: User = Depends(require_permissions(Permission.INVENTORY_MANAGE)),
    db: Session = Depends(get_db),
) -> StockAdjustmentOut:
    adj = approve_adjustment(
        db, adjustment_id, actor=actor, ip_address=get_client_ip(request)
    )
    return to_adjustment_out(adj)


@router.get("/alerts", response_model=PaginatedResponse[InventoryItemRow])
def get_low_stock_alerts(
    category: StockItemType | None = Query(default=None),
    stock_status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    _: User = Depends(require_permissions(Permission.INVENTORY_READ)),
    db: Session = Depends(get_db),
) -> PaginatedResponse[InventoryItemRow]:
    return _paged_inventory(
        db,
        item_type=category,
        search=None,
        stock_status=stock_status,
        sort_by="available_quantity",
        sort_dir="asc",
        page=page,
        page_size=page_size,
    )
