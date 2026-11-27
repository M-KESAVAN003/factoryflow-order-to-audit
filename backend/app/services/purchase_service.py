import csv
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
import io
from typing import List, Tuple

from fastapi import HTTPException, status
from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.orm import Session

from app.models.inventory import MovementType
from app.models.product import Product
from app.models.purchase import Purchase, PurchaseItem, PurchaseStatus
from app.models.stock_item import StockItem
from app.models.supplier import Supplier
from app.models.unit import Unit
from app.models.user import User
from app.schemas.inventory_purchase import (
    PurchaseCreate,
    PurchaseItemInput,
    PurchaseItemOut,
    PurchaseOut,
    PurchaseUpdate,
)
from app.services.audit_service import record_audit_event
from app.services.ledger_service import apply_stock_movement
from app.services.unit_service import convert_quantity

MONEY_PREC = Decimal("0.0001")
QTY_PREC = Decimal("0.000001")


def to_purchase_out(purchase: Purchase) -> PurchaseOut:
    return PurchaseOut(
        id=purchase.id,
        reference_number=purchase.reference_number,
        supplier_id=purchase.supplier_id,
        supplier_name=purchase.supplier.name,
        purchase_date=purchase.purchase_date,
        status=purchase.status,
        payment_status=purchase.payment_status,
        subtotal=purchase.subtotal,
        tax_amount=purchase.tax_amount,
        total_amount=purchase.total_amount,
        notes=purchase.notes,
        created_by=purchase.created_by,
        created_by_email=purchase.creator.email,
        posted_by=purchase.posted_by,
        posted_at=purchase.posted_at,
        cancelled_at=purchase.cancelled_at,
        cancel_reason=purchase.cancel_reason,
        created_at=purchase.created_at,
        updated_at=purchase.updated_at,
        items=[
            PurchaseItemOut(
                id=item.id,
                stock_item_id=item.stock_item_id,
                stock_item_name=item.stock_item.name,
                stock_item_sku=item.stock_item.sku,
                unit_id=item.unit_id,
                unit_symbol=item.unit.symbol,
                base_unit_symbol=item.stock_item.base_unit.symbol,
                quantity=item.quantity,
                base_quantity=item.base_quantity,
                unit_rate=item.unit_rate,
                tax_rate=item.tax_rate,
                tax_amount=item.tax_amount,
                line_subtotal=item.line_subtotal,
                line_total=item.line_total,
            )
            for item in purchase.items
        ],
    )


def _build_purchase_items(
    db: Session, raw_items: List[PurchaseItemInput]
) -> Tuple[List[PurchaseItem], Decimal, Decimal, Decimal]:
    built: List[PurchaseItem] = []
    subtotal = Decimal("0.0000")
    total_tax = Decimal("0.0000")

    for row in raw_items:
        stock_item = db.get(StockItem, row.stock_item_id)
        if not stock_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Stock item '{row.stock_item_id}' not found.",
            )
        unit = db.get(Unit, row.unit_id)
        if not unit:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Unit '{row.unit_id}' not found.",
            )

        linked_product = db.scalar(
            select(Product).where(Product.stock_item_id == stock_item.id)
        )
        conversion = convert_quantity(
            db,
            quantity=row.quantity,
            from_unit_id=unit.id,
            to_unit_id=stock_item.base_unit_id,
            product_id=linked_product.id if linked_product else None,
        )
        base_qty = conversion.converted_quantity.quantize(QTY_PREC, rounding=ROUND_HALF_UP)

        line_sub = (row.quantity * row.unit_rate).quantize(MONEY_PREC, rounding=ROUND_HALF_UP)
        line_tax = (line_sub * row.tax_rate / Decimal("100")).quantize(
            MONEY_PREC, rounding=ROUND_HALF_UP
        )
        line_tot = (line_sub + line_tax).quantize(MONEY_PREC, rounding=ROUND_HALF_UP)

        subtotal += line_sub
        total_tax += line_tax
        built.append(
            PurchaseItem(
                stock_item_id=stock_item.id,
                unit_id=unit.id,
                quantity=row.quantity,
                base_quantity=base_qty,
                unit_rate=row.unit_rate,
                tax_rate=row.tax_rate,
                tax_amount=line_tax,
                line_subtotal=line_sub,
                line_total=line_tot,
            )
        )

    total_amount = (subtotal + total_tax).quantize(MONEY_PREC, rounding=ROUND_HALF_UP)
    return built, subtotal.quantize(MONEY_PREC), total_tax.quantize(MONEY_PREC), total_amount


