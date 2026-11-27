from typing import List, Tuple

from fastapi import HTTPException, status
from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.orm import Session

from app.models.stock_item import StockItem, StockItemType
from app.models.unit import Unit
from app.models.user import User
from app.schemas.master_data import StockItemCreate, StockItemOut, StockItemUpdate
from app.services.audit_service import record_audit_event


def to_stock_item_out(item: StockItem) -> StockItemOut:
    return StockItemOut(
        id=item.id,
        name=item.name,
        sku=item.sku,
        item_type=item.item_type,
        base_unit_id=item.base_unit_id,
        base_unit_symbol=item.base_unit.symbol,
        purchase_unit_id=item.purchase_unit_id,
        purchase_unit_symbol=item.purchase_unit.symbol,
        purchase_rate=item.purchase_rate,
        reorder_level=item.reorder_level,
        description=item.description,
        is_active=item.is_active,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def list_stock_items(
    db: Session,
    *,
    item_type: StockItemType | None = None,
    search: str | None = None,
    is_active: bool | None = None,
    sort_by: str = "name",
    sort_dir: str = "asc",
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[StockItem], int]:
    filters = []
    if item_type is not None:
        filters.append(StockItem.item_type == item_type)
    if search:
        term = f"%{search.strip()}%"
        filters.append(or_(StockItem.name.ilike(term), StockItem.sku.ilike(term)))
    if is_active is not None:
        filters.append(StockItem.is_active.is_(is_active))

    total = int(db.scalar(select(func.count(StockItem.id)).where(*filters)) or 0)
    col = getattr(StockItem, sort_by, StockItem.name)
    order_fn = desc if sort_dir == "desc" else asc
    stmt = (
        select(StockItem)
        .where(*filters)
        .order_by(order_fn(col))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(db.scalars(stmt).all()), total


def get_stock_item_or_404(db: Session, item_id: str) -> StockItem:
    item = db.get(StockItem, item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stock item not found.")
    return item


def _validate_unit_pair(db: Session, base_unit_id: str, purchase_unit_id: str) -> None:
    base_unit = db.get(Unit, base_unit_id)
    purchase_unit = db.get(Unit, purchase_unit_id)
    if not base_unit or not purchase_unit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Base unit or purchase unit not found.",
        )
    if base_unit.dimension != purchase_unit.dimension:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Base unit '{base_unit.symbol}' ({base_unit.dimension.value}) and "
                f"purchase unit '{purchase_unit.symbol}' ({purchase_unit.dimension.value}) must share the same dimension."
            ),
        )


def create_stock_item(
    db: Session,
    payload: StockItemCreate,
    *,
    actor: User | None = None,
    ip_address: str | None = None,
) -> StockItem:
    sku_norm = payload.sku.strip().upper()
    if db.scalar(select(StockItem).where(func.upper(StockItem.sku) == sku_norm)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Stock item SKU '{sku_norm}' already exists.",
        )

    _validate_unit_pair(db, payload.base_unit_id, payload.purchase_unit_id)

    item = StockItem(
        name=payload.name.strip(),
        sku=sku_norm,
        item_type=payload.item_type,
        base_unit_id=payload.base_unit_id,
        purchase_unit_id=payload.purchase_unit_id,
        purchase_rate=payload.purchase_rate,
        reorder_level=payload.reorder_level,
        description=payload.description.strip() if payload.description else None,
        is_active=payload.is_active,
    )
    db.add(item)
    db.flush()

    record_audit_event(
        db,
        actor_id=actor.id if actor else None,
        actor_email=actor.email if actor else "system@factoryflow.io",
        actor_role=actor.role.value if actor else "system",
        action="master.stock_item_created",
        resource_type="stock_item",
        resource_id=item.id,
        details=f"Created {item.item_type.value} {item.sku} ({item.name})",
        ip_address=ip_address,
        commit=False,
    )
    db.commit()
    db.refresh(item)
    return item


def update_stock_item(
    db: Session,
    item_id: str,
    payload: StockItemUpdate,
    *,
    actor: User,
    ip_address: str | None = None,
) -> StockItem:
    item = get_stock_item_or_404(db, item_id)

    if payload.sku is not None:
        sku_norm = payload.sku.strip().upper()
        conflict = db.scalar(
            select(StockItem).where(
                func.upper(StockItem.sku) == sku_norm,
                StockItem.id != item.id,
            )
        )
        if conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Stock item SKU '{sku_norm}' already exists.",
            )
        item.sku = sku_norm

    next_base = payload.base_unit_id or item.base_unit_id
    next_purchase = payload.purchase_unit_id or item.purchase_unit_id
    _validate_unit_pair(db, next_base, next_purchase)
    item.base_unit_id = next_base
    item.purchase_unit_id = next_purchase

    if payload.name is not None:
        item.name = payload.name.strip()
    if payload.purchase_rate is not None:
        item.purchase_rate = payload.purchase_rate
    if payload.reorder_level is not None:
        item.reorder_level = payload.reorder_level
    if payload.description is not None:
        item.description = payload.description.strip() or None
    if payload.is_active is not None:
        item.is_active = payload.is_active

    record_audit_event(
        db,
        actor_id=actor.id,
        actor_email=actor.email,
        actor_role=actor.role.value,
        action="master.stock_item_updated",
        resource_type="stock_item",
        resource_id=item.id,
        details=f"Updated stock item {item.sku}",
        ip_address=ip_address,
        commit=False,
    )
    db.commit()
    db.refresh(item)
    return item
