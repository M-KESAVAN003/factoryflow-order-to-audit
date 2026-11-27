from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Tuple

from fastapi import HTTPException, status
from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.orm import Session

from app.models.inventory import (
    AdjustmentStatus,
    MovementType,
    StockAdjustment,
    StockBalance,
    StockLedger,
)
from app.models.stock_item import StockItem, StockItemType
from app.models.user import User
from app.schemas.inventory_purchase import (
    CategorySummary,
    InventoryItemDetailOut,
    InventoryItemRow,
    InventorySummaryOut,
    StockAdjustmentCreate,
    StockAdjustmentOut,
)
from app.services.audit_service import record_audit_event
from app.services.ledger_service import apply_stock_movement, to_ledger_out

CATEGORY_LABELS = {
    StockItemType.RAW_MATERIAL: "Raw Materials",
    StockItemType.PACKAGING: "Packaging Materials",
    StockItemType.FINISHED_GOOD: "Finished Goods",
}


def compute_stock_status(available_qty: Decimal, reorder_level: Decimal) -> Tuple[str, Decimal]:
    """Classify stock alert level (RED, ORANGE, GREEN) and shortage quantity."""
    shortage = max(Decimal("0"), reorder_level - available_qty)
    if reorder_level > Decimal("0"):
        if available_qty <= reorder_level:
            return "RED", shortage
        if available_qty <= reorder_level * Decimal("1.20"):
            return "ORANGE", Decimal("0")
    return "GREEN", Decimal("0")


def _to_inventory_row(item: StockItem, balance: StockBalance | None) -> InventoryItemRow:
    qty = Decimal(balance.available_quantity) if balance else Decimal("0.000000")
    avg_cost = Decimal(balance.average_cost) if balance else Decimal("0.000000")
    val = Decimal(balance.total_value) if balance else Decimal("0.0000")
    reorder = Decimal(item.reorder_level)
    alert_status, shortage = compute_stock_status(qty, reorder)
    return InventoryItemRow(
        stock_item_id=item.id,
        name=item.name,
        sku=item.sku,
        item_type=item.item_type,
        category_label=CATEGORY_LABELS[item.item_type],
        base_unit_id=item.base_unit_id,
        base_unit_symbol=item.base_unit.symbol,
        available_quantity=qty,
        average_cost=avg_cost,
        stock_value=val,
        reorder_level=reorder,
        shortage_quantity=shortage,
        stock_status=alert_status,
        is_active=item.is_active,
        last_movement_at=balance.last_movement_at if balance else None,
    )


def list_inventory_items(
    db: Session,
    *,
    item_type: StockItemType | None = None,
    search: str | None = None,
    stock_status: str | None = None,
    sort_by: str = "name",
    sort_dir: str = "asc",
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[InventoryItemRow], int]:
    filters = []
    if item_type is not None:
        filters.append(StockItem.item_type == item_type)
    if search:
        term = f"%{search.strip()}%"
        filters.append(or_(StockItem.name.ilike(term), StockItem.sku.ilike(term)))

    col_map = {
        "name": StockItem.name,
        "sku": StockItem.sku,
        "available_quantity": func.coalesce(StockBalance.available_quantity, 0),
        "stock_value": func.coalesce(StockBalance.total_value, 0),
    }
    sort_col = col_map.get(sort_by, StockItem.name)
    order_fn = desc if sort_dir == "desc" else asc

    stmt = (
        select(StockItem, StockBalance)
        .outerjoin(StockBalance, StockBalance.stock_item_id == StockItem.id)
        .where(*filters)
        .order_by(order_fn(sort_col))
    )
    rows = [_to_inventory_row(item, bal) for item, bal in db.execute(stmt).all()]
    if stock_status:
        rows = [r for r in rows if r.stock_status == stock_status.upper()]

    total = len(rows)
    start = (page - 1) * page_size
    return rows[start : start + page_size], total


