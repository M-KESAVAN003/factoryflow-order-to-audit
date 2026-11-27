from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Tuple

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.bom import BomHeader, BomStatus
from app.models.inventory import MovementType, StockBalance
from app.models.product import Product
from app.models.production import (
    ProductionMaterial,
    ProductionOutput,
    ProductionRun,
    ProductionStatus,
    ProductionWastage,
)
from app.models.stock_item import StockItem, StockItemType
from app.models.unit import Unit
from app.models.user import User
from app.schemas.bom_production import (
    DailyProductionPoint,
    MaterialVarianceRow,
    ProductionConsumeRequest,
    ProductionDashboardOut,
    ProductionMaterialOut,
    ProductionOutputInput,
    ProductionOutputOut,
    ProductionRunCreate,
    ProductionRunOut,
    ProductionRunUpdate,
    ProductionWastageInput,
    ProductionWastageOut,
    ProductYieldPoint,
    RunVarianceReportOut,
    VarianceSummaryItem,
    VarianceSummaryOut,
)
from app.services.audit_service import record_audit_event
from app.services.ledger_service import apply_stock_movement
from app.services.unit_service import convert_quantity

QTY_PREC = Decimal("0.000001")
PCT_PREC = Decimal("0.0001")


def classify_variance(
    actual: Decimal, planned: Decimal, tolerance_pct: Decimal
) -> Tuple[Decimal, str, bool]:
    """Compute percentage variance and Green/Orange/Red status against tolerance."""
    if planned == Decimal("0"):
        return Decimal("0.0000"), "GREEN", False
    pct = (((actual - planned) / planned) * Decimal("100")).quantize(
        PCT_PREC, rounding=ROUND_HALF_UP
    )
    abs_pct = abs(pct)
    exceeds = abs_pct > tolerance_pct
    if exceeds:
        return pct, "RED", True
    if abs_pct >= (tolerance_pct * Decimal("0.75")).quantize(PCT_PREC):
        return pct, "ORANGE", False
    return pct, "GREEN", False


def _evaluate_packaging_capacity(
    product: Product, good_packets: Decimal, cartons_used: Decimal
) -> Tuple[Decimal, Decimal, str | None]:
    per_carton = Decimal(product.packets_per_carton or 20)
    capacity = (cartons_used * per_carton).quantize(QTY_PREC, rounding=ROUND_HALF_UP)
    unpacked = max(Decimal("0.000000"), (good_packets - capacity).quantize(QTY_PREC))
    warning: str | None = None
    if unpacked > Decimal("0"):
        warning = (
            f"{int(cartons_used) if cartons_used == int(cartons_used) else cartons_used} cartons hold "
            f"{int(capacity) if capacity == int(capacity) else capacity} packets. "
            f"{int(good_packets) if good_packets == int(good_packets) else good_packets} packets were produced. "
            f"Therefore, {int(unpacked) if unpacked == int(unpacked) else unpacked} packets remain unpacked."
        )
    return capacity, unpacked, warning


def _available_stock_map(db: Session, stock_item_ids: List[str]) -> Dict[str, Decimal]:
    if not stock_item_ids:
        return {}
    rows = db.scalars(
        select(StockBalance).where(StockBalance.stock_item_id.in_(stock_item_ids))
    ).all()
    return {b.stock_item_id: Decimal(b.available_quantity) for b in rows}