def list_purchases(
    db: Session,
    *,
    search: str | None = None,
    supplier_id: str | None = None,
    status_filter: PurchaseStatus | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    sort_by: str = "purchase_date",
    sort_dir: str = "desc",
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[Purchase], int]:
    filters = []
    if search:
        term = f"%{search.strip()}%"
        filters.append(
            or_(
                Purchase.reference_number.ilike(term),
                Purchase.supplier.has(Supplier.name.ilike(term)),
            )
        )
    if supplier_id:
        filters.append(Purchase.supplier_id == supplier_id)
    if status_filter is not None:
        filters.append(Purchase.status == status_filter)
    if date_from is not None:
        filters.append(Purchase.purchase_date >= date_from)
    if date_to is not None:
        filters.append(Purchase.purchase_date <= date_to)

    total = int(db.scalar(select(func.count(Purchase.id)).where(*filters)) or 0)
    col = getattr(Purchase, sort_by, Purchase.purchase_date)
    order_fn = desc if sort_dir == "desc" else asc
    stmt = (
        select(Purchase)
        .where(*filters)
        .order_by(order_fn(col), Purchase.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(db.scalars(stmt).unique().all()), total


def get_purchase_or_404(db: Session, purchase_id: str) -> Purchase:
    purchase = db.get(Purchase, purchase_id)
    if not purchase:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase not found.")
    return purchase


def create_purchase(
    db: Session,
    payload: PurchaseCreate,
    *,
    actor: User,
    ip_address: str | None = None,
) -> Purchase:
    ref = payload.reference_number.strip().upper()
    if db.scalar(select(Purchase).where(func.upper(Purchase.reference_number) == ref)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Purchase reference '{ref}' already exists.",
        )

    supplier = db.get(Supplier, payload.supplier_id)
    if not supplier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found.")

    built_items, subtotal, tax_amount, total_amount = _build_purchase_items(db, payload.items)
    purchase = Purchase(
        reference_number=ref,
        supplier_id=supplier.id,
        purchase_date=payload.purchase_date,
        status=PurchaseStatus.DRAFT,
        payment_status=payload.payment_status,
        subtotal=subtotal,
        tax_amount=tax_amount,
        total_amount=total_amount,
        notes=payload.notes.strip() if payload.notes else None,
        created_by=actor.id,
        items=built_items,
    )
    db.add(purchase)
    db.flush()

    record_audit_event(
        db,
        actor_id=actor.id,
        actor_email=actor.email,
        actor_role=actor.role.value,
        action="purchase.draft_created",
        resource_type="purchase",
        resource_id=purchase.id,
        details=f"Draft {purchase.reference_number} total={purchase.total_amount}",
        ip_address=ip_address,
        commit=False,
    )
    db.commit()
    db.refresh(purchase)
    return purchase


def update_purchase(
    db: Session,
    purchase_id: str,
    payload: PurchaseUpdate,
    *,
    actor: User,
    ip_address: str | None = None,
) -> Purchase:
    purchase = get_purchase_or_404(db, purchase_id)
    if purchase.status in {PurchaseStatus.POSTED, PurchaseStatus.CANCELLED}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot modify a {purchase.status.value} purchase.",
        )

    if payload.status is not None:
        if payload.status not in {PurchaseStatus.DRAFT, PurchaseStatus.REVIEWED}:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Use /post or /cancel endpoints for posting or cancelling purchases.",
            )
        purchase.status = payload.status
        if payload.status == PurchaseStatus.REVIEWED:
            purchase.reviewed_by = actor.id

    if payload.supplier_id is not None:
        if not db.get(Supplier, payload.supplier_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found.")
        purchase.supplier_id = payload.supplier_id
    if payload.purchase_date is not None:
        purchase.purchase_date = payload.purchase_date
    if payload.payment_status is not None:
        purchase.payment_status = payload.payment_status
    if payload.notes is not None:
        purchase.notes = payload.notes.strip() or None

    if payload.items is not None:
        built_items, subtotal, tax_amount, total_amount = _build_purchase_items(db, payload.items)
        purchase.items.clear()
        db.flush()
        purchase.items.extend(built_items)
        purchase.subtotal = subtotal
        purchase.tax_amount = tax_amount
        purchase.total_amount = total_amount

    record_audit_event(
        db,
        actor_id=actor.id,
        actor_email=actor.email,
        actor_role=actor.role.value,
        action="purchase.updated",
        resource_type="purchase",
        resource_id=purchase.id,
        details=f"Updated {purchase.reference_number} status={purchase.status.value}",
        ip_address=ip_address,
        commit=False,
    )
    db.commit()
    db.refresh(purchase)
    return purchase


def post_purchase(
    db: Session,
    purchase_id: str,
    *,
    actor: User,
    ip_address: str | None = None,
) -> Purchase:
    """Atomically validate, convert units, post stock receipts, and update weighted-avg valuation."""
    purchase = get_purchase_or_404(db, purchase_id)
    if purchase.status == PurchaseStatus.POSTED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Purchase '{purchase.reference_number}' has already been posted.",
        )
    if purchase.status == PurchaseStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Cancelled purchases cannot be posted.",
        )
    if not purchase.items:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Cannot post a purchase with no line items.",
        )

    now = datetime.now(timezone.utc)
    try:
        for item in purchase.items:
            if Decimal(item.quantity) <= Decimal("0") or Decimal(item.base_quantity) <= Decimal("0"):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="All purchase quantities must be greater than zero.",
                )
            stock_item = db.get(StockItem, item.stock_item_id)
            if not stock_item:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Stock item missing."
                )

            # Re-verify conversion validity at posting time
            linked_product = db.scalar(
                select(Product).where(Product.stock_item_id == stock_item.id)
            )
            conv = convert_quantity(
                db,
                quantity=Decimal(item.quantity),
                from_unit_id=item.unit_id,
                to_unit_id=stock_item.base_unit_id,
                product_id=linked_product.id if linked_product else None,
            )
            base_qty = conv.converted_quantity.quantize(QTY_PREC, rounding=ROUND_HALF_UP)
            base_unit_cost = (Decimal(item.line_subtotal) / base_qty).quantize(
                QTY_PREC, rounding=ROUND_HALF_UP
            )

            apply_stock_movement(
                db,
                stock_item=stock_item,
                movement_type=MovementType.PURCHASE_RECEIPT,
                quantity_in=base_qty,
                unit_cost=base_unit_cost,
                reference_doc_type="PURCHASE",
                reference_doc_id=purchase.reference_number,
                transaction_date=now,
                notes=f"Purchase receipt from {purchase.supplier.name}",
                created_by=actor.id,
            )

        purchase.status = PurchaseStatus.POSTED
        purchase.posted_by = actor.id
        purchase.posted_at = now
        if purchase.reviewed_by is None:
            purchase.reviewed_by = actor.id

        record_audit_event(
            db,
            actor_id=actor.id,
            actor_email=actor.email,
            actor_role=actor.role.value,
            action="purchase.posted",
            resource_type="purchase",
            resource_id=purchase.id,
            details=f"Posted {purchase.reference_number} ({len(purchase.items)} items)",
            ip_address=ip_address,
            commit=False,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(purchase)
    return purchase


def cancel_purchase(
    db: Session,
    purchase_id: str,
    *,
    reason: str,
    actor: User,
    ip_address: str | None = None,
) -> Purchase:
    """Cancel a purchase; if posted, emit traceable REVERSAL ledger entries."""
    purchase = get_purchase_or_404(db, purchase_id)
    if purchase.status == PurchaseStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Purchase is already cancelled.",
        )

    now = datetime.now(timezone.utc)
    was_posted = purchase.status == PurchaseStatus.POSTED
    try:
        if was_posted:
            for item in purchase.items:
                stock_item = db.get(StockItem, item.stock_item_id)
                if not stock_item:
                    continue
                base_qty = Decimal(item.base_quantity)
                base_unit_cost = (Decimal(item.line_subtotal) / base_qty).quantize(
                    QTY_PREC, rounding=ROUND_HALF_UP
                )
                apply_stock_movement(
                    db,
                    stock_item=stock_item,
                    movement_type=MovementType.REVERSAL,
                    quantity_out=base_qty,
                    unit_cost=base_unit_cost,
                    reference_doc_type="PURCHASE_REVERSAL",
                    reference_doc_id=purchase.reference_number,
                    transaction_date=now,
                    notes=f"Reversal of {purchase.reference_number}: {reason}",
                    created_by=actor.id,
                )

        purchase.status = PurchaseStatus.CANCELLED
        purchase.cancelled_by = actor.id
        purchase.cancelled_at = now
        purchase.cancel_reason = reason.strip()

        record_audit_event(
            db,
            actor_id=actor.id,
            actor_email=actor.email,
            actor_role=actor.role.value,
            action="purchase.cancelled",
            resource_type="purchase",
            resource_id=purchase.id,
            details=f"Cancelled {purchase.reference_number} (reversed={was_posted}): {reason}",
            ip_address=ip_address,
            commit=False,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(purchase)
    return purchase


def export_purchases_csv(purchases: List[Purchase]) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "Reference",
            "Date",
            "Supplier",
            "Status",
            "Payment Status",
            "Subtotal",
            "Tax",
            "Total Amount",
            "Created By",
        ]
    )
    for p in purchases:
        writer.writerow(
            [
                p.reference_number,
                p.purchase_date.isoformat(),
                p.supplier.name,
                p.status.value,
                p.payment_status.value,
                f"{p.subtotal:.2f}",
                f"{p.tax_amount:.2f}",
                f"{p.total_amount:.2f}",
                p.creator.email,
            ]
        )
    return buf.getvalue().encode("utf-8")


