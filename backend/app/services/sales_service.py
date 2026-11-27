from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Tuple

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.permissions import Role
from app.models.customer import Customer
from app.models.inventory import MovementType, StockBalance
from app.models.product import Product
from app.models.sales import (
    CreditNote,
    Dispatch,
    DispatchItem,
    Invoice,
    InvoiceItem,
    InvoiceStatus,
    SalesOrder,
    SalesOrderItem,
    SalesOrderStatus,
    TaxType,
)
from app.models.user import User
from app.schemas.sales import (
    CreditNoteCreate,
    CreditNoteOut,
    CustomerSalesSummaryRow,
    DispatchCreate,
    DispatchItemOut,
    DispatchOut,
    InvoiceCreate,
    InvoiceItemOut,
    InvoiceOut,
    PriceConflictLineOut,
    SalesOrderApproveRequest,
    SalesOrderCreate,
    SalesOrderItemOut,
    SalesOrderOut,
    SalesOrderStockCheckOut,
    SalesOrderSyncRequest,
    SalesOrderSyncResponse,
    SalesOrderUpdate,
    SalesOverviewOut,
    StockCheckLineOut,
)
from app.services.audit_service import record_audit_event
from app.services.gst_service import (
    AMT_PREC,
    amount_to_inr_words,
    compute_line_gst,
    determine_tax_type,
    format_place_of_supply,
    get_financial_year,
)
from app.services.ledger_service import QTY_PREC, apply_stock_movement, get_or_create_locked_balance

COMMITTED_STATUSES = (SalesOrderStatus.APPROVED, SalesOrderStatus.INVOICED, SalesOrderStatus.PARTIALLY_FULFILLED)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _stock_balance_map(db: Session, stock_item_ids: List[str]) -> Dict[str, Decimal]:
    if not stock_item_ids:
        return {}
    rows = db.scalars(
        select(StockBalance).where(StockBalance.stock_item_id.in_(stock_item_ids))
    ).all()
    return {b.stock_item_id: Decimal(b.available_quantity) for b in rows}


def _committed_stock_map(
    db: Session, stock_item_ids: List[str], *, exclude_order_id: str | None = None
) -> Dict[str, Decimal]:
    """Sum approved but not-yet-dispatched quantities across active orders to avoid overselling."""
    if not stock_item_ids:
        return {}
    stmt = (
        select(
            SalesOrderItem.stock_item_id,
            func.coalesce(
                func.sum(SalesOrderItem.approved_quantity - SalesOrderItem.dispatched_quantity),
                0,
            ),
        )
        .join(SalesOrder, SalesOrder.id == SalesOrderItem.sales_order_id)
        .where(
            SalesOrderItem.stock_item_id.in_(stock_item_ids),
            SalesOrder.status.in_(COMMITTED_STATUSES),
        )
    )
    if exclude_order_id:
        stmt = stmt.where(SalesOrder.id != exclude_order_id)
    rows = db.execute(stmt.group_by(SalesOrderItem.stock_item_id)).all()
    return {row[0]: max(Decimal("0.000000"), Decimal(str(row[1])).quantize(QTY_PREC)) for row in rows}


def _recalculate_order_totals(order: SalesOrder) -> None:
    sub = Decimal("0.00")
    cgst = Decimal("0.00")
    sgst = Decimal("0.00")
    igst = Decimal("0.00")
    for item in order.items:
        qty = (
            Decimal(item.approved_quantity)
            if order.status in {SalesOrderStatus.APPROVED, SalesOrderStatus.PARTIALLY_FULFILLED, SalesOrderStatus.INVOICED, SalesOrderStatus.DISPATCHED}
            else Decimal(item.requested_quantity)
        )
        calc = compute_line_gst(
            quantity=qty,
            unit_price=Decimal(item.unit_price),
            gst_rate=Decimal(item.gst_rate),
            tax_type=order.tax_type,
        )
        item.taxable_value = calc.taxable_value
        item.cgst_rate = calc.cgst_rate
        item.sgst_rate = calc.sgst_rate
        item.igst_rate = calc.igst_rate
        item.cgst_amount = calc.cgst_amount
        item.sgst_amount = calc.sgst_amount
        item.igst_amount = calc.igst_amount
        item.line_total = calc.line_total
        sub += calc.taxable_value
        cgst += calc.cgst_amount
        sgst += calc.sgst_amount
        igst += calc.igst_amount

    order.subtotal = sub.quantize(AMT_PREC)
    order.cgst_amount = cgst.quantize(AMT_PREC)
    order.sgst_amount = sgst.quantize(AMT_PREC)
    order.igst_amount = igst.quantize(AMT_PREC)
    order.tax_amount = (cgst + sgst + igst).quantize(AMT_PREC)
    order.total_amount = (order.subtotal + order.tax_amount).quantize(AMT_PREC)