def get_inventory_summary(db: Session) -> InventorySummaryOut:
    rows, _ = list_inventory_items(db, page=1, page_size=1000)
    total_val = sum((r.stock_value for r in rows), Decimal("0.0000"))
    red_cnt = sum(1 for r in rows if r.stock_status == "RED")
    orange_cnt = sum(1 for r in rows if r.stock_status == "ORANGE")

    categories: List[CategorySummary] = []
    for cat_type in (StockItemType.RAW_MATERIAL, StockItemType.PACKAGING, StockItemType.FINISHED_GOOD):
        cat_rows = [r for r in rows if r.item_type == cat_type]
        categories.append(
            CategorySummary(
                item_type=cat_type,
                label=CATEGORY_LABELS[cat_type],
                item_count=len(cat_rows),
                total_quantity=sum((r.available_quantity for r in cat_rows), Decimal("0.000000")),
                total_value=sum((r.stock_value for r in cat_rows), Decimal("0.0000")),
                low_stock_count=sum(1 for r in cat_rows if r.stock_status in {"RED", "ORANGE"}),
            )
        )

    recent_entries = list(
        db.scalars(
            select(StockLedger).order_by(StockLedger.created_at.desc()).limit(10)
        ).all()
    )
    return InventorySummaryOut(
        total_items=len(rows),
        total_stock_value=total_val,
        low_stock_red_count=red_cnt,
        approaching_orange_count=orange_cnt,
        categories=categories,
        recent_movements=[to_ledger_out(e) for e in recent_entries],
    )


