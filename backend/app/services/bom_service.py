from decimal import Decimal, ROUND_HALF_UP
from typing import List, Tuple

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.bom import BomHeader, BomLine, BomStatus
from app.models.inventory import StockBalance
from app.models.product import Product
from app.models.stock_item import StockItem, StockItemType
from app.models.unit import Unit
from app.models.user import User
from app.schemas.bom_production import BomCreate, BomLineInput, BomLineOut, BomOut, BomUpdate
from app.services.audit_service import record_audit_event
from app.services.unit_service import convert_quantity

QTY_PREC = Decimal("0.000001")


def to_bom_out(db: Session, bom: BomHeader) -> BomOut:
    item_ids = [line.stock_item_id for line in bom.lines]
    balances = {}
    if item_ids:
        balances = {
            b.stock_item_id: Decimal(b.available_quantity)
            for b in db.scalars(
                select(StockBalance).where(StockBalance.stock_item_id.in_(item_ids))
            ).all()
        }

    return BomOut(
        id=bom.id,
        product_id=bom.product_id,
        product_name=bom.product.name,
        product_sku=bom.product.sku,
        version_number=bom.version_number,
        batch_size=bom.batch_size,
        expected_output=bom.expected_output,
        output_unit_id=bom.output_unit_id,
        output_unit_symbol=bom.output_unit.symbol,
        effective_date=bom.effective_date,
        status=bom.status,
        is_active=bom.is_active,
        notes=bom.notes,
        created_by_email=bom.creator.email,
        created_at=bom.created_at,
        updated_at=bom.updated_at,
        lines=[
            BomLineOut(
                id=line.id,
                stock_item_id=line.stock_item_id,
                stock_item_name=line.stock_item.name,
                stock_item_sku=line.stock_item.sku,
                input_category=line.input_category,
                standard_quantity=line.standard_quantity,
                unit_id=line.unit_id,
                unit_symbol=line.unit.symbol,
                base_quantity=line.base_quantity,
                base_unit_symbol=line.stock_item.base_unit.symbol,
                available_stock=balances.get(line.stock_item_id, Decimal("0.000000")),
            )
            for line in bom.lines
        ],
    )


def _build_bom_lines(db: Session, product_id: str, raw_lines: List[BomLineInput]) -> List[BomLine]:
    seen_items = set()
    built: List[BomLine] = []
    for row in raw_lines:
        if row.stock_item_id in seen_items:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Duplicate input material in BOM lines.",
            )
        seen_items.add(row.stock_item_id)

        stock_item = db.get(StockItem, row.stock_item_id)
        if not stock_item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="BOM input stock item not found.")
        if stock_item.item_type not in {StockItemType.RAW_MATERIAL, StockItemType.PACKAGING}:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="BOM inputs must be RAW_MATERIAL or PACKAGING items.",
            )
        unit = db.get(Unit, row.unit_id)
        if not unit:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="BOM line unit not found.")

        conv = convert_quantity(
            db,
            quantity=row.standard_quantity,
            from_unit_id=unit.id,
            to_unit_id=stock_item.base_unit_id,
            product_id=product_id,
        )
        base_qty = conv.converted_quantity.quantize(QTY_PREC, rounding=ROUND_HALF_UP)

        built.append(
            BomLine(
                stock_item_id=stock_item.id,
                input_category=stock_item.item_type,
                standard_quantity=row.standard_quantity,
                unit_id=unit.id,
                base_quantity=base_qty,
            )
        )
    return built


def _deactivate_sibling_boms(db: Session, product_id: str, keep_bom_id: str) -> None:
    siblings = list(
        db.scalars(
            select(BomHeader).where(
                BomHeader.product_id == product_id,
                BomHeader.id != keep_bom_id,
                BomHeader.is_active.is_(True),
            )
        ).all()
    )
    for sib in siblings:
        sib.is_active = False
        if sib.status == BomStatus.ACTIVE:
            sib.status = BomStatus.INACTIVE