def to_sales_order_out(db: Session, order: SalesOrder) -> SalesOrderOut:
    item_ids = [it.stock_item_id for it in order.items]
    avail_map = _stock_balance_map(db, item_ids)
    committed_map = _committed_stock_map(db, item_ids, exclude_order_id=order.id)

    items_out: List[SalesOrderItemOut] = []
    for it in order.items:
        avail = avail_map.get(it.stock_item_id, Decimal("0.000000"))
        committed = committed_map.get(it.stock_item_id, Decimal("0.000000"))
        net_avail = max(Decimal("0.000000"), (avail - committed).quantize(QTY_PREC))
        req = Decimal(it.requested_quantity)
        shortage = max(Decimal("0.000000"), (req - net_avail).quantize(QTY_PREC))
        items_out.append(
            SalesOrderItemOut(
                id=it.id,
                product_id=it.product_id,
                product_name=it.product.name,
                sku=it.product.sku,
                pack_size=it.product.pack_size,
                hsn_code=it.hsn_code,
                unit_symbol=it.unit.symbol,
                requested_quantity=req,
                approved_quantity=Decimal(it.approved_quantity),
                dispatched_quantity=Decimal(it.dispatched_quantity),
                unit_price=Decimal(it.unit_price),
                submitted_unit_price=(
                    Decimal(it.submitted_unit_price)
                    if it.submitted_unit_price is not None
                    else None
                ),
                gst_rate=Decimal(it.gst_rate),
                taxable_value=Decimal(it.taxable_value),
                cgst_rate=Decimal(it.cgst_rate),
                sgst_rate=Decimal(it.sgst_rate),
                igst_rate=Decimal(it.igst_rate),
                cgst_amount=Decimal(it.cgst_amount),
                sgst_amount=Decimal(it.sgst_amount),
                igst_amount=Decimal(it.igst_amount),
                line_total=Decimal(it.line_total),
                available_stock=net_avail,
                shortage_quantity=shortage,
            )
        )

    return SalesOrderOut(
        id=order.id,
        order_number=order.order_number,
        customer_id=order.customer_id,
        customer_name=order.customer.name,
        customer_type=order.customer.customer_type.value,
        customer_gstin=order.customer.gstin,
        salesman_id=order.salesman_id,
        salesman_name=order.salesman.full_name,
        salesman_email=order.salesman.email,
        order_date=order.order_date,
        status=order.status,
        factory_state=order.factory_state,
        customer_state=order.customer_state,
        place_of_supply=order.place_of_supply,
        tax_type=order.tax_type,
        subtotal=Decimal(order.subtotal),
        cgst_amount=Decimal(order.cgst_amount),
        sgst_amount=Decimal(order.sgst_amount),
        igst_amount=Decimal(order.igst_amount),
        tax_amount=Decimal(order.tax_amount),
        total_amount=Decimal(order.total_amount),
        has_stock_shortage=order.has_stock_shortage,
        shortage_notes=order.shortage_notes,
        notes=order.notes,
        rejection_reason=order.rejection_reason,
        invoice_id=order.invoice.id if order.invoice else None,
        invoice_number=order.invoice.invoice_number if order.invoice else None,
        dispatch_id=order.dispatch.id if order.dispatch else None,
        dispatch_number=order.dispatch.dispatch_number if order.dispatch else None,
        idempotency_key=order.idempotency_key,
        local_order_id=order.local_order_id,
        is_offline_order=order.is_offline_order,
        offline_created_at=order.offline_created_at,
        synced_at=order.synced_at,
        price_review_required=order.price_review_required,
        price_conflict_notes=order.price_conflict_notes,
        created_at=order.created_at,
        updated_at=order.updated_at,
        items=items_out,
    )


def to_invoice_out(invoice: Invoice) -> InvoiceOut:
    return InvoiceOut(
        id=invoice.id,
        invoice_number=invoice.invoice_number,
        financial_year=invoice.financial_year,
        sequence_number=invoice.sequence_number,
        sales_order_id=invoice.sales_order_id,
        order_number=invoice.sales_order.order_number,
        customer_id=invoice.customer_id,
        invoice_date=invoice.invoice_date,
        status=invoice.status,
        factory_name=invoice.factory_name,
        factory_address=invoice.factory_address,
        factory_gstin=invoice.factory_gstin,
        factory_state=invoice.factory_state,
        factory_state_code=invoice.factory_state_code,
        customer_name=invoice.customer_name,
        customer_gstin=invoice.customer_gstin,
        billing_address=invoice.billing_address,
        customer_state=invoice.customer_state,
        place_of_supply=invoice.place_of_supply,
        tax_type=invoice.tax_type,
        subtotal=Decimal(invoice.subtotal),
        cgst_amount=Decimal(invoice.cgst_amount),
        sgst_amount=Decimal(invoice.sgst_amount),
        igst_amount=Decimal(invoice.igst_amount),
        tax_amount=Decimal(invoice.tax_amount),
        grand_total=Decimal(invoice.grand_total),
        amount_in_words=invoice.amount_in_words,
        created_by_email=invoice.creator.email,
        created_at=invoice.created_at,
        dispatch_id=invoice.dispatch.id if invoice.dispatch else None,
        dispatch_number=invoice.dispatch.dispatch_number if invoice.dispatch else None,
        items=[
            InvoiceItemOut(
                id=it.id,
                product_id=it.product_id,
                product_name=it.product_name,
                sku=it.sku,
                pack_size=it.pack_size,
                hsn_code=it.hsn_code,
                unit_symbol=it.unit_symbol,
                quantity=Decimal(it.quantity),
                unit_price=Decimal(it.unit_price),
                gst_rate=Decimal(it.gst_rate),
                taxable_value=Decimal(it.taxable_value),
                cgst_rate=Decimal(it.cgst_rate),
                sgst_rate=Decimal(it.sgst_rate),
                igst_rate=Decimal(it.igst_rate),
                cgst_amount=Decimal(it.cgst_amount),
                sgst_amount=Decimal(it.sgst_amount),
                igst_amount=Decimal(it.igst_amount),
                line_total=Decimal(it.line_total),
            )
            for it in invoice.items
        ],
        credit_notes=[
            CreditNoteOut(
                id=cn.id,
                credit_note_number=cn.credit_note_number,
                invoice_id=cn.invoice_id,
                financial_year=cn.financial_year,
                credit_date=cn.credit_date,
                reason=cn.reason,
                amount=Decimal(cn.amount),
                created_by_email=cn.creator.email,
                created_at=cn.created_at,
            )
            for cn in invoice.credit_notes
        ],
    )


def to_dispatch_out(dispatch: Dispatch) -> DispatchOut:
    return DispatchOut(
        id=dispatch.id,
        dispatch_number=dispatch.dispatch_number,
        sales_order_id=dispatch.sales_order_id,
        order_number=dispatch.sales_order.order_number,
        invoice_id=dispatch.invoice_id,
        invoice_number=dispatch.invoice.invoice_number,
        customer_name=dispatch.sales_order.customer.name,
        dispatch_date=dispatch.dispatch_date,
        vehicle_number=dispatch.vehicle_number,
        transporter_name=dispatch.transporter_name,
        notes=dispatch.notes,
        dispatched_by_email=dispatch.dispatcher.email,
        created_at=dispatch.created_at,
        items=[
            DispatchItemOut(
                id=it.id,
                product_id=it.product_id,
                product_name=it.product.name,
                sku=it.product.sku,
                stock_item_id=it.stock_item_id,
                quantity=Decimal(it.quantity),
                stock_ledger_id=it.stock_ledger_id,
            )
            for it in dispatch.items
        ],
    )


