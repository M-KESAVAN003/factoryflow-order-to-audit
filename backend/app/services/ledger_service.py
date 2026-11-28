from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import List

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.inventory import MovementType, StockBalance, StockLedger
from app.models.stock_item import StockItem
from app.schemas.inventory_purchase import (
    ReconciliationItemOut,
    ReconciliationReportOut,
    StockLedgerOut,
)

QTY_PREC = Decimal("0.000001")
VAL_PREC = Decimal("0.0001")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def to_ledger_out(entry: StockLedger) -> StockLedgerOut:
    return StockLedgerOut(
        id=entry.id,
        stock_item_id=entry.stock_item_id,
        stock_item_name=entry.stock_item.name,
        stock_item_sku=entry.stock_item.sku,
        movement_type=entry.movement_type,
        quantity_in=entry.quantity_in,
        quantity_out=entry.quantity_out,
        base_unit_symbol=entry.base_unit.symbol,
        reference_doc_type=entry.reference_doc_type,
        reference_doc_id=entry.reference_doc_id,
        transaction_date=entry.transaction_date,
        unit_cost=entry.unit_cost,
        total_value=entry.total_value,
        balance_qty_after=entry.balance_qty_after,
        avg_cost_after=entry.avg_cost_after,
        balance_value_after=entry.balance_value_after,
        notes=entry.notes,
        created_by_email=entry.creator.email if entry.creator else "system@factoryflow.io",
        created_at=entry.created_at,
    )


def get_or_create_locked_balance(db: Session, stock_item_id: str) -> StockBalance:
    """Fetch StockBalance with FOR UPDATE row-level lock (or initialize at zero)."""
    stmt = (
        select(StockBalance)
        .where(StockBalance.stock_item_id == stock_item_id)
        .with_for_update(of=StockBalance)
    )
    balance = db.scalar(stmt)
    if balance is None:
        balance = StockBalance(
            stock_item_id=stock_item_id,
            available_quantity=Decimal("0.000000"),
            average_cost=Decimal("0.000000"),
            total_value=Decimal("0.0000"),
        )
        db.add(balance)
        db.flush()
    return balance


def apply_stock_movement(
    db: Session,
    *,
    stock_item: StockItem,
    movement_type: MovementType,
    quantity_in: Decimal = Decimal("0"),
    quantity_out: Decimal = Decimal("0"),
    unit_cost: Decimal | None = None,
    reference_doc_type: str,
    reference_doc_id: str,
    transaction_date: datetime | None = None,
    notes: str | None = None,
    created_by: str | None = None,
) -> StockLedger:
    """Append an immutable stock ledger entry and atomically update weighted-average balance."""
    qty_in = Decimal(quantity_in).quantize(QTY_PREC, rounding=ROUND_HALF_UP)
    qty_out = Decimal(quantity_out).quantize(QTY_PREC, rounding=ROUND_HALF_UP)

    if qty_in < 0 or qty_out < 0 or (qty_in > 0 and qty_out > 0) or (qty_in == 0 and qty_out == 0):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Movement must specify either a positive quantity_in or a positive quantity_out.",
        )

    balance = get_or_create_locked_balance(db, stock_item.id)
    existing_qty = Decimal(balance.available_quantity)
    existing_avg = Decimal(balance.average_cost)
    existing_val = Decimal(balance.total_value)
    tx_dt = transaction_date or _utcnow()

    if qty_in > 0:
        effective_cost = (
            Decimal(unit_cost) if unit_cost is not None else existing_avg
        ).quantize(QTY_PREC, rounding=ROUND_HALF_UP)
        movement_value = (qty_in * effective_cost).quantize(VAL_PREC, rounding=ROUND_HALF_UP)
        new_qty = (existing_qty + qty_in).quantize(QTY_PREC, rounding=ROUND_HALF_UP)
        new_val = (existing_val + movement_value).quantize(VAL_PREC, rounding=ROUND_HALF_UP)
        new_avg = (
            (new_val / new_qty).quantize(QTY_PREC, rounding=ROUND_HALF_UP)
            if new_qty > Decimal("0")
            else Decimal("0.000000")
        )
    else:
        if existing_qty - qty_out < Decimal("0"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Insufficient stock for {stock_item.name} ({stock_item.sku}): "
                    f"available {existing_qty}, requested out {qty_out}."
                ),
            )
        effective_cost = (
            Decimal(unit_cost) if unit_cost is not None else existing_avg
        ).quantize(QTY_PREC, rounding=ROUND_HALF_UP)
        movement_value = (qty_out * effective_cost).quantize(VAL_PREC, rounding=ROUND_HALF_UP)
        new_qty = (existing_qty - qty_out).quantize(QTY_PREC, rounding=ROUND_HALF_UP)
        new_val = max(
            Decimal("0.0000"),
            (existing_val - movement_value).quantize(VAL_PREC, rounding=ROUND_HALF_UP),
        )
        new_avg = (
            (new_val / new_qty).quantize(QTY_PREC, rounding=ROUND_HALF_UP)
            if new_qty > Decimal("0")
            else Decimal("0.000000")
        )

    balance.available_quantity = new_qty
    balance.average_cost = new_avg
    balance.total_value = new_val
    balance.last_movement_at = tx_dt

    entry = StockLedger(
        stock_item_id=stock_item.id,
        movement_type=movement_type,
        quantity_in=qty_in,
        quantity_out=qty_out,
        base_unit_id=stock_item.base_unit_id,
        reference_doc_type=reference_doc_type,
        reference_doc_id=reference_doc_id,
        transaction_date=tx_dt,
        unit_cost=effective_cost,
        total_value=movement_value,
        balance_qty_after=new_qty,
        avg_cost_after=new_avg,
        balance_value_after=new_val,
        notes=notes,
        created_by=created_by,
    )
    db.add(entry)
    db.flush()
    return entry


def reconcile_stock_balances(db: Session) -> ReconciliationReportOut:
    """Compare StockBalance projections against raw SUM(quantity_in - quantity_out) in StockLedger."""
    items = list(db.scalars(select(StockItem).order_by(StockItem.sku.asc())).all())
    balances = {
        b.stock_item_id: Decimal(b.available_quantity)
        for b in db.scalars(select(StockBalance)).all()
    }
    ledger_rows = db.execute(
        select(
            StockLedger.stock_item_id,
            func.coalesce(func.sum(StockLedger.quantity_in - StockLedger.quantity_out), 0),
        ).group_by(StockLedger.stock_item_id)
    ).all()
    ledger_sums = {row[0]: Decimal(str(row[1])).quantize(QTY_PREC) for row in ledger_rows}

    report_items: List[ReconciliationItemOut] = []
    all_ok = True
    for item in items:
        bal_qty = balances.get(item.id, Decimal("0.000000")).quantize(QTY_PREC)
        led_qty = ledger_sums.get(item.id, Decimal("0.000000")).quantize(QTY_PREC)
        diff = (bal_qty - led_qty).quantize(QTY_PREC)
        ok = diff == Decimal("0.000000")
        if not ok:
            all_ok = False
        report_items.append(
            ReconciliationItemOut(
                stock_item_id=item.id,
                sku=item.sku,
                name=item.name,
                balance_quantity=bal_qty,
                ledger_quantity=led_qty,
                discrepancy=diff,
                reconciled=ok,
            )
        )
    return ReconciliationReportOut(
        all_reconciled=all_ok,
        checked_items=len(report_items),
        items=report_items,
    )