def list_boms(
    db: Session,
    *,
    product_id: str | None = None,
    status_filter: BomStatus | None = None,
    is_active: bool | None = None,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[BomHeader], int]:
    filters = []
    if product_id:
        filters.append(BomHeader.product_id == product_id)
    if status_filter is not None:
        filters.append(BomHeader.status == status_filter)
    if is_active is not None:
        filters.append(BomHeader.is_active.is_(is_active))

    total = int(db.scalar(select(func.count(BomHeader.id)).where(*filters)) or 0)
    stmt = (
        select(BomHeader)
        .where(*filters)
        .order_by(BomHeader.created_at.desc(), BomHeader.version_number.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(db.scalars(stmt).unique().all()), total


def get_bom_or_404(db: Session, bom_id: str) -> BomHeader:
    bom = db.get(BomHeader, bom_id)
    if not bom:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="BOM not found.")
    return bom


def get_bom_versions(db: Session, bom_id: str) -> List[BomHeader]:
    bom = get_bom_or_404(db, bom_id)
    stmt = (
        select(BomHeader)
        .where(BomHeader.product_id == bom.product_id)
        .order_by(BomHeader.version_number.desc())
    )
    return list(db.scalars(stmt).unique().all())


def create_bom(
    db: Session,
    payload: BomCreate,
    *,
    actor: User,
    ip_address: str | None = None,
) -> BomHeader:
    product = db.get(Product, payload.product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")
    if not db.get(Unit, payload.output_unit_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Output unit not found.")

    max_ver = db.scalar(
        select(func.coalesce(func.max(BomHeader.version_number), 0)).where(
            BomHeader.product_id == product.id
        )
    )
    next_version = int(max_ver or 0) + 1
    lines = _build_bom_lines(db, product.id, payload.lines)

    bom = BomHeader(
        product_id=product.id,
        version_number=next_version,
        batch_size=payload.batch_size,
        expected_output=payload.expected_output,
        output_unit_id=payload.output_unit_id,
        effective_date=payload.effective_date,
        status=BomStatus.ACTIVE if payload.activate else BomStatus.DRAFT,
        is_active=payload.activate,
        notes=payload.notes.strip() if payload.notes else None,
        created_by=actor.id,
        lines=lines,
    )
    db.add(bom)
    db.flush()

    if payload.activate:
        _deactivate_sibling_boms(db, product.id, bom.id)

    record_audit_event(
        db,
        actor_id=actor.id,
        actor_email=actor.email,
        actor_role=actor.role.value,
        action="bom.created",
        resource_type="bom",
        resource_id=bom.id,
        details=f"{product.sku} BOM v{next_version} (active={bom.is_active})",
        ip_address=ip_address,
        commit=False,
    )
    db.commit()
    db.refresh(bom)
    return bom


def update_bom(
    db: Session,
    bom_id: str,
    payload: BomUpdate,
    *,
    actor: User,
    ip_address: str | None = None,
) -> BomHeader:
    bom = get_bom_or_404(db, bom_id)

    # Preserve immutability of lines/quantities once activated; allow status toggling (ACTIVE <-> INACTIVE)
    is_editing_spec = any(
        val is not None
        for val in (
            payload.batch_size,
            payload.expected_output,
            payload.output_unit_id,
            payload.effective_date,
            payload.lines,
        )
    )
    if is_editing_spec and bom.status != BomStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only DRAFT BOMs can have quantities or lines edited. Create a new BOM version instead.",
        )

    if payload.batch_size is not None:
        bom.batch_size = payload.batch_size
    if payload.expected_output is not None:
        bom.expected_output = payload.expected_output
    if payload.output_unit_id is not None:
        if not db.get(Unit, payload.output_unit_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Output unit not found.")
        bom.output_unit_id = payload.output_unit_id
    if payload.effective_date is not None:
        bom.effective_date = payload.effective_date
    if payload.notes is not None:
        bom.notes = payload.notes.strip() or None
    if payload.lines is not None:
        built_lines = _build_bom_lines(db, bom.product_id, payload.lines)
        bom.lines.clear()
        db.flush()
        bom.lines.extend(built_lines)

    if payload.status is not None:
        bom.status = payload.status
        bom.is_active = payload.status == BomStatus.ACTIVE
        if bom.is_active:
            _deactivate_sibling_boms(db, bom.product_id, bom.id)

    record_audit_event(
        db,
        actor_id=actor.id,
        actor_email=actor.email,
        actor_role=actor.role.value,
        action="bom.updated",
        resource_type="bom",
        resource_id=bom.id,
        details=f"Updated BOM v{bom.version_number} status={bom.status.value}",
        ip_address=ip_address,
        commit=False,
    )
    db.commit()
    db.refresh(bom)
    return bom
