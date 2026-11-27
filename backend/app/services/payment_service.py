from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Tuple

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.costing_payment import CustomerPaymentStatus, Payment, PaymentAllocation
from app.models.customer import Customer
from app.models.sales import CreditNote, Invoice
from app.models.user import User
from app.schemas.costing_payment import (
    AgeingBucketSummary,
    CustomerLedgerEntryOut,
    CustomerLedgerOut,
    CustomerReceivableSummary,
    CustomerStatementOut,
    InvoicePaymentStatusRow,
    InvoicePaymentsDetailOut,
    PaymentAllocateRequest,
    PaymentAllocationOut,
    PaymentCreate,
    PaymentOut,
    ReceivablesAgeingReportOut,
    ReceivablesReportOut,
)
from app.services.audit_service import record_audit_event

AMT_PREC = Decimal("0.01")

AGEING_BUCKETS = [
    "Current / Not Due",
    "1-30 days overdue",
    "31-60 days overdue",
    "61-90 days overdue",
    "More than 90 days overdue",
]


def _classify_ageing(days_overdue: int) -> str:
    if days_overdue <= 0:
        return "Current / Not Due"
    if days_overdue <= 30:
        return "1-30 days overdue"
    if days_overdue <= 60:
        return "31-60 days overdue"
    if days_overdue <= 90:
        return "61-90 days overdue"
    return "More than 90 days overdue"


def _invoice_paid_map(db: Session, invoice_ids: List[str]) -> Dict[str, Decimal]:
    if not invoice_ids:
        return {}
    rows = db.execute(
        select(
            PaymentAllocation.invoice_id,
            func.coalesce(func.sum(PaymentAllocation.allocated_amount), 0),
        )
        .join(Payment, Payment.id == PaymentAllocation.payment_id)
        .where(
            PaymentAllocation.invoice_id.in_(invoice_ids),
            Payment.status == CustomerPaymentStatus.POSTED,
        )
        .group_by(PaymentAllocation.invoice_id)
    ).all()
    return {row[0]: Decimal(str(row[1])).quantize(AMT_PREC) for row in rows}


def _invoice_credit_map(db: Session, invoice_ids: List[str]) -> Dict[str, Decimal]:
    if not invoice_ids:
        return {}
    rows = db.execute(
        select(
            CreditNote.invoice_id,
            func.coalesce(func.sum(CreditNote.amount), 0),
        )
        .where(CreditNote.invoice_id.in_(invoice_ids))
        .group_by(CreditNote.invoice_id)
    ).all()
    return {row[0]: Decimal(str(row[1])).quantize(AMT_PREC) for row in rows}


def build_invoice_payment_row(
    db: Session,
    invoice: Invoice,
    *,
    as_of: date,
    paid_map: Dict[str, Decimal] | None = None,
    credit_map: Dict[str, Decimal] | None = None,
) -> InvoicePaymentStatusRow:
    term_days = get_settings().default_payment_term_days
    due_date = invoice.invoice_date + timedelta(days=term_days)
    inv_amt = Decimal(invoice.grand_total).quantize(AMT_PREC)

    paid = (
        paid_map.get(invoice.id, Decimal("0.00"))
        if paid_map is not None
        else _invoice_paid_map(db, [invoice.id]).get(invoice.id, Decimal("0.00"))
    )
    credited = (
        credit_map.get(invoice.id, Decimal("0.00"))
        if credit_map is not None
        else _invoice_credit_map(db, [invoice.id]).get(invoice.id, Decimal("0.00"))
    )
    outstanding = max(Decimal("0.00"), (inv_amt - paid - credited).quantize(AMT_PREC))

    if outstanding == Decimal("0.00"):
        pay_status = "PAID"
    elif paid > Decimal("0.00") or credited > Decimal("0.00"):
        pay_status = "PARTIAL"
    else:
        pay_status = "UNPAID"

    days_over = max(0, (as_of - due_date).days) if outstanding > Decimal("0.00") else 0
    bucket = _classify_ageing(days_over) if outstanding > Decimal("0.00") else "Current / Not Due"

    return InvoicePaymentStatusRow(
        invoice_id=invoice.id,
        invoice_number=invoice.invoice_number,
        customer_id=invoice.customer_id,
        customer_name=invoice.customer_name,
        invoice_date=invoice.invoice_date,
        due_date=due_date,
        invoice_amount=inv_amt,
        paid_amount=paid,
        credit_note_amount=credited,
        outstanding_amount=outstanding,
        payment_status=pay_status,
        days_overdue=days_over,
        ageing_category=bucket,
    )