def _next_order_number(db: Session, order_date: date) -> str:
    prefix = f"SO-{order_date.year}-"
    existing = db.scalars(
        select(SalesOrder.order_number).where(SalesOrder.order_number.like(f"{prefix}%"))
    ).all()
    max_seq = 0
    for code in existing:
        tail = code.replace(prefix, "", 1)
        if tail.isdigit():
            max_seq = max(max_seq, int(tail))
    return f"{prefix}{max_seq + 1:04d}"


def _next_dispatch_number(db: Session, dispatch_date: date) -> str:
    prefix = f"DSP-{dispatch_date.year}-"
    existing = db.scalars(
        select(Dispatch.dispatch_number).where(Dispatch.dispatch_number.like(f"{prefix}%"))
    ).all()
    max_seq = 0
    for code in existing:
        tail = code.replace(prefix, "", 1)
        if tail.isdigit():
            max_seq = max(max_seq, int(tail))
    return f"{prefix}{max_seq + 1:04d}"


def get_sales_order_or_404(
    db: Session, order_id: str, *, actor: User | None = None
) -> SalesOrder:
    order = db.get(SalesOrder, order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sales order not found.")
    if actor and actor.role == Role.ORDER_MANAGER and order.salesman_id != actor.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view sales orders you submitted.",
        )
    return order


def list_sales_orders(
    db: Session,
    *,
    actor: User,
    search: str | None = None,
    customer_id: str | None = None,
    status_filter: SalesOrderStatus | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[SalesOrder], int]:
    filters = []
    if actor.role == Role.ORDER_MANAGER:
        filters.append(SalesOrder.salesman_id == actor.id)
    if search:
        term = f"%{search.strip()}%"
        filters.append(
            or_(
                SalesOrder.order_number.ilike(term),
                SalesOrder.customer.has(Customer.name.ilike(term)),
            )
        )
    if customer_id:
        filters.append(SalesOrder.customer_id == customer_id)
    if status_filter is not None:
        filters.append(SalesOrder.status == status_filter)
    if date_from is not None:
        filters.append(SalesOrder.order_date >= date_from)
    if date_to is not None:
        filters.append(SalesOrder.order_date <= date_to)

    total = int(db.scalar(select(func.count(SalesOrder.id)).where(*filters)) or 0)
    stmt = (
        select(SalesOrder)
        .where(*filters)
        .order_by(SalesOrder.created_at.desc(), SalesOrder.order_number.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(db.scalars(stmt).unique().all()), total


def create_sales_order(
    db: Session,
    payload: SalesOrderCreate,
    *,
    actor: User,
    ip_address: str | None = None,
) -> SalesOrder:
    customer = db.get(Customer, payload.customer_id)
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found.")
    if not customer.is_active:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Cannot place an order for an inactive customer.",
        )
    if actor.role == Role.ORDER_MANAGER and customer.assigned_salesman_id != actor.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only submit sales orders for customers assigned to you.",
        )

    order_date = payload.order_date or date.today()
    order_number = (
        payload.order_number.strip().upper()
        if payload.order_number
        else _next_order_number(db, order_date)
    )
    if db.scalar(select(SalesOrder).where(func.upper(SalesOrder.order_number) == order_number)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Sales order '{order_number}' already exists.",
        )

    settings = get_settings()
    tax_type = determine_tax_type(
        settings.factory_state,
        customer.state,
        settings.factory_state_code,
        customer.state_code,
    )

    seen_products = set()
    items: List[SalesOrderItem] = []
    stock_item_ids: List[str] = []
    for row in payload.items:
        if row.product_id in seen_products:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Duplicate product line in sales order.",
            )
        seen_products.add(row.product_id)

        product = db.get(Product, row.product_id)
        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")
        if not product.is_active:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Product '{product.name}' is inactive.",
            )
        stock_item_ids.append(product.stock_item_id)
        items.append(
            SalesOrderItem(
                product_id=product.id,
                stock_item_id=product.stock_item_id,
                unit_id=product.unit_id,
                hsn_code=product.hsn_code,
                requested_quantity=row.quantity,
                approved_quantity=row.quantity,
                dispatched_quantity=Decimal("0.000000"),
                unit_price=Decimal(product.selling_price),
                gst_rate=Decimal(product.gst_rate),
                taxable_value=Decimal("0.00"),
                line_total=Decimal("0.00"),
            )
        )

    avail_map = _stock_balance_map(db, stock_item_ids)
    committed_map = _committed_stock_map(db, stock_item_ids)
    shortage_msgs: List[str] = []
    for it in items:
        net_avail = max(
            Decimal("0.000000"),
            avail_map.get(it.stock_item_id, Decimal("0")) - committed_map.get(it.stock_item_id, Decimal("0")),
        )
        if Decimal(it.requested_quantity) > net_avail:
            shortage = (Decimal(it.requested_quantity) - net_avail).quantize(QTY_PREC)
            shortage_msgs.append(f"Requested {it.requested_quantity}, available {net_avail}, shortage {shortage}")

    order = SalesOrder(
        order_number=order_number,
        customer_id=customer.id,
        salesman_id=actor.id,
        order_date=order_date,
        status=SalesOrderStatus.SUBMITTED,
        factory_state=settings.factory_state,
        customer_state=customer.state,
        place_of_supply=format_place_of_supply(customer.state, customer.state_code),
        tax_type=tax_type,
        has_stock_shortage=bool(shortage_msgs),
        shortage_notes="; ".join(shortage_msgs) if shortage_msgs else None,
        notes=payload.notes.strip() if payload.notes else None,
        items=items,
    )
    _recalculate_order_totals(order)
    db.add(order)
    db.flush()

    record_audit_event(
        db,
        actor_id=actor.id,
        actor_email=actor.email,
        actor_role=actor.role.value,
        action="sales_order.submitted",
        resource_type="sales_order",
        resource_id=order.id,
        details=f"{order.order_number} for {customer.name} total={order.total_amount}",
        ip_address=ip_address,
        commit=False,
    )
    db.commit()
    db.refresh(order)
    return order