def to_production_run_out(db: Session, run: ProductionRun) -> ProductionRunOut:
    balances = _available_stock_map(db, [m.stock_item_id for m in run.materials])
    tolerance = Decimal(run.variance_tolerance_pct)

    yield_pct = Decimal("0.0000")
    yield_status = "GREEN"
    yield_exceeds = False
    if run.status in {ProductionStatus.COMPLETED, ProductionStatus.POSTED} or run.outputs:
        yield_pct, yield_status, yield_exceeds = classify_variance(
            Decimal(run.actual_good_output), Decimal(run.expected_output), tolerance
        )

    latest_warning = run.outputs[-1].packaging_warning if run.outputs else None

    materials_out: List[ProductionMaterialOut] = []
    for mat in run.materials:
        avail = balances.get(mat.stock_item_id, Decimal("0.000000"))
        planned_base = Decimal(mat.planned_base_quantity)
        consumed_base = Decimal(mat.total_consumed_base_qty)
        diff = (consumed_base - planned_base).quantize(QTY_PREC, rounding=ROUND_HALF_UP)

        var_pct = mat.variance_pct
        var_status = mat.variance_status
        exceeds = False
        if var_pct is not None:
            exceeds = abs(Decimal(var_pct)) > tolerance

        materials_out.append(
            ProductionMaterialOut(
                id=mat.id,
                stock_item_id=mat.stock_item_id,
                stock_item_name=mat.stock_item.name,
                stock_item_sku=mat.stock_item.sku,
                input_category=mat.input_category,
                unit_id=mat.unit_id,
                unit_symbol=mat.unit.symbol,
                base_unit_symbol=mat.stock_item.base_unit.symbol,
                planned_quantity=mat.planned_quantity,
                planned_base_quantity=planned_base,
                actual_quantity=mat.actual_quantity,
                damaged_quantity=mat.damaged_quantity,
                total_consumed_base_qty=consumed_base,
                available_stock=avail,
                insufficient_stock=(avail < planned_base),
                difference_qty=diff,
                variance_pct=var_pct,
                variance_status=var_status,
                exceeds_tolerance=exceeds,
            )
        )

    return ProductionRunOut(
        id=run.id,
        order_number=run.order_number,
        product_id=run.product_id,
        product_name=run.product.name,
        product_sku=run.product.sku,
        bom_id=run.bom_id,
        bom_version_snapshot=run.bom_version_snapshot,
        batch_number=run.batch_number,
        production_date=run.production_date,
        planned_batches=run.planned_batches,
        expected_output=run.expected_output,
        actual_good_output=run.actual_good_output,
        damaged_packets=run.damaged_packets,
        damaged_pouches=run.damaged_pouches,
        scrap_quantity=run.scrap_quantity,
        yield_variance_pct=yield_pct if run.yield_variance_pct is not None else None,
        yield_status=yield_status,
        yield_exceeds_tolerance=yield_exceeds,
        variance_tolerance_pct=tolerance,
        packaging_warning=latest_warning,
        supervisor_id=run.supervisor_id,
        supervisor_email=run.supervisor.email,
        notes=run.notes,
        status=run.status,
        started_at=run.started_at,
        completed_at=run.completed_at,
        posted_at=run.posted_at,
        created_at=run.created_at,
        materials=materials_out,
        outputs=[
            ProductionOutputOut(
                id=o.id,
                product_id=o.product_id,
                unit_symbol=o.unit.symbol,
                expected_quantity=o.expected_quantity,
                good_quantity=o.good_quantity,
                damaged_packets=o.damaged_packets,
                cartons_used=o.cartons_used,
                carton_capacity_packets=o.carton_capacity_packets,
                unpacked_packets=o.unpacked_packets,
                packaging_warning=o.packaging_warning,
                recorded_by_email=o.recorder.email,
                recorded_at=o.recorded_at,
            )
            for o in run.outputs
        ],
        wastages=[
            ProductionWastageOut(
                id=w.id,
                stock_item_id=w.stock_item_id,
                stock_item_name=w.stock_item.name if w.stock_item else None,
                wastage_type=w.wastage_type,
                quantity=w.quantity,
                unit_symbol=w.unit.symbol if w.unit else None,
                reason=w.reason,
                notes=w.notes,
                recorded_by_email=w.recorder.email,
                created_at=w.created_at,
            )
            for w in run.wastages
        ],
    )


def _resolve_bom_for_run(db: Session, product_id: str, bom_id: str | None) -> BomHeader:
    if bom_id:
        bom = db.get(BomHeader, bom_id)
        if not bom or bom.product_id != product_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Specified BOM version was not found for this product.",
            )
        return bom

    bom = db.scalar(
        select(BomHeader).where(
            BomHeader.product_id == product_id,
            BomHeader.is_active.is_(True),
        )
    )
    if not bom:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No active BOM version exists for this product.",
        )
    return bom