def export_purchases_excel_tsv(purchases: List[Purchase]) -> bytes:
    """Spreadsheet-ready tab-delimited export compatible with Microsoft Excel."""
    lines = ["Reference\tDate\tSupplier\tStatus\tPayment\tSubtotal\tTax\tTotal"]
    for p in purchases:
        lines.append(
            f"{p.reference_number}\t{p.purchase_date.isoformat()}\t{p.supplier.name}\t"
            f"{p.status.value}\t{p.payment_status.value}\t{p.subtotal:.2f}\t"
            f"{p.tax_amount:.2f}\t{p.total_amount:.2f}"
        )
    return ("\n".join(lines)).encode("utf-8")


def export_purchases_pdf(purchases: List[Purchase]) -> bytes:
    """Generate a valid single-page PDF 1.4 summary report for the purchase register."""
    lines = [
        "FactoryFlow Purchase Register",
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "-" * 72,
    ]
    for p in purchases[:35]:
        lines.append(
            f"{p.reference_number} | {p.purchase_date} | {p.supplier.name[:20]} | "
            f"{p.status.value} | INR {p.total_amount:.2f}"
        )

    def _pdf_escape(text: str) -> str:
        return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    stream_cmds = ["BT", "/F1 10 Tf", "40 760 Td", "14 TL"]
    for idx, line in enumerate(lines):
        if idx == 0:
            stream_cmds.append(f"({_pdf_escape(line)}) Tj")
        else:
            stream_cmds.append(f"T* ({_pdf_escape(line)}) Tj")
    stream_cmds.append("ET")
    stream_bytes = "\n".join(stream_cmds).encode("latin-1", errors="replace")

    objects = [
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n",
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n",
        (
            b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj\n"
        ),
        b"4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Courier >> endobj\n",
        (
            f"5 0 obj << /Length {len(stream_bytes)} >>\nstream\n".encode("ascii")
            + stream_bytes
            + b"\nendstream\nendobj\n"
        ),
    ]

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objects:
        offsets.append(len(pdf))
        pdf.extend(obj)
    xref_pos = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode("ascii"))
    for off in offsets[1:]:
        pdf.extend(f"{off:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        (
            f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_pos}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(pdf)