def to_allocation_out(alloc: PaymentAllocation) -> PaymentAllocationOut:
    return PaymentAllocationOut(
        id=alloc.id,
        payment_id=alloc.payment_id,
        payment_reference=alloc.payment.payment_reference,
        invoice_id=alloc.invoice_id,
        invoice_number=alloc.invoice.invoice_number,
        allocated_amount=Decimal(alloc.allocated_amount),
        allocation_date=alloc.allocation_date,
        notes=alloc.notes,
        allocated_by_email=alloc.allocator.email,
        created_at=alloc.created_at,
    )


def to_payment_out(p: Payment) -> PaymentOut:
    return PaymentOut(
        id=p.id,
        payment_reference=p.payment_reference,
        customer_id=p.customer_id,
        customer_name=p.customer.name,
        payment_date=p.payment_date,
        payment_method=p.payment_method,
        amount_received=Decimal(p.amount_received),
        allocated_amount=Decimal(p.allocated_amount),
        unallocated_advance=Decimal(p.unallocated_advance),
        transaction_reference=p.transaction_reference,
        notes=p.notes,
        status=p.status,
        recorded_by_email=p.recorder.email,
        created_at=p.created_at,
        allocations=[to_allocation_out(a) for a in p.allocations],
    )


def _next_payment_reference(db: Session, pay_date: date) -> str:
    prefix = f"PAY-{pay_date.year}-"
    existing = db.scalars(
        select(Payment.payment_reference).where(Payment.payment_reference.like(f"{prefix}%"))
    ).all()
    max_seq = 0
    for code in existing:
        tail = code.replace(prefix, "", 1)
        if tail.isdigit():
            max_seq = max(max_seq, int(tail))
    return f"{prefix}{max_seq + 1:04d}"


def list_payments(
    db: Session,
    *,
    search: str | None = None,
    customer_id: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[Payment], int]:
    filters = []
    if search:
        term = f"%{search.strip()}%"
        filters.append(
            or_(
                Payment.payment_reference.ilike(term),
                Payment.transaction_reference.ilike(term),
                Payment.customer.has(Customer.name.ilike(term)),
            )
        )
    if customer_id:
        filters.append(Payment.customer_id == customer_id)

    total = int(db.scalar(select(func.count(Payment.id)).where(*filters)) or 0)
    stmt = (
        select(Payment)
        .where(*filters)
        .order_by(Payment.payment_date.desc(), Payment.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(db.scalars(stmt).unique().all()), total


def get_payment_or_404(db: Session, payment_id: str) -> Payment:
    p = db.get(Payment, payment_id)
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment record not found.")
    return p


def _apply_allocations(
    db: Session,
    *,
    payment: Payment,
    alloc_inputs,
    alloc_date: date,
    actor: User,
) -> None:
    """Validate and apply payment allocations inside the caller's transaction."""
    existing_by_inv = {a.invoice_id: a for a in payment.allocations}
    total_new = sum((Decimal(row.amount).quantize(AMT_PREC) for row in alloc_inputs), Decimal("0.00"))
    remaining_advance = Decimal(payment.unallocated_advance).quantize(AMT_PREC)

    if total_new > remaining_advance:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Allocation total ({total_new}) exceeds available payment balance ({remaining_advance}).",
        )

    for row in alloc_inputs:
        amt = Decimal(row.amount).quantize(AMT_PREC, rounding=ROUND_HALF_UP)
        if row.invoice_id in existing_by_inv:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This payment is already allocated to the specified invoice.",
            )
        inv = db.scalar(select(Invoice).where(Invoice.id == row.invoice_id).with_for_update())
        if not inv:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found.")
        if inv.customer_id != payment.customer_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invoice belongs to a different customer.",
            )

        status_row = build_invoice_payment_row(db, inv, as_of=alloc_date)
        if amt > status_row.outstanding_amount:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Allocation ({amt}) exceeds outstanding balance ({status_row.outstanding_amount}) "
                    f"for invoice {inv.invoice_number}."
                ),
            )

        alloc = PaymentAllocation(
            payment_id=payment.id,
            invoice_id=inv.id,
            allocated_amount=amt,
            allocation_date=alloc_date,
            notes=row.notes.strip() if row.notes else None,
            allocated_by=actor.id,
        )
        db.add(alloc)
        existing_by_inv[inv.id] = alloc

    payment.allocated_amount = (Decimal(payment.allocated_amount) + total_new).quantize(AMT_PREC)
    payment.unallocated_advance = (
        Decimal(payment.amount_received) - Decimal(payment.allocated_amount)
    ).quantize(AMT_PREC)