def _build_planned_materials(bom: BomHeader, planned_batches: Decimal) -> List[ProductionMaterial]:
    ratio = (planned_batches / Decimal(bom.batch_size)).quantize(QTY_PREC, rounding=ROUND_HALF_UP)
    rows: List[ProductionMaterial] = []
    for line in bom.lines:
        planned_qty = (Decimal(line.standard_quantity) * ratio).quantize(
            QTY_PREC, rounding=ROUND_HALF_UP
        )
        planned_base = (Decimal(line.base_quantity) * ratio).quantize(
            QTY_PREC, rounding=ROUND_HALF_UP
        )
        rows.append(
            ProductionMaterial(
                stock_item_id=line.stock_item_id,
                input_category=line.input_category,
                unit_id=line.unit_id,
                planned_quantity=planned_qty,
                planned_base_quantity=planned_base,
                actual_quantity=Decimal("0.000000"),
                damaged_quantity=Decimal("0.000000"),
                total_consumed_base_qty=Decimal("0.000000"),
            )
        )
    return rows


def list_production_runs(
    db: Session,
    *,
    search: str | None = None,
    product_id: str | None = None,
    status_filter: ProductionStatus | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[ProductionRun], int]:
    filters = []
    if search:
        term = f"%{search.strip()}%"
        filters.append(
            or_(
                ProductionRun.order_number.ilike(term),
                ProductionRun.batch_number.ilike(term),
                ProductionRun.product.has(Product.name.ilike(term)),
            )
        )
    if product_id:
        filters.append(ProductionRun.product_id == product_id)
    if status_filter is not None:
        filters.append(ProductionRun.status == status_filter)
    if date_from is not None:
        filters.append(ProductionRun.production_date >= date_from)
    if date_to is not None:
        filters.append(ProductionRun.production_date <= date_to)

    total = int(db.scalar(select(func.count(ProductionRun.id)).where(*filters)) or 0)
    stmt = (
        select(ProductionRun)
        .where(*filters)
        .order_by(ProductionRun.production_date.desc(), ProductionRun.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(db.scalars(stmt).unique().all()), total


def get_production_run_or_404(db: Session, run_id: str) -> ProductionRun:
    run = db.get(ProductionRun, run_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Production run not found.")
    return run


def create_production_run(
    db: Session,
    payload: ProductionRunCreate,
    *,
    actor: User,
    ip_address: str | None = None,
) -> ProductionRun:
    order_no = payload.order_number.strip().upper()
    if db.scalar(select(ProductionRun).where(func.upper(ProductionRun.order_number) == order_no)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Production order '{order_no}' already exists.",
        )

    product = db.get(Product, payload.product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")

    bom = _resolve_bom_for_run(db, product.id, payload.bom_id)
    ratio = (payload.planned_batches / Decimal(bom.batch_size)).quantize(
        QTY_PREC, rounding=ROUND_HALF_UP
    )
    expected_out = (Decimal(bom.expected_output) * ratio).quantize(
        QTY_PREC, rounding=ROUND_HALF_UP
    )
    materials = _build_planned_materials(bom, payload.planned_batches)

    run = ProductionRun(
        order_number=order_no,
        product_id=product.id,
        bom_id=bom.id,
        bom_version_snapshot=bom.version_number,
        batch_number=payload.batch_number.strip().upper(),
        production_date=payload.production_date,
        planned_batches=payload.planned_batches,
        expected_output=expected_out,
        variance_tolerance_pct=payload.variance_tolerance_pct,
        supervisor_id=actor.id,
        notes=payload.notes.strip() if payload.notes else None,
        status=ProductionStatus.DRAFT,
        materials=materials,
    )
    db.add(run)
    db.flush()

    record_audit_event(
        db,
        actor_id=actor.id,
        actor_email=actor.email,
        actor_role=actor.role.value,
        action="production.run_created",
        resource_type="production_run",
        resource_id=run.id,
        details=f"{run.order_number} ({product.sku}) BOM v{bom.version_number} expected={expected_out}",
        ip_address=ip_address,
        commit=False,
    )
    db.commit()
    db.refresh(run)
    return run


def update_production_run(
    db: Session,
    run_id: str,
    payload: ProductionRunUpdate,
    *,
    actor: User,
    ip_address: str | None = None,
) -> ProductionRun:
    run = get_production_run_or_404(db, run_id)
    if run.status not in {ProductionStatus.DRAFT, ProductionStatus.PLANNED}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot edit production run in {run.status.value} status.",
        )

    if payload.batch_number is not None:
        run.batch_number = payload.batch_number.strip().upper()
    if payload.production_date is not None:
        run.production_date = payload.production_date
    if payload.notes is not None:
        run.notes = payload.notes.strip() or None
    if payload.status is not None:
        if payload.status not in {ProductionStatus.DRAFT, ProductionStatus.PLANNED}:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Use /start, /complete, /post, or /cancel endpoints for lifecycle transitions.",
            )
        run.status = payload.status
    if payload.planned_batches is not None:
        run.planned_batches = payload.planned_batches
        ratio = (payload.planned_batches / Decimal(run.bom.batch_size)).quantize(
            QTY_PREC, rounding=ROUND_HALF_UP
        )
        run.expected_output = (Decimal(run.bom.expected_output) * ratio).quantize(
            QTY_PREC, rounding=ROUND_HALF_UP
        )
        run.materials.clear()
        db.flush()
        run.materials.extend(_build_planned_materials(run.bom, payload.planned_batches))

    record_audit_event(
        db,
        actor_id=actor.id,
        actor_email=actor.email,
        actor_role=actor.role.value,
        action="production.run_updated",
        resource_type="production_run",
        resource_id=run.id,
        details=f"Updated {run.order_number} status={run.status.value}",
        ip_address=ip_address,
        commit=False,
    )
    db.commit()
    db.refresh(run)
    return run


def start_production_run(
    db: Session,
    run_id: str,
    *,
    actor: User,
    ip_address: str | None = None,
) -> ProductionRun:
    run = get_production_run_or_404(db, run_id)
    if run.status not in {ProductionStatus.DRAFT, ProductionStatus.PLANNED}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Only DRAFT or PLANNED runs can be started (current: {run.status.value}).",
        )
    run.status = ProductionStatus.IN_PROGRESS
    run.started_at = datetime.now(timezone.utc)

    record_audit_event(
        db,
        actor_id=actor.id,
        actor_email=actor.email,
        actor_role=actor.role.value,
        action="production.run_started",
        resource_type="production_run",
        resource_id=run.id,
        details=f"Started {run.order_number}",
        ip_address=ip_address,
        commit=False,
    )
    db.commit()
    db.refresh(run)
    return run


def record_material_consumption(
    db: Session,
    run_id: str,
    payload: ProductionConsumeRequest,
    *,
    actor: User,
    ip_address: str | None = None,
) -> ProductionRun:
    run = get_production_run_or_404(db, run_id)
    if run.status in {ProductionStatus.POSTED, ProductionStatus.CANCELLED}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot modify material consumption on a {run.status.value} run.",
        )

    mat_by_item = {m.stock_item_id: m for m in run.materials}
    tolerance = Decimal(run.variance_tolerance_pct)
    damaged_pouches_total = Decimal("0.000000")

    for entry in payload.materials:
        mat = mat_by_item.get(entry.stock_item_id)
        if not mat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Material '{entry.stock_item_id}' is not part of this run's BOM.",
            )

        total_in_unit = (entry.actual_quantity + entry.damaged_quantity).quantize(QTY_PREC)
        if total_in_unit > Decimal("0"):
            conv = convert_quantity(
                db,
                quantity=total_in_unit,
                from_unit_id=mat.unit_id,
                to_unit_id=mat.stock_item.base_unit_id,
                product_id=run.product_id,
            )
            consumed_base = conv.converted_quantity.quantize(QTY_PREC, rounding=ROUND_HALF_UP)
        else:
            consumed_base = Decimal("0.000000")

        mat.actual_quantity = entry.actual_quantity
        mat.damaged_quantity = entry.damaged_quantity
        mat.total_consumed_base_qty = consumed_base

        var_pct, var_status, _ = classify_variance(
            consumed_base, Decimal(mat.planned_base_quantity), tolerance
        )
        mat.variance_pct = var_pct
        mat.variance_status = var_status

        if mat.input_category == StockItemType.PACKAGING and "pouch" in mat.stock_item.name.lower():
            damaged_pouches_total += entry.damaged_quantity

    run.damaged_pouches = damaged_pouches_total

    record_audit_event(
        db,
        actor_id=actor.id,
        actor_email=actor.email,
        actor_role=actor.role.value,
        action="production.materials_recorded",
        resource_type="production_run",
        resource_id=run.id,
        details=f"Recorded consumption for {run.order_number}",
        ip_address=ip_address,
        commit=False,
    )
    db.commit()
    db.refresh(run)
    return run