def update_sales_order(
    db: Session,
    order_id: str,
    payload: SalesOrderUpdate,
    *,
    actor: User,
    ip_address: str | None = None,
) -> SalesOrder:
    order = get_sales_order_or_404(db, order_id)
    if order.status not in {
        SalesOrderStatus.SUBMITTED,
        SalesOrderStatus.UNDER_REVIEW,
        SalesOrderStatus.AWAITING_STOCK,
    }:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot modify sales order in {order.status.value} status.",
        )

    if payload.status is not None:
        if payload.status not in {
            SalesOrderStatus.SUBMITTED,
            SalesOrderStatus.UNDER_REVIEW,
            SalesOrderStatus.AWAITING_STOCK,
            SalesOrderStatus.CANCELLED,
        }:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Use /approve, /reject, /invoices, or /dispatches for protected transitions.",
            )
        order.status = payload.status
        if payload.status == SalesOrderStatus.UNDER_REVIEW:
            order.reviewed_by = actor.id
            order.reviewed_at = _utcnow()

    if payload.notes is not None:
        order.notes = payload.notes.strip() or None

    if payload.items is not None:
        seen = set()
        rebuilt: List[SalesOrderItem] = []
        for row in payload.items:
            if row.product_id in seen:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Duplicate product line in order update.",
                )
            seen.add(row.product_id)
            product = db.get(Product, row.product_id)
            if not product:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")
            price = Decimal(row.unit_price) if row.unit_price is not None else Decimal(product.selling_price)
            rebuilt.append(
                SalesOrderItem(
                    product_id=product.id,
                    stock_item_id=product.stock_item_id,
                    unit_id=product.unit_id,
                    hsn_code=product.hsn_code,
                    requested_quantity=row.quantity,
                    approved_quantity=row.quantity,
                    dispatched_quantity=Decimal("0.000000"),
                    unit_price=price,
                    gst_rate=Decimal(product.gst_rate),
                    taxable_value=Decimal("0.00"),
                    line_total=Decimal("0.00"),
                )
            )
        order.items.clear()
        db.flush()
        order.items.extend(rebuilt)

    _recalculate_order_totals(order)
    order.reviewed_by = actor.id
    order.reviewed_at = _utcnow()

    record_audit_event(
        db,
        actor_id=actor.id,
        actor_email=actor.email,
        actor_role=actor.role.value,
        action="sales_order.updated",
        resource_type="sales_order",
        resource_id=order.id,
        details=f"Updated {order.order_number} status={order.status.value} total={order.total_amount}",
        ip_address=ip_address,
        commit=False,
    )
    db.commit()
    db.refresh(order)
    return order


def check_sales_order_stock(
    db: Session,
    order_id: str,
    *,
    actor: User,
) -> SalesOrderStockCheckOut:
    order = get_sales_order_or_404(db, order_id, actor=actor)
    item_ids = [it.stock_item_id for it in order.items]
    avail_map = _stock_balance_map(db, item_ids)
    committed_map = _committed_stock_map(db, item_ids, exclude_order_id=order.id)

    lines: List[StockCheckLineOut] = []
    all_ok = True
    for it in order.items:
        avail = avail_map.get(it.stock_item_id, Decimal("0.000000"))
        committed = committed_map.get(it.stock_item_id, Decimal("0.000000"))
        net_avail = max(Decimal("0.000000"), (avail - committed).quantize(QTY_PREC))
        req = Decimal(it.requested_quantity)
        shortage = max(Decimal("0.000000"), (req - net_avail).quantize(QTY_PREC))
        ok = shortage == Decimal("0.000000")
        if not ok:
            all_ok = False
        lines.append(
            StockCheckLineOut(
                product_id=it.product_id,
                product_name=it.product.name,
                sku=it.product.sku,
                unit_symbol=it.unit.symbol,
                requested_quantity=req,
                available_stock=avail,
                committed_stock=committed,
                net_available_stock=net_avail,
                shortage_quantity=shortage,
                sufficient=ok,
            )
        )

    return SalesOrderStockCheckOut(
        sales_order_id=order.id,
        order_number=order.order_number,
        status=order.status,
        tax_type=order.tax_type,
        all_available=all_ok,
        recommended_action="APPROVE" if all_ok else "HOLD_AWAITING_STOCK",
        subtotal_preview=Decimal(order.subtotal),
        cgst_preview=Decimal(order.cgst_amount),
        sgst_preview=Decimal(order.sgst_amount),
        igst_preview=Decimal(order.igst_amount),
        total_preview=Decimal(order.total_amount),
        lines=lines,
    )


def approve_sales_order(
    db: Session,
    order_id: str,
    payload: SalesOrderApproveRequest,
    *,
    actor: User,
    ip_address: str | None = None,
) -> SalesOrder:
    order = get_sales_order_or_404(db, order_id)
    if order.status in {
        SalesOrderStatus.APPROVED,
        SalesOrderStatus.PARTIALLY_FULFILLED,
        SalesOrderStatus.INVOICED,
        SalesOrderStatus.DISPATCHED,
    }:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Sales order '{order.order_number}' is already {order.status.value}.",
        )
    if order.status in {SalesOrderStatus.REJECTED, SalesOrderStatus.CANCELLED}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot approve a {order.status.value} sales order.",
        )

    item_ids = [it.stock_item_id for it in order.items]
    # Lock balance projection rows inside the approval transaction to prevent concurrent overselling.
    locked_avail: Dict[str, Decimal] = {}
    for sid in item_ids:
        bal = get_or_create_locked_balance(db, sid)
        locked_avail[sid] = Decimal(bal.available_quantity)
    committed_map = _committed_stock_map(db, item_ids, exclude_order_id=order.id)

    shortages: List[Tuple[SalesOrderItem, Decimal, Decimal]] = []
    for it in order.items:
        net_avail = max(
            Decimal("0.000000"),
            locked_avail[it.stock_item_id] - committed_map.get(it.stock_item_id, Decimal("0.000000")),
        )
        req = Decimal(it.requested_quantity)
        if net_avail < req:
            shortage = (req - net_avail).quantize(QTY_PREC)
            shortages.append((it, net_avail, shortage))

    now = _utcnow()
    if shortages:
        msg = "; ".join(
            f"{it.product.name}: Requested {int(it.requested_quantity) if it.requested_quantity == int(it.requested_quantity) else it.requested_quantity}, "
            f"Available {int(avail) if avail == int(avail) else avail}, Shortage {int(short) if short == int(short) else short}"
            for it, avail, short in shortages
        )
        if payload.allow_partial and all(avail > Decimal("0") for _, avail, _ in shortages):
            for it, avail, _ in shortages:
                it.approved_quantity = avail
            order.status = SalesOrderStatus.PARTIALLY_FULFILLED
            order.has_stock_shortage = True
            order.shortage_notes = msg
            order.approved_by = actor.id
            order.approved_at = now
            _recalculate_order_totals(order)
            audit_action = "sales_order.partially_approved"
        elif payload.hold_if_insufficient:
            order.status = SalesOrderStatus.AWAITING_STOCK
            order.has_stock_shortage = True
            order.shortage_notes = msg
            order.reviewed_by = actor.id
            order.reviewed_at = now
            audit_action = "sales_order.held_awaiting_stock"
        else:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Insufficient finished-goods stock — {msg}",
            )
    else:
        for it in order.items:
            it.approved_quantity = it.requested_quantity
        order.status = SalesOrderStatus.APPROVED
        order.has_stock_shortage = False
        order.shortage_notes = None
        order.approved_by = actor.id
        order.approved_at = now
        _recalculate_order_totals(order)
        audit_action = "sales_order.approved"

    if payload.notes:
        order.notes = payload.notes.strip()

    record_audit_event(
        db,
        actor_id=actor.id,
        actor_email=actor.email,
        actor_role=actor.role.value,
        action=audit_action,
        resource_type="sales_order",
        resource_id=order.id,
        details=f"{order.order_number} -> {order.status.value}",
        ip_address=ip_address,
        commit=False,
    )
    db.commit()
    db.refresh(order)
    return order