def create_payment(
    db: Session,
    payload: PaymentCreate,
    *,
    actor: User,
    ip_address: str | None = None,
) -> Payment:
    customer = db.get(Customer, payload.customer_id)
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found.")

    pay_date = payload.payment_date or date.today()
    pay_ref = (
        payload.payment_reference.strip().upper()
        if payload.payment_reference
        else _next_payment_reference(db, pay_date)
    )
    if db.scalar(select(Payment).where(func.upper(Payment.payment_reference) == pay_ref)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Payment reference '{pay_ref}' already exists.",
        )

    tx_ref = payload.transaction_reference.strip() if payload.transaction_reference else None
    if tx_ref:
        dup_tx = db.scalar(
            select(Payment).where(
                Payment.customer_id == customer.id,
                Payment.payment_method == payload.payment_method,
                func.lower(Payment.transaction_reference) == tx_ref.lower(),
                Payment.status == CustomerPaymentStatus.POSTED,
            )
        )
        if dup_tx:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Duplicate payment transaction reference '{tx_ref}' for {customer.name}.",
            )

    amt_recv = Decimal(payload.amount_received).quantize(AMT_PREC, rounding=ROUND_HALF_UP)

    try:
        payment = Payment(
            payment_reference=pay_ref,
            customer_id=customer.id,
            payment_date=pay_date,
            payment_method=payload.payment_method,
            amount_received=amt_recv,
            allocated_amount=Decimal("0.00"),
            unallocated_advance=amt_recv,
            transaction_reference=tx_ref,
            notes=payload.notes.strip() if payload.notes else None,
            status=CustomerPaymentStatus.POSTED,
            recorded_by=actor.id,
        )
        db.add(payment)
        db.flush()

        if payload.allocations:
            _apply_allocations(
                db,
                payment=payment,
                alloc_inputs=payload.allocations,
                alloc_date=pay_date,
                actor=actor,
            )

        record_audit_event(
            db,
            actor_id=actor.id,
            actor_email=actor.email,
            actor_role=actor.role.value,
            action="payment.posted",
            resource_type="payment",
            resource_id=payment.id,
            details=f"{payment.payment_reference} {customer.name} INR {payment.amount_received} (allocated={payment.allocated_amount})",
            ip_address=ip_address,
            commit=False,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(payment)
    return payment


def allocate_payment(
    db: Session,
    payment_id: str,
    payload: PaymentAllocateRequest,
    *,
    actor: User,
    ip_address: str | None = None,
) -> Payment:
    payment = db.scalar(select(Payment).where(Payment.id == payment_id).with_for_update())
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found.")
    if payment.status != CustomerPaymentStatus.POSTED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot allocate a {payment.status.value} payment.",
        )

    alloc_date = payload.allocation_date or date.today()
    try:
        _apply_allocations(
            db,
            payment=payment,
            alloc_inputs=payload.allocations,
            alloc_date=alloc_date,
            actor=actor,
        )
        record_audit_event(
            db,
            actor_id=actor.id,
            actor_email=actor.email,
            actor_role=actor.role.value,
            action="payment.allocated",
            resource_type="payment",
            resource_id=payment.id,
            details=f"Allocated {payment.payment_reference} (total allocated={payment.allocated_amount})",
            ip_address=ip_address,
            commit=False,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(payment)
    return payment


def get_invoice_payments_detail(db: Session, invoice_id: str) -> InvoicePaymentsDetailOut:
    inv = db.get(Invoice, invoice_id)
    if not inv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found.")
    row = build_invoice_payment_row(db, inv, as_of=date.today())
    allocs = list(
        db.scalars(
            select(PaymentAllocation)
            .where(PaymentAllocation.invoice_id == inv.id)
            .order_by(PaymentAllocation.allocation_date.asc(), PaymentAllocation.created_at.asc())
        ).all()
    )
    return InvoicePaymentsDetailOut(
        invoice=row,
        allocations=[to_allocation_out(a) for a in allocs],
    )


def build_receivables_report(
    db: Session,
    *,
    customer_id: str | None = None,
    as_of: date | None = None,
) -> ReceivablesReportOut:
    ref_date = as_of or date.today()
    inv_stmt = select(Invoice).order_by(Invoice.invoice_date.desc(), Invoice.sequence_number.desc())
    if customer_id:
        inv_stmt = inv_stmt.where(Invoice.customer_id == customer_id)
    invoices = list(db.scalars(inv_stmt).unique().all())

    inv_ids = [i.id for i in invoices]
    paid_map = _invoice_paid_map(db, inv_ids)
    credit_map = _invoice_credit_map(db, inv_ids)
    inv_rows = [
        build_invoice_payment_row(db, i, as_of=ref_date, paid_map=paid_map, credit_map=credit_map)
        for i in invoices
    ]

    pay_stmt = select(Payment).where(Payment.status == CustomerPaymentStatus.POSTED)
    if customer_id:
        pay_stmt = pay_stmt.where(Payment.customer_id == customer_id)
    payments = list(db.scalars(pay_stmt).unique().all())

    adv_by_cust: Dict[str, Decimal] = {}
    for p in payments:
        adv_by_cust[p.customer_id] = (
            adv_by_cust.get(p.customer_id, Decimal("0.00")) + Decimal(p.unallocated_advance)
        ).quantize(AMT_PREC)

    cust_map: Dict[str, CustomerReceivableSummary] = {}
    for r in inv_rows:
        entry = cust_map.get(r.customer_id)
        if entry is None:
            cust_obj = db.get(Customer, r.customer_id)
            adv = adv_by_cust.get(r.customer_id, Decimal("0.00"))
            cust_map[r.customer_id] = CustomerReceivableSummary(
                customer_id=r.customer_id,
                customer_name=r.customer_name,
                customer_state=cust_obj.state if cust_obj else "",
                invoices_count=1,
                total_invoiced=r.invoice_amount,
                total_paid=r.paid_amount,
                unallocated_advance=adv,
                total_outstanding=r.outstanding_amount,
                net_receivable=(r.outstanding_amount - adv).quantize(AMT_PREC),
            )
        else:
            entry.invoices_count += 1
            entry.total_invoiced = (entry.total_invoiced + r.invoice_amount).quantize(AMT_PREC)
            entry.total_paid = (entry.total_paid + r.paid_amount).quantize(AMT_PREC)
            entry.total_outstanding = (entry.total_outstanding + r.outstanding_amount).quantize(AMT_PREC)
            entry.net_receivable = (entry.total_outstanding - entry.unallocated_advance).quantize(AMT_PREC)

    tot_inv = sum((r.invoice_amount for r in inv_rows), Decimal("0.00")).quantize(AMT_PREC)
    tot_col = sum((Decimal(p.amount_received) for p in payments), Decimal("0.00")).quantize(AMT_PREC)
    tot_adv = sum(adv_by_cust.values(), Decimal("0.00")).quantize(AMT_PREC)
    tot_out = sum((r.outstanding_amount for r in inv_rows), Decimal("0.00")).quantize(AMT_PREC)

    return ReceivablesReportOut(
        total_invoiced=tot_inv,
        total_collected=tot_col,
        total_unallocated_advances=tot_adv,
        total_outstanding=tot_out,
        default_payment_term_days=get_settings().default_payment_term_days,
        customers=sorted(cust_map.values(), key=lambda c: c.total_outstanding, reverse=True),
        invoices=inv_rows,
    )


def build_receivables_ageing_report(
    db: Session,
    *,
    as_of: date | None = None,
    customer_id: str | None = None,
) -> ReceivablesAgeingReportOut:
    ref_date = as_of or date.today()
    rec = build_receivables_report(db, customer_id=customer_id, as_of=ref_date)
    open_rows = [r for r in rec.invoices if r.outstanding_amount > Decimal("0.00")]

    bucket_totals: Dict[str, Tuple[int, Decimal]] = {b: (0, Decimal("0.00")) for b in AGEING_BUCKETS}
    for r in open_rows:
        cnt, val = bucket_totals[r.ageing_category]
        bucket_totals[r.ageing_category] = (cnt + 1, (val + r.outstanding_amount).quantize(AMT_PREC))

    return ReceivablesAgeingReportOut(
        as_of_date=ref_date,
        default_payment_term_days=get_settings().default_payment_term_days,
        total_outstanding=rec.total_outstanding,
        buckets=[
            AgeingBucketSummary(category=b, invoices_count=cnt, outstanding_amount=val)
            for b, (cnt, val) in bucket_totals.items()
        ],
        rows=open_rows,
    )


def _chronological_customer_entries(
    db: Session, customer_id: str
) -> Tuple[Customer, List[CustomerLedgerEntryOut], Decimal, Decimal, Decimal, Decimal]:
    customer = db.get(Customer, customer_id)
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found.")

    invoices = list(
        db.scalars(
            select(Invoice)
            .where(Invoice.customer_id == customer.id)
            .order_by(Invoice.invoice_date.asc(), Invoice.created_at.asc())
        ).unique().all()
    )
    payments = list(
        db.scalars(
            select(Payment)
            .where(Payment.customer_id == customer.id, Payment.status == CustomerPaymentStatus.POSTED)
            .order_by(Payment.payment_date.asc(), Payment.created_at.asc())
        ).unique().all()
    )

    events = []
    for inv in invoices:
        events.append((inv.invoice_date, inv.created_at, "INVOICE", inv.invoice_number, f"GST Invoice ({inv.sales_order.order_number})", Decimal(inv.grand_total), Decimal("0.00")))
        for cn in inv.credit_notes:
            events.append((cn.credit_date, cn.created_at, "CREDIT_NOTE", cn.credit_note_number, f"Credit Note against {inv.invoice_number}: {cn.reason}", Decimal("0.00"), Decimal(cn.amount)))
    for pay in payments:
        events.append((pay.payment_date, pay.created_at, "PAYMENT", pay.payment_reference, f"{pay.payment_method.value} receipt", Decimal("0.00"), Decimal(pay.amount_received)))

    events.sort(key=lambda x: (x[0], x[1]))

    running = Decimal("0.00")
    entries: List[CustomerLedgerEntryOut] = []
    for dt, _, doc_type, ref, desc, deb, cred in events:
        running = (running + deb - cred).quantize(AMT_PREC)
        entries.append(
            CustomerLedgerEntryOut(
                entry_date=dt,
                doc_type=doc_type,
                reference_number=ref,
                description=desc,
                debit_amount=deb.quantize(AMT_PREC),
                credit_amount=cred.quantize(AMT_PREC),
                running_balance=running,
            )
        )

    tot_inv = sum((Decimal(i.grand_total) for i in invoices), Decimal("0.00")).quantize(AMT_PREC)
    tot_paid = sum((Decimal(p.amount_received) for p in payments), Decimal("0.00")).quantize(AMT_PREC)
    unalloc = sum((Decimal(p.unallocated_advance) for p in payments), Decimal("0.00")).quantize(AMT_PREC)
    return customer, entries, tot_inv, tot_paid, unalloc, running


def build_customer_ledger(db: Session, customer_id: str) -> CustomerLedgerOut:
    customer, entries, tot_inv, tot_paid, unalloc, closing = _chronological_customer_entries(
        db, customer_id
    )
    return CustomerLedgerOut(
        customer_id=customer.id,
        customer_name=customer.name,
        customer_gstin=customer.gstin,
        customer_state=customer.state,
        total_invoiced=tot_inv,
        total_paid=tot_paid,
        unallocated_advance=unalloc,
        closing_outstanding=closing,
        entries=entries,
    )


def build_customer_statement(
    db: Session,
    customer_id: str,
    *,
    from_date: date | None = None,
    to_date: date | None = None,
) -> CustomerStatementOut:
    customer, all_entries, _, _, unalloc, _ = _chronological_customer_entries(db, customer_id)

    opening = Decimal("0.00")
    period_entries: List[CustomerLedgerEntryOut] = []
    for e in all_entries:
        if from_date and e.entry_date < from_date:
            opening = e.running_balance
            continue
        if to_date and e.entry_date > to_date:
            continue
        period_entries.append(e)

    debits = sum((e.debit_amount for e in period_entries), Decimal("0.00")).quantize(AMT_PREC)
    credits = sum((e.credit_amount for e in period_entries), Decimal("0.00")).quantize(AMT_PREC)
    closing = (opening + debits - credits).quantize(AMT_PREC)
    rec = build_receivables_report(db, customer_id=customer_id, as_of=to_date or date.today())

    return CustomerStatementOut(
        customer_id=customer.id,
        customer_name=customer.name,
        customer_gstin=customer.gstin,
        billing_address=f"{customer.address}, {customer.city}, {customer.state}",
        from_date=from_date,
        to_date=to_date,
        opening_balance=opening,
        period_debits=debits,
        period_credits=credits,
        closing_balance=closing,
        unallocated_advance=unalloc,
        invoices=rec.invoices,
        entries=period_entries,
    )