def record_production_output(
    db: Session,
    run_id: str,
    payload: ProductionOutputInput,
    *,
    actor: User,
    ip_address: str | None = None,
) -> ProductionRun:
    run = get_production_run_or_404(db, run_id)
    if run.status in {ProductionStatus.POSTED, ProductionStatus.CANCELLED}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot record output on a {run.status.value} run.",
        )

    cartons_used = payload.cartons_used
    if cartons_used is None:
        carton_mat = next(
            (
                m
                for m in run.materials
                if m.input_category == StockItemType.PACKAGING
                and "carton" in m.stock_item.name.lower()
            ),
            None,
        )
        cartons_used = Decimal(carton_mat.actual_quantity) if carton_mat else Decimal("0")

    capacity, unpacked, warning = _evaluate_packaging_capacity(
        run.product, payload.good_quantity, cartons_used
    )

    run.outputs.clear()
    db.flush()
    out_row = ProductionOutput(
        production_run_id=run.id,
        product_id=run.product_id,
        unit_id=run.product.unit_id,
        expected_quantity=run.expected_output,
        good_quantity=payload.good_quantity,
        damaged_packets=payload.damaged_packets,
        cartons_used=cartons_used,
        carton_capacity_packets=capacity,
        unpacked_packets=unpacked,
        packaging_warning=warning,
        recorded_by=actor.id,
    )
    db.add(out_row)

    run.actual_good_output = payload.good_quantity
    run.damaged_packets = payload.damaged_packets
    yield_pct, _, _ = classify_variance(
        payload.good_quantity,
        Decimal(run.expected_output),
        Decimal(run.variance_tolerance_pct),
    )
    run.yield_variance_pct = yield_pct

    record_audit_event(
        db,
        actor_id=actor.id,
        actor_email=actor.email,
        actor_role=actor.role.value,
        action="production.output_recorded",
        resource_type="production_run",
        resource_id=run.id,
        details=f"Output {payload.good_quantity} good, {payload.damaged_packets} damaged",
        ip_address=ip_address,
        commit=False,
    )
    db.commit()
    db.refresh(run)
    return run