def reject_sales_order(
    db: Session,
    order_id: str,
    reason: str,
    *,
    actor: User,
    ip_address: str | None = None,
) -> SalesOrder:
    order = get_sales_order_or_404(db, order_id)
    if order.status in {SalesOrderStatus.INVOICED, SalesOrderStatus.DISPATCHED, SalesOrderStatus.REJECTED}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot reject sales order in {order.status.value} status.",
        )

    order.status = SalesOrderStatus.REJECTED
    order.rejected_by = actor.id
    order.rejected_at = _utcnow()
    order.rejection_reason = reason.strip()

    record_audit_event(
        db,
        actor_id=actor.id,
        actor_email=actor.email,
        actor_role=actor.role.value,
        action="sales_order.rejected",
        resource_type="sales_order",
        resource_id=order.id,
        details=f"Rejected {order.order_number}: {order.rejection_reason}",
        ip_address=ip_address,
        commit=False,
    )
    db.commit()
    db.refresh(order)
    return order


def list_invoices(
    db: Session,
    *,
    search: str | None = None,
    customer_id: str | None = None,
    financial_year: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[Invoice], int]:
    filters = []
    if search:
        term = f"%{search.strip()}%"
        filters.append(
            or_(
                Invoice.invoice_number.ilike(term),
                Invoice.customer_name.ilike(term),
                Invoice.customer_gstin.ilike(term),
            )
        )
    if customer_id:
        filters.append(Invoice.customer_id == customer_id)
    if financial_year:
        filters.append(Invoice.financial_year == financial_year)

    total = int(db.scalar(select(func.count(Invoice.id)).where(*filters)) or 0)
    stmt = (
        select(Invoice)
        .where(*filters)
        .order_by(Invoice.invoice_date.desc(), Invoice.sequence_number.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(db.scalars(stmt).unique().all()), total


def get_invoice_or_404(db: Session, invoice_id: str) -> Invoice:
    inv = db.get(Invoice, invoice_id)
    if not inv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found.")
    return inv


def create_invoice(
    db: Session,
    payload: InvoiceCreate,
    *,
    actor: User,
    ip_address: str | None = None,
) -> Invoice:
    order = get_sales_order_or_404(db, payload.sales_order_id)
    if order.invoice is not None or order.status in {SalesOrderStatus.INVOICED, SalesOrderStatus.DISPATCHED}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"An invoice already exists for order '{order.order_number}'.",
        )
    if order.status not in {SalesOrderStatus.APPROVED, SalesOrderStatus.PARTIALLY_FULFILLED}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Order '{order.order_number}' must be APPROVED before invoicing (current: {order.status.value}).",
        )

    # Re-verify available finished-goods stock before issuing GST tax invoice (do NOT deduct yet).
    item_ids = [it.stock_item_id for it in order.items]
    avail_map: Dict[str, Decimal] = {}
    for sid in item_ids:
        bal = get_or_create_locked_balance(db, sid)
        avail_map[sid] = Decimal(bal.available_quantity)
    committed_map = _committed_stock_map(db, item_ids, exclude_order_id=order.id)

    for it in order.items:
        net_avail = max(Decimal("0.000000"), avail_map[it.stock_item_id] - committed_map.get(it.stock_item_id, Decimal("0.000000")))
        qty = Decimal(it.approved_quantity)
        if qty <= Decimal("0") or net_avail < qty:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Insufficient finished-goods stock for {it.product.name} ({qty} needed, {net_avail} available).",
            )

    settings = get_settings()
    inv_date = payload.invoice_date or date.today()
    fy = get_financial_year(inv_date)
    max_seq = db.scalar(
        select(func.coalesce(func.max(Invoice.sequence_number), 0)).where(
            Invoice.financial_year == fy
        )
    )
    seq = int(max_seq or 0) + 1
    inv_number = f"INV/{fy}/{seq:04d}"

    _recalculate_order_totals(order)
    inv_items = [
        InvoiceItem(
            sales_order_item_id=it.id,
            product_id=it.product_id,
            product_name=it.product.name,
            sku=it.product.sku,
            pack_size=it.product.pack_size,
            hsn_code=it.hsn_code,
            unit_symbol=it.unit.symbol,
            quantity=Decimal(it.approved_quantity),
            unit_price=Decimal(it.unit_price),
            gst_rate=Decimal(it.gst_rate),
            taxable_value=Decimal(it.taxable_value),
            cgst_rate=Decimal(it.cgst_rate),
            sgst_rate=Decimal(it.sgst_rate),
            igst_rate=Decimal(it.igst_rate),
            cgst_amount=Decimal(it.cgst_amount),
            sgst_amount=Decimal(it.sgst_amount),
            igst_amount=Decimal(it.igst_amount),
            line_total=Decimal(it.line_total),
        )
        for it in order.items
    ]

    invoice = Invoice(
        invoice_number=inv_number,
        financial_year=fy,
        sequence_number=seq,
        sales_order_id=order.id,
        customer_id=order.customer_id,
        invoice_date=inv_date,
        status=InvoiceStatus.POSTED,
        factory_name=settings.factory_name,
        factory_address=settings.factory_address,
        factory_gstin=settings.factory_gstin,
        factory_state=order.factory_state,
        factory_state_code=settings.factory_state_code,
        customer_name=order.customer.name,
        customer_gstin=order.customer.gstin,
        billing_address=f"{order.customer.address}, {order.customer.city}, {order.customer.state}",
        customer_state=order.customer_state,
        place_of_supply=order.place_of_supply,
        tax_type=order.tax_type,
        subtotal=Decimal(order.subtotal),
        cgst_amount=Decimal(order.cgst_amount),
        sgst_amount=Decimal(order.sgst_amount),
        igst_amount=Decimal(order.igst_amount),
        tax_amount=Decimal(order.tax_amount),
        grand_total=Decimal(order.total_amount),
        amount_in_words=amount_to_inr_words(Decimal(order.total_amount)),
        created_by=actor.id,
        items=inv_items,
    )
    order.status = SalesOrderStatus.INVOICED
    db.add(invoice)
    db.flush()

    record_audit_event(
        db,
        actor_id=actor.id,
        actor_email=actor.email,
        actor_role=actor.role.value,
        action="invoice.posted",
        resource_type="invoice",
        resource_id=invoice.id,
        details=f"{invoice.invoice_number} for {order.order_number} grand_total={invoice.grand_total}",
        ip_address=ip_address,
        commit=False,
    )
    db.commit()
    db.refresh(invoice)
    return invoice