def get_inventory_item_detail(db: Session, stock_item_id: str) -> InventoryItemDetailOut:
    item = db.get(StockItem, stock_item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory item not found.")

    balance = db.scalar(select(StockBalance).where(StockBalance.stock_item_id == item.id))
    row = _to_inventory_row(item, balance)

    ledger_sum = Decimal(
        str(
            db.scalar(
                select(
                    func.coalesce(func.sum(StockLedger.quantity_in - StockLedger.quantity_out), 0)
                ).where(StockLedger.stock_item_id == item.id)
            )
        )
    ).quantize(Decimal("0.000001"))

    recent = list(
        db.scalars(
            select(StockLedger)
            .where(StockLedger.stock_item_id == item.id)
            .order_by(StockLedger.created_at.desc())
            .limit(25)
        ).all()
    )
    return InventoryItemDetailOut(
        item=row,
        ledger_sum_quantity=ledger_sum,
        reconciled=(row.available_quantity.quantize(Decimal("0.000001")) == ledger_sum),
        recent_movements=[to_ledger_out(e) for e in recent],
    )


def list_ledger_entries(
    db: Session,
    *,
    stock_item_id: str | None = None,
    movement_type: MovementType | None = None,
    reference_doc_id: str | None = None,
    page: int = 1,
    page_size: int = 30,
) -> Tuple[List[StockLedger], int]:
    filters = []
    if stock_item_id:
        filters.append(StockLedger.stock_item_id == stock_item_id)
    if movement_type is not None:
        filters.append(StockLedger.movement_type == movement_type)
    if reference_doc_id:
        filters.append(StockLedger.reference_doc_id.ilike(f"%{reference_doc_id.strip()}%"))

    total = int(db.scalar(select(func.count(StockLedger.id)).where(*filters)) or 0)
    stmt = (
        select(StockLedger)
        .where(*filters)
        .order_by(StockLedger.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(db.scalars(stmt).all()), total


def to_adjustment_out(adj: StockAdjustment) -> StockAdjustmentOut:
    return StockAdjustmentOut(
        id=adj.id,
        stock_item_id=adj.stock_item_id,
        stock_item_name=adj.stock_item.name,
        stock_item_sku=adj.stock_item.sku,
        base_unit_symbol=adj.stock_item.base_unit.symbol,
        current_balance=adj.current_balance,
        physical_count=adj.physical_count,
        difference=adj.difference,
        reason=adj.reason,
        supporting_notes=adj.supporting_notes,
        status=adj.status,
        adjustment_date=adj.adjustment_date,
        created_by_email=adj.creator.email,
        approved_by_email=adj.approver.email if adj.approver else None,
        approved_at=adj.approved_at,
        created_at=adj.created_at,
    )


def list_adjustments(
    db: Session,
    *,
    stock_item_id: str | None = None,
    status_filter: AdjustmentStatus | None = None,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[StockAdjustment], int]:
    filters = []
    if stock_item_id:
        filters.append(StockAdjustment.stock_item_id == stock_item_id)
    if status_filter is not None:
        filters.append(StockAdjustment.status == status_filter)

    total = int(db.scalar(select(func.count(StockAdjustment.id)).where(*filters)) or 0)
    stmt = (
        select(StockAdjustment)
        .where(*filters)
        .order_by(StockAdjustment.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(db.scalars(stmt).all()), total


def create_adjustment(
    db: Session,
    payload: StockAdjustmentCreate,
    *,
    actor: User,
    ip_address: str | None = None,
) -> StockAdjustment:
    item = db.get(StockItem, payload.stock_item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stock item not found.")

    balance = db.scalar(select(StockBalance).where(StockBalance.stock_item_id == item.id))
    current_qty = Decimal(balance.available_quantity) if balance else Decimal("0.000000")
    diff = (payload.physical_count - current_qty).quantize(Decimal("0.000001"))

    if diff == Decimal("0.000000"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Physical count matches current stock balance; no adjustment required.",
        )

    adj = StockAdjustment(
        stock_item_id=item.id,
        current_balance=current_qty,
        physical_count=payload.physical_count,
        difference=diff,
        reason=payload.reason.strip(),
        supporting_notes=payload.supporting_notes.strip() if payload.supporting_notes else None,
        status=AdjustmentStatus.PENDING,
        adjustment_date=payload.adjustment_date,
        created_by=actor.id,
    )
    db.add(adj)
    db.flush()

    record_audit_event(
        db,
        actor_id=actor.id,
        actor_email=actor.email,
        actor_role=actor.role.value,
        action="inventory.adjustment_created",
        resource_type="stock_adjustment",
        resource_id=adj.id,
        details=f"{item.sku} diff={diff} reason={adj.reason}",
        ip_address=ip_address,
        commit=False,
    )
    db.commit()
    db.refresh(adj)
    return adj


def approve_adjustment(
    db: Session,
    adjustment_id: str,
    *,
    actor: User,
    ip_address: str | None = None,
) -> StockAdjustment:
    adj = db.get(StockAdjustment, adjustment_id)
    if not adj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Adjustment not found.")
    if adj.status == AdjustmentStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Stock adjustment has already been approved and posted.",
        )

    item = db.get(StockItem, adj.stock_item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stock item not found.")

    diff = Decimal(adj.difference)
    if diff > Decimal("0"):
        apply_stock_movement(
            db,
            stock_item=item,
            movement_type=MovementType.STOCK_ADJUSTMENT,
            quantity_in=diff,
            unit_cost=Decimal(item.purchase_rate),
            reference_doc_type="STOCK_ADJUSTMENT",
            reference_doc_id=adj.id,
            notes=f"Adjustment approved: {adj.reason}",
            created_by=actor.id,
        )
    else:
        apply_stock_movement(
            db,
            stock_item=item,
            movement_type=MovementType.STOCK_ADJUSTMENT,
            quantity_out=abs(diff),
            reference_doc_type="STOCK_ADJUSTMENT",
            reference_doc_id=adj.id,
            notes=f"Adjustment approved: {adj.reason}",
            created_by=actor.id,
        )

    adj.status = AdjustmentStatus.APPROVED
    adj.approved_by = actor.id
    adj.approved_at = datetime.now(timezone.utc)

    record_audit_event(
        db,
        actor_id=actor.id,
        actor_email=actor.email,
        actor_role=actor.role.value,
        action="inventory.adjustment_approved",
        resource_type="stock_adjustment",
        resource_id=adj.id,
        details=f"Approved {item.sku} adjustment ({adj.difference})",
        ip_address=ip_address,
        commit=False,
    )
    db.commit()
    db.refresh(adj)
    return adj