def record_wastage(
    db: Session,
    run_id: str,
    payload: ProductionWastageInput,
    *,
    actor: User,
    ip_address: str | None = None,
) -> ProductionRun:
    run = get_production_run_or_404(db, run_id)
    if run.status in {ProductionStatus.POSTED, ProductionStatus.CANCELLED}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot record wastage on a {run.status.value} run.",
        )

    if payload.stock_item_id and not db.get(StockItem, payload.stock_item_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stock item not found.")
    if payload.unit_id and not db.get(Unit, payload.unit_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unit not found.")

    w = ProductionWastage(
        production_run_id=run.id,
        stock_item_id=payload.stock_item_id,
        wastage_type=payload.wastage_type.strip().upper(),
        quantity=payload.quantity,
        unit_id=payload.unit_id,
        reason=payload.reason.strip(),
        notes=payload.notes.strip() if payload.notes else None,
        recorded_by=actor.id,
    )
    db.add(w)
    run.scrap_quantity = (Decimal(run.scrap_quantity) + payload.quantity).quantize(QTY_PREC)

    record_audit_event(
        db,
        actor_id=actor.id,
        actor_email=actor.email,
        actor_role=actor.role.value,
        action="production.wastage_recorded",
        resource_type="production_run",
        resource_id=run.id,
        details=f"Wastage {payload.wastage_type}: {payload.quantity} ({payload.reason})",
        ip_address=ip_address,
        commit=False,
    )
    db.commit()
    db.refresh(run)
    return run


def complete_production_run(
    db: Session,
    run_id: str,
    *,
    actor: User,
    ip_address: str | None = None,
) -> ProductionRun:
    run = get_production_run_or_404(db, run_id)
    if run.status != ProductionStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Only IN_PROGRESS runs can be completed (current: {run.status.value}).",
        )
    if Decimal(run.actual_good_output) <= Decimal("0") and not run.outputs:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Record actual production output before completing the run.",
        )

    run.status = ProductionStatus.COMPLETED
    run.completed_at = datetime.now(timezone.utc)

    record_audit_event(
        db,
        actor_id=actor.id,
        actor_email=actor.email,
        actor_role=actor.role.value,
        action="production.run_completed",
        resource_type="production_run",
        resource_id=run.id,
        details=f"Completed {run.order_number} good_output={run.actual_good_output}",
        ip_address=ip_address,
        commit=False,
    )
    db.commit()
    db.refresh(run)
    return run