def create_credit_note(
    db: Session,
    invoice_id: str,
    payload: CreditNoteCreate,
    *,
    actor: User,
    ip_address: str | None = None,
) -> CreditNote:
    invoice = get_invoice_or_404(db, invoice_id)
    credited_so_far = sum((Decimal(cn.amount) for cn in invoice.credit_notes), Decimal("0.00"))
    remaining = (Decimal(invoice.grand_total) - credited_so_far).quantize(AMT_PREC)
    amount = Decimal(payload.amount).quantize(AMT_PREC) if payload.amount is not None else remaining
    if amount <= Decimal("0.00") or amount > remaining:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Credit note amount {amount} exceeds remaining invoice balance {remaining}.",
        )

    c_date = payload.credit_date or date.today()
    fy = get_financial_year(c_date)
    prefix = f"CN/{fy}/"
    existing = db.scalars(
        select(CreditNote.credit_note_number).where(CreditNote.credit_note_number.like(f"{prefix}%"))
    ).all()
    max_seq = 0
    for code in existing:
        tail = code.replace(prefix, "", 1)
        if tail.isdigit():
            max_seq = max(max_seq, int(tail))
    cn_number = f"{prefix}{max_seq + 1:04d}"

    cn = CreditNote(
        credit_note_number=cn_number,
        invoice_id=invoice.id,
        financial_year=fy,
        credit_date=c_date,
        reason=payload.reason.strip(),
        amount=amount,
        created_by=actor.id,
    )
    db.add(cn)
    db.flush()

    record_audit_event(
        db,
        actor_id=actor.id,
        actor_email=actor.email,
        actor_role=actor.role.value,
        action="invoice.credit_note_issued",
        resource_type="credit_note",
        resource_id=cn.id,
        details=f"{cn.credit_note_number} against {invoice.invoice_number} amount={cn.amount}",
        ip_address=ip_address,
        commit=False,
    )
    db.commit()
    db.refresh(cn)
    return cn