def post_production_run(
    db: Session,
    run_id: str,
    *,
    actor: User,
    ip_address: str | None = None,
) -> ProductionRun:
    """Atomically deduct consumed inputs and add good finished output in one transaction."""
    run = get_production_run_or_404(db, run_id)
    if run.status == ProductionStatus.POSTED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Production run '{run.order_number}' has already been posted.",
        )
    if run.status != ProductionStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Production run must be COMPLETED before posting (current: {run.status.value}).",
        )

    now = datetime.now(timezone.utc)
    total_input_cost = Decimal("0.0000")

    try:
        for mat in run.materials:
            consumed = Decimal(mat.total_consumed_base_qty)
            if consumed <= Decimal("0"):
                continue
            ledger_entry = apply_stock_movement(
                db,
                stock_item=mat.stock_item,
                movement_type=MovementType.PRODUCTION_ISSUE,
                quantity_out=consumed,
                reference_doc_type="PRODUCTION_RUN",
                reference_doc_id=run.order_number,
                transaction_date=now,
                notes=f"Issued for {run.order_number} (Batch {run.batch_number})",
                created_by=actor.id,
            )
            total_input_cost += Decimal(ledger_entry.total_value)

        good_qty = Decimal(run.actual_good_output)
        if good_qty > Decimal("0"):
            finished_unit_cost = (total_input_cost / good_qty).quantize(
                QTY_PREC, rounding=ROUND_HALF_UP
            )
            apply_stock_movement(
                db,
                stock_item=run.product.stock_item,
                movement_type=MovementType.PRODUCTION_OUTPUT,
                quantity_in=good_qty,
                unit_cost=finished_unit_cost,
                reference_doc_type="PRODUCTION_RUN",
                reference_doc_id=run.order_number,
                transaction_date=now,
                notes=f"Produced {good_qty} {run.product.unit.symbol} in Batch {run.batch_number}",
                created_by=actor.id,
            )

        run.status = ProductionStatus.POSTED
        run.posted_by = actor.id
        run.posted_at = now

        record_audit_event(
            db,
            actor_id=actor.id,
            actor_email=actor.email,
            actor_role=actor.role.value,
            action="production.run_posted",
            resource_type="production_run",
            resource_id=run.id,
            details=f"Posted {run.order_number} output={good_qty} input_cost={total_input_cost}",
            ip_address=ip_address,
            commit=False,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(run)
    return run


def cancel_production_run(
    db: Session,
    run_id: str,
    *,
    reason: str,
    actor: User,
    ip_address: str | None = None,
) -> ProductionRun:
    run = get_production_run_or_404(db, run_id)
    if run.status == ProductionStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Production run is already cancelled.",
        )

    now = datetime.now(timezone.utc)
    was_posted = run.status == ProductionStatus.POSTED
    try:
        if was_posted:
            good_qty = Decimal(run.actual_good_output)
            if good_qty > Decimal("0"):
                apply_stock_movement(
                    db,
                    stock_item=run.product.stock_item,
                    movement_type=MovementType.REVERSAL,
                    quantity_out=good_qty,
                    reference_doc_type="PRODUCTION_REVERSAL",
                    reference_doc_id=run.order_number,
                    transaction_date=now,
                    notes=f"Reverse finished output for {run.order_number}: {reason}",
                    created_by=actor.id,
                )
            for mat in run.materials:
                consumed = Decimal(mat.total_consumed_base_qty)
                if consumed > Decimal("0"):
                    apply_stock_movement(
                        db,
                        stock_item=mat.stock_item,
                        movement_type=MovementType.REVERSAL,
                        quantity_in=consumed,
                        reference_doc_type="PRODUCTION_REVERSAL",
                        reference_doc_id=run.order_number,
                        transaction_date=now,
                        notes=f"Restore material for {run.order_number}: {reason}",
                        created_by=actor.id,
                    )

        run.status = ProductionStatus.CANCELLED
        run.cancelled_by = actor.id
        run.cancelled_at = now
        run.cancel_reason = reason.strip()

        record_audit_event(
            db,
            actor_id=actor.id,
            actor_email=actor.email,
            actor_role=actor.role.value,
            action="production.run_cancelled",
            resource_type="production_run",
            resource_id=run.id,
            details=f"Cancelled {run.order_number} (reversed={was_posted}): {reason}",
            ip_address=ip_address,
            commit=False,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(run)
    return run


def build_run_variance_report(db: Session, run_id: str) -> RunVarianceReportOut:
    run = get_production_run_or_404(db, run_id)
    tolerance = Decimal(run.variance_tolerance_pct)
    yield_pct, yield_status, yield_exceeds = classify_variance(
        Decimal(run.actual_good_output), Decimal(run.expected_output), tolerance
    )

    mat_rows: List[MaterialVarianceRow] = []
    for m in run.materials:
        planned = Decimal(m.planned_base_quantity)
        actual = Decimal(m.total_consumed_base_qty)
        diff = (actual - planned).quantize(QTY_PREC, rounding=ROUND_HALF_UP)
        pct, status_lbl, exceeds = classify_variance(actual, planned, tolerance)
        mat_rows.append(
            MaterialVarianceRow(
                stock_item_id=m.stock_item_id,
                material_name=m.stock_item.name,
                sku=m.stock_item.sku,
                input_category=m.input_category,
                unit_symbol=m.stock_item.base_unit.symbol,
                planned_consumption=planned,
                actual_consumption=actual,
                damaged_quantity=Decimal(m.damaged_quantity),
                difference=diff,
                variance_pct=pct,
                status=status_lbl,
                exceeds_tolerance=exceeds,
            )
        )

    latest_warning = run.outputs[-1].packaging_warning if run.outputs else None
    return RunVarianceReportOut(
        production_run_id=run.id,
        order_number=run.order_number,
        product_name=run.product.name,
        tolerance_pct=tolerance,
        expected_output=run.expected_output,
        actual_good_output=run.actual_good_output,
        yield_variance_pct=yield_pct,
        yield_status=yield_status,
        yield_exceeds_tolerance=yield_exceeds,
        packaging_warning=latest_warning,
        materials=mat_rows,
    )


def build_variance_summary(db: Session) -> VarianceSummaryOut:
    runs = list(
        db.scalars(
            select(ProductionRun)
            .where(ProductionRun.status.in_([ProductionStatus.COMPLETED, ProductionStatus.POSTED]))
            .order_by(ProductionRun.production_date.desc())
        ).unique().all()
    )
    items: List[VarianceSummaryItem] = []
    flagged = 0
    yield_sum = Decimal("0.0000")

    for r in runs:
        tol = Decimal(r.variance_tolerance_pct)
        y_pct, y_status, y_exceeds = classify_variance(
            Decimal(r.actual_good_output), Decimal(r.expected_output), tol
        )
        flagged_mats = sum(
            1
            for m in r.materials
            if classify_variance(Decimal(m.total_consumed_base_qty), Decimal(m.planned_base_quantity), tol)[2]
        )
        if y_exceeds or flagged_mats > 0:
            flagged += 1
        yield_sum += y_pct
        items.append(
            VarianceSummaryItem(
                production_run_id=r.id,
                order_number=r.order_number,
                product_name=r.product.name,
                production_date=r.production_date,
                status=r.status,
                expected_output=r.expected_output,
                actual_good_output=r.actual_good_output,
                yield_variance_pct=y_pct,
                yield_status=y_status,
                flagged_material_count=flagged_mats,
            )
        )

    avg_yield = (
        (yield_sum / Decimal(len(runs))).quantize(PCT_PREC, rounding=ROUND_HALF_UP)
        if runs
        else Decimal("0.0000")
    )
    return VarianceSummaryOut(
        total_runs=len(runs),
        flagged_runs=flagged,
        avg_yield_variance_pct=avg_yield,
        runs=items,
    )


def build_production_dashboard(db: Session) -> ProductionDashboardOut:
    today = date.today()
    runs = list(
        db.scalars(
            select(ProductionRun).order_by(
                ProductionRun.production_date.desc(), ProductionRun.created_at.desc()
            )
        ).unique().all()
    )
    active_boms = int(
        db.scalar(select(func.count(BomHeader.id)).where(BomHeader.is_active.is_(True))) or 0
    )

    non_cancelled = [r for r in runs if r.status != ProductionStatus.CANCELLED]
    todays_runs = sum(1 for r in non_cancelled if r.production_date == today)
    pending_runs = sum(
        1
        for r in non_cancelled
        if r.status in {ProductionStatus.DRAFT, ProductionStatus.PLANNED, ProductionStatus.IN_PROGRESS, ProductionStatus.COMPLETED}
    )
    planned_out = sum((Decimal(r.expected_output) for r in non_cancelled), Decimal("0.000000"))
    actual_out = sum((Decimal(r.actual_good_output) for r in non_cancelled), Decimal("0.000000"))
    total_wastage = sum(
        (Decimal(r.damaged_packets) + Decimal(r.damaged_pouches) + Decimal(r.scrap_quantity) for r in non_cancelled),
        Decimal("0.000000"),
    )

    done_runs = [r for r in non_cancelled if r.status in {ProductionStatus.COMPLETED, ProductionStatus.POSTED}]
    done_exp = sum((Decimal(r.expected_output) for r in done_runs), Decimal("0.000000"))
    done_act = sum((Decimal(r.actual_good_output) for r in done_runs), Decimal("0.000000"))
    overall_yield_var = (
        (((done_act - done_exp) / done_exp) * Decimal("100")).quantize(PCT_PREC, rounding=ROUND_HALF_UP)
        if done_exp > Decimal("0")
        else Decimal("0.0000")
    )

    by_date: Dict[str, DailyProductionPoint] = {}
    for r in reversed(non_cancelled):
        d_key = r.production_date.isoformat()
        cur = by_date.get(d_key)
        w = Decimal(r.damaged_packets) + Decimal(r.damaged_pouches) + Decimal(r.scrap_quantity)
        if cur is None:
            by_date[d_key] = DailyProductionPoint(
                date=d_key,
                planned_output=Decimal(r.expected_output),
                actual_output=Decimal(r.actual_good_output),
                wastage=w,
            )
        else:
            cur.planned_output += Decimal(r.expected_output)
            cur.actual_output += Decimal(r.actual_good_output)
            cur.wastage += w

    by_prod: Dict[str, ProductYieldPoint] = {}
    for r in done_runs:
        pname = r.product.name
        cur = by_prod.get(pname)
        if cur is None:
            by_prod[pname] = ProductYieldPoint(
                product_name=pname,
                runs_count=1,
                expected_output=Decimal(r.expected_output),
                actual_output=Decimal(r.actual_good_output),
                yield_pct=Decimal("0"),
            )
        else:
            cur.runs_count += 1
            cur.expected_output += Decimal(r.expected_output)
            cur.actual_output += Decimal(r.actual_good_output)
    for pt in by_prod.values():
        pt.yield_pct = (
            ((pt.actual_output / pt.expected_output) * Decimal("100")).quantize(
                PCT_PREC, rounding=ROUND_HALF_UP
            )
            if pt.expected_output > Decimal("0")
            else Decimal("0.0000")
        )

    var_summary = build_variance_summary(db)

    return ProductionDashboardOut(
        todays_runs=todays_runs,
        planned_output=planned_out,
        actual_output=actual_out,
        total_wastage=total_wastage,
        overall_yield_variance_pct=overall_yield_var,
        pending_runs=pending_runs,
        active_boms=active_boms,
        daily_trend=list(by_date.values())[-14:],
        product_yield=list(by_prod.values()),
        recent_runs=[to_production_run_out(db, r) for r in runs[:10]],
        variance_alerts=[v for v in var_summary.runs if v.yield_status != "GREEN" or v.flagged_material_count > 0],
    )