def list_dispatches(
    db: Session,
    *,
    search: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[Dispatch], int]:
    filters = []
    if search:
        term = f"%{search.strip()}%"
        filters.append(
            or_(
                Dispatch.dispatch_number.ilike(term),
                Dispatch.vehicle_number.ilike(term),
                Dispatch.sales_order.has(SalesOrder.order_number.ilike(term)),
            )
        )
    total = int(db.scalar(select(func.count(Dispatch.id)).where(*filters)) or 0)
    stmt = (
        select(Dispatch)
        .where(*filters)
        .order_by(Dispatch.dispatch_date.desc(), Dispatch.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(db.scalars(stmt).unique().all()), total


def get_dispatch_or_404(db: Session, dispatch_id: str) -> Dispatch:
    dispatch = db.get(Dispatch, dispatch_id)
    if not dispatch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dispatch record not found.")
    return dispatch


def create_dispatch(
    db: Session,
    payload: DispatchCreate,
    *,
    actor: User,
    ip_address: str | None = None,
) -> Dispatch:
    """Atomically record physical dispatch and deduct finished-goods stock via StockLedger."""
    order = get_sales_order_or_404(db, payload.sales_order_id)
    if order.dispatch is not None or order.status == SalesOrderStatus.DISPATCHED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Order '{order.order_number}' has already been dispatched.",
        )
    if order.invoice is None or order.status != SalesOrderStatus.INVOICED:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Order '{order.order_number}' must be INVOICED before dispatch.",
        )

    disp_date = payload.dispatch_date or date.today()
    disp_number = _next_dispatch_number(db, disp_date)
    tx_dt = datetime.combine(disp_date, datetime.now(timezone.utc).time(), tzinfo=timezone.utc)
    invoice = order.invoice

    try:
        dispatch = Dispatch(
            dispatch_number=disp_number,
            sales_order_id=order.id,
            invoice_id=invoice.id,
            dispatch_date=disp_date,
            vehicle_number=payload.vehicle_number.strip() if payload.vehicle_number else None,
            transporter_name=payload.transporter_name.strip() if payload.transporter_name else None,
            notes=payload.notes.strip() if payload.notes else None,
            dispatched_by=actor.id,
        )
        db.add(dispatch)
        db.flush()

        for it in order.items:
            qty_out = Decimal(it.approved_quantity).quantize(QTY_PREC, rounding=ROUND_HALF_UP)
            ledger_entry = apply_stock_movement(
                db,
                stock_item=it.stock_item,
                movement_type=MovementType.SALES_DISPATCH,
                quantity_out=qty_out,
                reference_doc_type="DISPATCH",
                reference_doc_id=dispatch.dispatch_number,
                transaction_date=tx_dt,
                notes=f"Dispatch {dispatch.dispatch_number} | Invoice {invoice.invoice_number} | Order {order.order_number}",
                created_by=actor.id,
            )
            db.add(
                DispatchItem(
                    dispatch_id=dispatch.id,
                    sales_order_item_id=it.id,
                    product_id=it.product_id,
                    stock_item_id=it.stock_item_id,
                    quantity=qty_out,
                    stock_ledger_id=ledger_entry.id,
                )
            )
            it.dispatched_quantity = qty_out

        order.status = SalesOrderStatus.DISPATCHED

        record_audit_event(
            db,
            actor_id=actor.id,
            actor_email=actor.email,
            actor_role=actor.role.value,
            action="dispatch.posted",
            resource_type="dispatch",
            resource_id=dispatch.id,
            details=f"{dispatch.dispatch_number} for {invoice.invoice_number} ({order.order_number})",
            ip_address=ip_address,
            commit=False,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(dispatch)
    return dispatch


def build_sales_overview(db: Session, *, actor: User) -> SalesOverviewOut:
    """Summarize orders, GST totals, and customer-wise sales scoped to role."""
    stmt = select(SalesOrder)
    if actor.role == Role.ORDER_MANAGER:
        stmt = stmt.where(SalesOrder.salesman_id == actor.id)
    orders = list(db.scalars(stmt).unique().all())

    pending_review = sum(
        1 for o in orders if o.status in {SalesOrderStatus.SUBMITTED, SalesOrderStatus.UNDER_REVIEW}
    )
    awaiting_stock = sum(1 for o in orders if o.status == SalesOrderStatus.AWAITING_STOCK)
    invoiced_count = sum(1 for o in orders if o.invoice is not None)
    dispatched_count = sum(1 for o in orders if o.status == SalesOrderStatus.DISPATCHED)

    total_sales_val = sum(
        (Decimal(o.total_amount) for o in orders if o.status not in {SalesOrderStatus.REJECTED, SalesOrderStatus.CANCELLED}),
        Decimal("0.00"),
    ).quantize(AMT_PREC)
    total_gst = sum(
        (Decimal(o.invoice.tax_amount) for o in orders if o.invoice is not None),
        Decimal("0.00"),
    ).quantize(AMT_PREC)

    by_customer: Dict[str, CustomerSalesSummaryRow] = {}
    for o in orders:
        c = o.customer
        row = by_customer.get(c.id)
        order_val = (
            Decimal(o.total_amount)
            if o.status not in {SalesOrderStatus.REJECTED, SalesOrderStatus.CANCELLED}
            else Decimal("0.00")
        )
        inv_val = Decimal(o.invoice.grand_total) if o.invoice else Decimal("0.00")
        if row is None:
            by_customer[c.id] = CustomerSalesSummaryRow(
                customer_id=c.id,
                customer_name=c.name,
                customer_type=c.customer_type.value,
                customer_state=c.state,
                orders_count=1,
                dispatched_count=1 if o.status == SalesOrderStatus.DISPATCHED else 0,
                total_order_value=order_val.quantize(AMT_PREC),
                invoiced_value=inv_val.quantize(AMT_PREC),
            )
        else:
            row.orders_count += 1
            if o.status == SalesOrderStatus.DISPATCHED:
                row.dispatched_count += 1
            row.total_order_value = (row.total_order_value + order_val).quantize(AMT_PREC)
            row.invoiced_value = (row.invoiced_value + inv_val).quantize(AMT_PREC)

    summary_rows = sorted(by_customer.values(), key=lambda r: r.total_order_value, reverse=True)
    return SalesOverviewOut(
        total_orders=len(orders),
        pending_review=pending_review,
        awaiting_stock=awaiting_stock,
        invoiced_count=invoiced_count,
        dispatched_count=dispatched_count,
        total_sales_value=total_sales_val,
        total_gst_collected=total_gst,
        customer_summary=summary_rows,
    )


def _extract_price_conflicts(order: SalesOrder) -> List[PriceConflictLineOut]:
    conflicts: List[PriceConflictLineOut] = []
    for it in order.items:
        if it.submitted_unit_price is None:
            continue
        sub_p = Decimal(it.submitted_unit_price).quantize(AMT_PREC)
        srv_p = Decimal(it.unit_price).quantize(AMT_PREC)
        if sub_p != srv_p:
            conflicts.append(
                PriceConflictLineOut(
                    product_id=it.product_id,
                    product_name=it.product.name,
                    submitted_unit_price=sub_p,
                    current_server_price=srv_p,
                    difference=(srv_p - sub_p).quantize(AMT_PREC),
                )
            )
    return conflicts


def _to_sync_response(
    db: Session, order: SalesOrder, *, duplicate: bool, fallback_local_id: str
) -> SalesOrderSyncResponse:
    conflicts = _extract_price_conflicts(order)
    sync_stat = "NEEDS_REVIEW" if (order.price_review_required or conflicts) else "SYNCED"
    return SalesOrderSyncResponse(
        local_order_id=order.local_order_id or fallback_local_id,
        idempotency_key=order.idempotency_key or "",
        server_order_id=order.id,
        server_order_number=order.order_number,
        server_status=order.status,
        sync_status=sync_stat,
        duplicate=duplicate,
        price_review_required=order.price_review_required,
        price_conflict_notes=order.price_conflict_notes,
        price_conflicts=conflicts,
        synced_at=order.synced_at or order.created_at,
        order=to_sales_order_out(db, order),
    )


def _record_sync_failure_audit(
    db: Session, *, actor: User, local_order_id: str, idempotency_key: str, reason: str, ip_address: str | None
) -> None:
    record_audit_event(
        db,
        actor_id=actor.id,
        actor_email=actor.email,
        actor_role=actor.role.value,
        action="sales_order.sync_failed",
        resource_type="sales_order",
        resource_id=local_order_id,
        status="FAILURE",
        details=f"idempotency_key={idempotency_key}; reason={reason}",
        ip_address=ip_address,
        commit=True,
    )


def sync_offline_sales_order(
    db: Session,
    payload: SalesOrderSyncRequest,
    *,
    actor: User,
    ip_address: str | None = None,
) -> SalesOrderSyncResponse:
    """Idempotently synchronize an offline sales order into PostgreSQL as SUBMITTED."""
    idem_key = payload.idempotency_key.strip()
    local_id = payload.local_order_id.strip()

    existing = db.scalar(select(SalesOrder).where(SalesOrder.idempotency_key == idem_key))
    if existing is not None:
        if actor.role == Role.ORDER_MANAGER and existing.salesman_id != actor.id:
            _record_sync_failure_audit(
                db,
                actor=actor,
                local_order_id=local_id,
                idempotency_key=idem_key,
                reason="Idempotency key belongs to a different salesman.",
                ip_address=ip_address,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This idempotency key belongs to another salesman.",
            )
        record_audit_event(
            db,
            actor_id=actor.id,
            actor_email=actor.email,
            actor_role=actor.role.value,
            action="sales_order.sync_idempotent_replay",
            resource_type="sales_order",
            resource_id=existing.id,
            details=f"local_id={local_id}; key={idem_key}; server_order={existing.order_number}",
            ip_address=ip_address,
            commit=True,
        )
        return _to_sync_response(db, existing, duplicate=True, fallback_local_id=local_id)

    customer = db.get(Customer, payload.customer_id)
    if not customer:
        _record_sync_failure_audit(
            db, actor=actor, local_order_id=local_id, idempotency_key=idem_key, reason="Customer not found", ip_address=ip_address
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found.")
    if not customer.is_active:
        _record_sync_failure_audit(
            db, actor=actor, local_order_id=local_id, idempotency_key=idem_key, reason="Inactive customer", ip_address=ip_address
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Cannot synchronize an order for an inactive customer.",
        )
    if actor.role == Role.ORDER_MANAGER and customer.assigned_salesman_id != actor.id:
        _record_sync_failure_audit(
            db, actor=actor, local_order_id=local_id, idempotency_key=idem_key, reason="Customer not assigned to salesman", ip_address=ip_address
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only synchronize orders for customers assigned to you.",
        )

    settings = get_settings()
    tax_type = determine_tax_type(
        settings.factory_state,
        customer.state,
        settings.factory_state_code,
        customer.state_code,
    )

    seen_products = set()
    items: List[SalesOrderItem] = []
    stock_item_ids: List[str] = []
    conflict_notes_parts: List[str] = []

    for row in payload.items:
        if row.product_id in seen_products:
            _record_sync_failure_audit(
                db, actor=actor, local_order_id=local_id, idempotency_key=idem_key, reason="Duplicate product line", ip_address=ip_address
            )
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Duplicate product line in synced order.",
            )
        seen_products.add(row.product_id)

        product = db.get(Product, row.product_id)
        if not product:
            _record_sync_failure_audit(
                db, actor=actor, local_order_id=local_id, idempotency_key=idem_key, reason=f"Product {row.product_id} not found", ip_address=ip_address
            )
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")
        if not product.is_active:
            _record_sync_failure_audit(
                db, actor=actor, local_order_id=local_id, idempotency_key=idem_key, reason=f"Inactive product {product.sku}", ip_address=ip_address
            )
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Product '{product.name}' is inactive.",
            )

        submitted_price = Decimal(row.cached_unit_price).quantize(AMT_PREC)
        server_price = Decimal(product.selling_price).quantize(AMT_PREC)
        if submitted_price != server_price:
            conflict_notes_parts.append(
                f"{product.name} ({product.sku}): cached offline Rs {submitted_price} vs current server Rs {server_price}"
            )

        stock_item_ids.append(product.stock_item_id)
        items.append(
            SalesOrderItem(
                product_id=product.id,
                stock_item_id=product.stock_item_id,
                unit_id=product.unit_id,
                hsn_code=product.hsn_code,
                requested_quantity=row.quantity,
                approved_quantity=row.quantity,
                dispatched_quantity=Decimal("0.000000"),
                unit_price=server_price,
                submitted_unit_price=submitted_price,
                gst_rate=Decimal(product.gst_rate),
                taxable_value=Decimal("0.00"),
                line_total=Decimal("0.00"),
            )
        )

    avail_map = _stock_balance_map(db, stock_item_ids)
    committed_map = _committed_stock_map(db, stock_item_ids)
    shortage_msgs: List[str] = []
    for it in items:
        net_avail = max(
            Decimal("0.000000"),
            avail_map.get(it.stock_item_id, Decimal("0")) - committed_map.get(it.stock_item_id, Decimal("0")),
        )
        if Decimal(it.requested_quantity) > net_avail:
            shortage = (Decimal(it.requested_quantity) - net_avail).quantize(QTY_PREC)
            shortage_msgs.append(f"Requested {it.requested_quantity}, available {net_avail}, shortage {shortage}")

    order_date = payload.order_date or payload.offline_created_at.date()
    sync_time = _utcnow()
    order = SalesOrder(
        order_number=_next_order_number(db, order_date),
        customer_id=customer.id,
        salesman_id=actor.id,
        order_date=order_date,
        status=SalesOrderStatus.SUBMITTED,
        factory_state=settings.factory_state,
        customer_state=customer.state,
        place_of_supply=format_place_of_supply(customer.state, customer.state_code),
        tax_type=tax_type,
        has_stock_shortage=bool(shortage_msgs),
        shortage_notes="; ".join(shortage_msgs) if shortage_msgs else None,
        notes=payload.notes.strip() if payload.notes else None,
        idempotency_key=idem_key,
        local_order_id=local_id,
        is_offline_order=True,
        offline_created_at=payload.offline_created_at,
        synced_at=sync_time,
        price_review_required=bool(conflict_notes_parts),
        price_conflict_notes="; ".join(conflict_notes_parts) if conflict_notes_parts else None,
        items=items,
    )
    _recalculate_order_totals(order)

    try:
        db.add(order)
        db.flush()
        record_audit_event(
            db,
            actor_id=actor.id,
            actor_email=actor.email,
            actor_role=actor.role.value,
            action="sales_order.sync_created",
            resource_type="sales_order",
            resource_id=order.id,
            details=(
                f"{order.order_number} local={local_id} key={idem_key} "
                f"price_review={order.price_review_required} total={order.total_amount}"
            ),
            ip_address=ip_address,
            commit=False,
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        winner = db.scalar(select(SalesOrder).where(SalesOrder.idempotency_key == idem_key))
        if winner is not None:
            return _to_sync_response(db, winner, duplicate=True, fallback_local_id=local_id)
        raise

    db.refresh(order)
    return _to_sync_response(db, order, duplicate=False, fallback_local_id=local_id)
