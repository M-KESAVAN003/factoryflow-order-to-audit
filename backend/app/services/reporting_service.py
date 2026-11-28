from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.costing_payment import CustomerPaymentStatus, ExpenseStatus, Payment, ProductionExpense
from app.models.customer import Customer
from app.models.inventory import MovementType, StockBalance, StockLedger
from app.models.stock_item import StockItem, StockItemType
from app.models.product import Product
from app.models.production import ProductionRun, ProductionStatus
from app.models.purchase import Purchase, PurchaseStatus
from app.models.sales import CreditNote, Dispatch, Invoice, SalesOrder, SalesOrderStatus, TaxType
from app.schemas.reports import (
    CustomerSalesReportOut,
    CustomerSalesReportRow,
    DateRangeMeta,
    GstHsnSummaryReportOut,
    GstOutwardSupplyReportOut,
    GstRateSummaryRow,
    GstSupplyTypeSummary,
    HsnSummaryRow,
    PaymentRegisterReportOut,
    PaymentRegisterRow,
    ProductSalesReportOut,
    ProductSalesReportRow,
    ProductionCostReportOut,
    ProductionRegisterReportOut,
    ProductionRegisterRow,
    ProductionVarianceMaterialLine,
    ProductionVarianceReportOut,
    ProductionYieldRow,
    PurchaseRegisterReportOut,
    PurchaseRegisterRow,
    ReceivablesAgeingAuditOut,
    ReceivablesReportSummaryOut,
    SalesRegisterReportOut,
    SalesRegisterRow,
    SalesmanPerformanceReportOut,
    SalesmanPerformanceRow,
    StockLedgerReportOut,
    StockLedgerReportRow,
    StockSummaryReportOut,
    StockSummaryReportRow,
)
from app.services.costing_service import build_run_costing
from app.services.ledger_service import reconcile_stock_balances
from app.services.payment_service import (
    _invoice_credit_map,
    _invoice_paid_map,
    build_invoice_payment_row,
    build_receivables_ageing_report,
    build_receivables_report,
)
from app.services.production_service import classify_variance

AMT_PREC = Decimal("0.01")
QTY_PREC = Decimal("0.000001")

GST_DISCLAIMER = (
    "Indicative internal GST outward supply summary only — not an official GST portal "
    "filing. Validate all figures with a qualified tax practitioner before GSTR-1/GSTR-3B submission."
)


def report_sales_register(
    db: Session,
    *,
    dr: DateRangeMeta,
    customer_id: str | None = None,
    product_id: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> SalesRegisterReportOut:
    invoices = [
        inv
        for inv in db.scalars(
            select(Invoice).order_by(Invoice.invoice_date.desc(), Invoice.sequence_number.desc())
        )
        .unique()
        .all()
        if dr.date_from <= inv.invoice_date <= dr.date_to
        and (not customer_id or inv.customer_id == customer_id)
    ]

    inv_ids = [i.id for i in invoices]
    paid_map = _invoice_paid_map(db, inv_ids)
    credit_map = _invoice_credit_map(db, inv_ids)

    all_rows: List[SalesRegisterRow] = []
    for inv in invoices:
        pay_row = build_invoice_payment_row(
            db, inv, as_of=dr.date_to, paid_map=paid_map, credit_map=credit_map
        )
        for it in inv.items:
            if product_id and it.product_id != product_id:
                continue
            all_rows.append(
                SalesRegisterRow(
                    invoice_id=inv.id,
                    invoice_number=inv.invoice_number,
                    invoice_date=inv.invoice_date,
                    customer_name=inv.customer_name,
                    customer_gstin=inv.customer_gstin,
                    state=inv.customer_state,
                    product_name=it.product_name,
                    hsn_code=it.hsn_code,
                    quantity=Decimal(it.quantity),
                    taxable_value=Decimal(it.taxable_value),
                    cgst=Decimal(it.cgst_amount),
                    sgst=Decimal(it.sgst_amount),
                    igst=Decimal(it.igst_amount),
                    invoice_total=Decimal(it.line_total),
                    payment_status=pay_row.payment_status,
                )
            )

    tot_taxable = sum((r.taxable_value for r in all_rows), Decimal("0.00")).quantize(AMT_PREC)
    tot_cgst = sum((r.cgst for r in all_rows), Decimal("0.00")).quantize(AMT_PREC)
    tot_sgst = sum((r.sgst for r in all_rows), Decimal("0.00")).quantize(AMT_PREC)
    tot_igst = sum((r.igst for r in all_rows), Decimal("0.00")).quantize(AMT_PREC)
    tot_val = sum((r.invoice_total for r in all_rows), Decimal("0.00")).quantize(AMT_PREC)

    cn_total = sum(
        (Decimal(cn.amount) for inv in invoices for cn in inv.credit_notes), Decimal("0.00")
    ).quantize(AMT_PREC)

    all_orders = [
        o
        for o in db.scalars(select(SalesOrder)).unique().all()
        if dr.date_from <= o.order_date <= dr.date_to
    ]
    draft_cnt = sum(
        1
        for o in all_orders
        if o.status in {SalesOrderStatus.SUBMITTED, SalesOrderStatus.UNDER_REVIEW, SalesOrderStatus.AWAITING_STOCK}
    )
    rej_cnt = sum(
        1 for o in all_orders if o.status in {SalesOrderStatus.REJECTED, SalesOrderStatus.CANCELLED}
    )

    # Reconcile invoice line items <-> invoice headers, dispatches <-> stock ledger, and report totals
    lines_reconciled = True
    for inv in invoices:
        item_sub = sum((Decimal(it.taxable_value) for it in inv.items), Decimal("0.00")).quantize(AMT_PREC)
        item_tot = sum((Decimal(it.line_total) for it in inv.items), Decimal("0.00")).quantize(AMT_PREC)
        if item_sub != Decimal(inv.subtotal).quantize(AMT_PREC) or item_tot != Decimal(inv.grand_total).quantize(AMT_PREC):
            lines_reconciled = False
            break
        if inv.dispatch is not None:
            dispatch_rows = list(
                db.scalars(
                    select(StockLedger).where(
                        StockLedger.reference_doc_type == "DISPATCH",
                        StockLedger.reference_doc_id == inv.dispatch.dispatch_number,
                        StockLedger.movement_type == MovementType.SALES_DISPATCH,
                    )
                ).all()
            )
            disp_qty = sum((Decimal(di.quantity) for di in inv.dispatch.items), Decimal("0.000000")).quantize(QTY_PREC)
            led_qty = sum((Decimal(le.quantity_out) for le in dispatch_rows), Decimal("0.000000")).quantize(QTY_PREC)
            if disp_qty != led_qty:
                lines_reconciled = False
                break

    expected_filtered_sum = sum(
        (
            Decimal(it.line_total)
            for inv in invoices
            for it in inv.items
            if not product_id or it.product_id == product_id
        ),
        Decimal("0.00"),
    ).quantize(AMT_PREC)
    source_sum = sum((Decimal(i.grand_total) for i in invoices), Decimal("0.00")).quantize(AMT_PREC)
    totals_match = (tot_val == source_sum) if not product_id else (tot_val == expected_filtered_sum)
    reconciled = lines_reconciled and totals_match

    offset = (page - 1) * page_size
    return SalesRegisterReportOut(
        date_range=dr,
        total=len(all_rows),
        page=page,
        page_size=page_size,
        rows=all_rows[offset : offset + page_size],
        total_taxable=tot_taxable,
        total_cgst=tot_cgst,
        total_sgst=tot_sgst,
        total_igst=tot_igst,
        total_invoice_value=tot_val,
        credit_notes_total=cn_total,
        draft_orders_count=draft_cnt,
        rejected_or_cancelled_orders_count=rej_cnt,
        reconciled_with_invoices=reconciled,
    )


def report_sales_by_customer(
    db: Session, *, dr: DateRangeMeta, customer_id: str | None = None
) -> CustomerSalesReportOut:
    orders = [
        o
        for o in db.scalars(select(SalesOrder)).unique().all()
        if dr.date_from <= o.order_date <= dr.date_to
        and o.status not in {SalesOrderStatus.REJECTED, SalesOrderStatus.CANCELLED}
        and (not customer_id or o.customer_id == customer_id)
    ]
    invoices = [
        inv
        for inv in db.scalars(select(Invoice)).unique().all()
        if dr.date_from <= inv.invoice_date <= dr.date_to
        and (not customer_id or inv.customer_id == customer_id)
    ]
    inv_ids = [i.id for i in invoices]
    paid_map = _invoice_paid_map(db, inv_ids)
    credit_map = _invoice_credit_map(db, inv_ids)

    by_cust: Dict[str, CustomerSalesReportRow] = {}
    for o in orders:
        c = o.customer
        if c.id not in by_cust:
            by_cust[c.id] = CustomerSalesReportRow(
                customer_id=c.id,
                customer_name=c.name,
                customer_gstin=c.gstin,
                state=c.state,
                total_orders=0,
                total_invoices=0,
                total_taxable_sales=Decimal("0.00"),
                total_gst=Decimal("0.00"),
                total_invoice_value=Decimal("0.00"),
                amount_collected=Decimal("0.00"),
                outstanding_amount=Decimal("0.00"),
            )
        by_cust[c.id].total_orders += 1

    for inv in invoices:
        pay_row = build_invoice_payment_row(
            db, inv, as_of=dr.date_to, paid_map=paid_map, credit_map=credit_map
        )
        if inv.customer_id not in by_cust:
            by_cust[inv.customer_id] = CustomerSalesReportRow(
                customer_id=inv.customer_id,
                customer_name=inv.customer_name,
                customer_gstin=inv.customer_gstin,
                state=inv.customer_state,
                total_orders=0,
                total_invoices=0,
                total_taxable_sales=Decimal("0.00"),
                total_gst=Decimal("0.00"),
                total_invoice_value=Decimal("0.00"),
                amount_collected=Decimal("0.00"),
                outstanding_amount=Decimal("0.00"),
            )
        r = by_cust[inv.customer_id]
        r.total_invoices += 1
        r.total_taxable_sales = (r.total_taxable_sales + Decimal(inv.subtotal)).quantize(AMT_PREC)
        r.total_gst = (r.total_gst + Decimal(inv.tax_amount)).quantize(AMT_PREC)
        r.total_invoice_value = (r.total_invoice_value + Decimal(inv.grand_total)).quantize(AMT_PREC)
        r.amount_collected = (r.amount_collected + pay_row.paid_amount).quantize(AMT_PREC)
        r.outstanding_amount = (r.outstanding_amount + pay_row.outstanding_amount).quantize(AMT_PREC)

    rows = sorted(by_cust.values(), key=lambda x: x.total_invoice_value, reverse=True)
    return CustomerSalesReportOut(
        date_range=dr,
        rows=rows,
        total_invoice_value=sum((r.total_invoice_value for r in rows), Decimal("0.00")).quantize(AMT_PREC),
        total_collected=sum((r.amount_collected for r in rows), Decimal("0.00")).quantize(AMT_PREC),
        total_outstanding=sum((r.outstanding_amount for r in rows), Decimal("0.00")).quantize(AMT_PREC),
    )


def report_sales_by_product(
    db: Session, *, dr: DateRangeMeta, product_id: str | None = None
) -> ProductSalesReportOut:
    invoices = [
        inv
        for inv in db.scalars(select(Invoice)).unique().all()
        if dr.date_from <= inv.invoice_date <= dr.date_to
    ]
    acc: Dict[str, Dict[str, Any]] = {}
    for inv in invoices:
        for it in inv.items:
            if product_id and it.product_id != product_id:
                continue
            cur = acc.setdefault(
                it.product_id,
                {
                    "product_id": it.product_id,
                    "product_name": it.product_name,
                    "sku": it.sku,
                    "qty": Decimal("0"),
                    "sales_val": Decimal("0.00"),
                    "tax": Decimal("0.00"),
                },
            )
            cur["qty"] += Decimal(it.quantity)
            cur["sales_val"] += Decimal(it.taxable_value)
            cur["tax"] += Decimal(it.cgst_amount) + Decimal(it.sgst_amount) + Decimal(it.igst_amount)

    tot_sales = sum((v["sales_val"] for v in acc.values()), Decimal("0.00")).quantize(AMT_PREC)
    tot_tax = sum((v["tax"] for v in acc.values()), Decimal("0.00")).quantize(AMT_PREC)

    rows: List[ProductSalesReportRow] = []
    for v in acc.values():
        qty = v["qty"]
        val = v["sales_val"].quantize(AMT_PREC)
        avg_sp = (val / qty).quantize(AMT_PREC, rounding=ROUND_HALF_UP) if qty > 0 else Decimal("0.00")
        contrib = (
            ((val / tot_sales) * Decimal("100")).quantize(AMT_PREC, rounding=ROUND_HALF_UP)
            if tot_sales > 0
            else Decimal("0.00")
        )
        rows.append(
            ProductSalesReportRow(
                product_id=v["product_id"],
                product_name=v["product_name"],
                sku=v["sku"],
                total_packets_sold=qty,
                sales_value=val,
                average_selling_price=avg_sp,
                tax_amount=v["tax"].quantize(AMT_PREC),
                revenue_contribution_pct=contrib,
            )
        )
    rows.sort(key=lambda r: r.sales_value, reverse=True)
    return ProductSalesReportOut(
        date_range=dr, rows=rows, total_taxable_sales=tot_sales, total_tax=tot_tax
    )


def report_sales_by_salesman(db: Session, *, dr: DateRangeMeta) -> SalesmanPerformanceReportOut:
    orders = [
        o
        for o in db.scalars(select(SalesOrder)).unique().all()
        if dr.date_from <= o.order_date <= dr.date_to
        and o.status not in {SalesOrderStatus.REJECTED, SalesOrderStatus.CANCELLED}
    ]
    acc: Dict[str, SalesmanPerformanceRow] = {}
    for o in orders:
        u = o.salesman
        row = acc.get(u.id)
        if row is None:
            row = SalesmanPerformanceRow(
                salesman_id=u.id,
                salesman_name=u.full_name,
                salesman_email=u.email,
                orders_count=0,
                approved_orders=0,
                dispatched_orders=0,
                sales_value=Decimal("0.00"),
            )
            acc[u.id] = row
        row.orders_count += 1
        if o.status in {
            SalesOrderStatus.APPROVED,
            SalesOrderStatus.PARTIALLY_FULFILLED,
            SalesOrderStatus.INVOICED,
            SalesOrderStatus.DISPATCHED,
        }:
            row.approved_orders += 1
        if o.status == SalesOrderStatus.DISPATCHED:
            row.dispatched_orders += 1
        if o.invoice is not None:
            row.sales_value = (row.sales_value + Decimal(o.invoice.grand_total)).quantize(AMT_PREC)

    rows = sorted(acc.values(), key=lambda r: r.sales_value, reverse=True)
    return SalesmanPerformanceReportOut(
        date_range=dr,
        rows=rows,
        total_sales_value=sum((r.sales_value for r in rows), Decimal("0.00")).quantize(AMT_PREC),
    )


def report_gst_outward_supplies(
    db: Session, *, dr: DateRangeMeta
) -> GstOutwardSupplyReportOut:
    invoices = [
        inv
        for inv in db.scalars(select(Invoice)).unique().all()
        if dr.date_from <= inv.invoice_date <= dr.date_to
    ]
    tot_taxable = sum((Decimal(i.subtotal) for i in invoices), Decimal("0.00")).quantize(AMT_PREC)
    intra_taxable = sum(
        (Decimal(i.subtotal) for i in invoices if i.tax_type == TaxType.INTRA_STATE), Decimal("0.00")
    ).quantize(AMT_PREC)
    inter_taxable = sum(
        (Decimal(i.subtotal) for i in invoices if i.tax_type == TaxType.INTER_STATE), Decimal("0.00")
    ).quantize(AMT_PREC)
    tot_cgst = sum((Decimal(i.cgst_amount) for i in invoices), Decimal("0.00")).quantize(AMT_PREC)
    tot_sgst = sum((Decimal(i.sgst_amount) for i in invoices), Decimal("0.00")).quantize(AMT_PREC)
    tot_igst = sum((Decimal(i.igst_amount) for i in invoices), Decimal("0.00")).quantize(AMT_PREC)

    cn_total = sum(
        (Decimal(cn.amount) for inv in invoices for cn in inv.credit_notes), Decimal("0.00")
    ).quantize(AMT_PREC)

    by_rate_map: Dict[Decimal, GstRateSummaryRow] = {}
    b2b_stats = [0, Decimal("0.00"), Decimal("0.00"), Decimal("0.00")]
    b2c_stats = [0, Decimal("0.00"), Decimal("0.00"), Decimal("0.00")]

    for inv in invoices:
        target = b2b_stats if (inv.customer_gstin and len(inv.customer_gstin.strip()) == 15) else b2c_stats
        target[0] += 1
        target[1] += Decimal(inv.subtotal)
        target[2] += Decimal(inv.tax_amount)
        target[3] += Decimal(inv.grand_total)
        for it in inv.items:
            rate = Decimal(it.gst_rate).quantize(AMT_PREC)
            r = by_rate_map.get(rate)
            line_tax = Decimal(it.cgst_amount) + Decimal(it.sgst_amount) + Decimal(it.igst_amount)
            if r is None:
                by_rate_map[rate] = GstRateSummaryRow(
                    gst_rate=rate,
                    taxable_value=Decimal(it.taxable_value),
                    cgst_amount=Decimal(it.cgst_amount),
                    sgst_amount=Decimal(it.sgst_amount),
                    igst_amount=Decimal(it.igst_amount),
                    total_tax=line_tax,
                )
            else:
                r.taxable_value = (r.taxable_value + Decimal(it.taxable_value)).quantize(AMT_PREC)
                r.cgst_amount = (r.cgst_amount + Decimal(it.cgst_amount)).quantize(AMT_PREC)
                r.sgst_amount = (r.sgst_amount + Decimal(it.sgst_amount)).quantize(AMT_PREC)
                r.igst_amount = (r.igst_amount + Decimal(it.igst_amount)).quantize(AMT_PREC)
                r.total_tax = (r.total_tax + line_tax).quantize(AMT_PREC)

    reconciled = (
        tot_taxable == (intra_taxable + inter_taxable).quantize(AMT_PREC)
        and sum((r.taxable_value for r in by_rate_map.values()), Decimal("0.00")).quantize(AMT_PREC) == tot_taxable
    )

    return GstOutwardSupplyReportOut(
        date_range=dr,
        disclaimer=GST_DISCLAIMER,
        gstr1_summary={
            "b2b_invoices": b2b_stats[0],
            "b2c_invoices": b2c_stats[0],
            "taxable_supplies": str(tot_taxable),
            "credit_notes": str(cn_total),
        },
        gstr3b_summary={
            "outward_taxable_supplies": str(tot_taxable),
            "igst_liability": str(tot_igst),
            "cgst_liability": str(tot_cgst),
            "sgst_liability": str(tot_sgst),
            "total_gst_liability": str((tot_cgst + tot_sgst + tot_igst).quantize(AMT_PREC)),
        },
        total_taxable_outward=tot_taxable,
        intra_state_taxable=intra_taxable,
        inter_state_taxable=inter_taxable,
        total_cgst=tot_cgst,
        total_sgst=tot_sgst,
        total_igst=tot_igst,
        credit_note_adjustments=cn_total,
        by_rate=sorted(by_rate_map.values(), key=lambda x: x.gst_rate),
        b2b_b2c_breakdown=[
            GstSupplyTypeSummary(
                supply_bucket="B2B",
                invoices_count=b2b_stats[0],
                taxable_value=b2b_stats[1].quantize(AMT_PREC),
                total_tax=b2b_stats[2].quantize(AMT_PREC),
                invoice_total=b2b_stats[3].quantize(AMT_PREC),
            ),
            GstSupplyTypeSummary(
                supply_bucket="B2C",
                invoices_count=b2c_stats[0],
                taxable_value=b2c_stats[1].quantize(AMT_PREC),
                total_tax=b2c_stats[2].quantize(AMT_PREC),
                invoice_total=b2c_stats[3].quantize(AMT_PREC),
            ),
        ],
        reconciled_with_invoices=reconciled,
    )


def report_gst_hsn_summary(db: Session, *, dr: DateRangeMeta) -> GstHsnSummaryReportOut:
    invoices = [
        inv
        for inv in db.scalars(select(Invoice)).unique().all()
        if dr.date_from <= inv.invoice_date <= dr.date_to
    ]
    hsn_map: Dict[str, HsnSummaryRow] = {}
    for inv in invoices:
        for it in inv.items:
            row = hsn_map.get(it.hsn_code)
            line_tax = Decimal(it.cgst_amount) + Decimal(it.sgst_amount) + Decimal(it.igst_amount)
            if row is None:
                hsn_map[it.hsn_code] = HsnSummaryRow(
                    hsn_code=it.hsn_code,
                    description=it.product_name,
                    uqc=it.unit_symbol.upper(),
                    total_quantity=Decimal(it.quantity),
                    taxable_value=Decimal(it.taxable_value),
                    cgst_amount=Decimal(it.cgst_amount),
                    sgst_amount=Decimal(it.sgst_amount),
                    igst_amount=Decimal(it.igst_amount),
                    total_tax=line_tax.quantize(AMT_PREC),
                    total_value=Decimal(it.line_total),
                )
            else:
                row.total_quantity += Decimal(it.quantity)
                row.taxable_value = (row.taxable_value + Decimal(it.taxable_value)).quantize(AMT_PREC)
                row.cgst_amount = (row.cgst_amount + Decimal(it.cgst_amount)).quantize(AMT_PREC)
                row.sgst_amount = (row.sgst_amount + Decimal(it.sgst_amount)).quantize(AMT_PREC)
                row.igst_amount = (row.igst_amount + Decimal(it.igst_amount)).quantize(AMT_PREC)
                row.total_tax = (row.total_tax + line_tax).quantize(AMT_PREC)
                row.total_value = (row.total_value + Decimal(it.line_total)).quantize(AMT_PREC)

    rows = sorted(hsn_map.values(), key=lambda r: r.hsn_code)
    return GstHsnSummaryReportOut(
        date_range=dr,
        disclaimer=GST_DISCLAIMER,
        rows=rows,
        total_taxable_value=sum((r.taxable_value for r in rows), Decimal("0.00")).quantize(AMT_PREC),
        total_tax=sum((r.total_tax for r in rows), Decimal("0.00")).quantize(AMT_PREC),
    )


def report_purchase_register(
    db: Session,
    *,
    dr: DateRangeMeta,
    supplier_id: str | None = None,
    stock_item_id: str | None = None,
    status_filter: PurchaseStatus | None = None,
    page: int = 1,
    page_size: int = 50,
) -> PurchaseRegisterReportOut:
    purchases = [
        p
        for p in db.scalars(select(Purchase).order_by(Purchase.purchase_date.desc(), Purchase.created_at.desc()))
        .unique()
        .all()
        if dr.date_from <= p.purchase_date <= dr.date_to
        and (not supplier_id or p.supplier_id == supplier_id)
        and (status_filter is None or p.status == status_filter)
    ]

    all_rows: List[PurchaseRegisterRow] = []
    posted_tot = Decimal("0.00")
    draft_tot = Decimal("0.00")
    cancel_tot = Decimal("0.00")

    for p in purchases:
        matching_items = [
            it for it in p.items if not stock_item_id or it.stock_item_id == stock_item_id
        ]
        if not matching_items:
            continue
        matching_line_total = Decimal("0.00")
        for it in matching_items:
            sub = Decimal(it.line_subtotal).quantize(AMT_PREC)
            # Proportionately include header tax_amount only if recorded on purchase header
            if Decimal(p.subtotal) > Decimal("0") and Decimal(p.tax_amount) > Decimal("0"):
                gst = ((Decimal(it.line_subtotal) / Decimal(p.subtotal)) * Decimal(p.tax_amount)).quantize(
                    AMT_PREC, rounding=ROUND_HALF_UP
                )
            else:
                gst = Decimal("0.00")
            line_tot = (sub + gst).quantize(AMT_PREC)
            matching_line_total += line_tot
            all_rows.append(
                PurchaseRegisterRow(
                    purchase_id=p.id,
                    reference_number=p.reference_number,
                    purchase_date=p.purchase_date,
                    supplier_name=p.supplier.name,
                    supplier_gstin=p.supplier.gstin,
                    item_name=it.stock_item.name,
                    quantity=Decimal(it.quantity),
                    unit_symbol=it.unit.symbol,
                    purchase_rate=Decimal(it.unit_rate),
                    taxable_amount=sub,
                    gst_amount=gst,
                    total_purchase_amount=line_tot,
                    status=p.status.value,
                )
            )
        # Unfiltered totals retain full purchase header amounts; stock-item-filtered totals
        # sum only the matching line amounts (including pro-rata header GST) across all rows.
        bucket_amount = Decimal(p.total_amount) if not stock_item_id else matching_line_total
        if p.status == PurchaseStatus.POSTED:
            posted_tot += bucket_amount
        elif p.status == PurchaseStatus.CANCELLED:
            cancel_tot += bucket_amount
        else:
            draft_tot += bucket_amount

    posted_line_tot = sum(
        (r.total_purchase_amount for r in all_rows if r.status == PurchaseStatus.POSTED.value),
        Decimal("0.00"),
    ).quantize(AMT_PREC)
    purchases_reconciled = True
    for p in purchases:
        if p.status != PurchaseStatus.POSTED:
            continue
        if stock_item_id and not any(it.stock_item_id == stock_item_id for it in p.items):
            continue
        item_sub = sum((Decimal(it.line_subtotal) for it in p.items), Decimal("0.00")).quantize(AMT_PREC)
        if item_sub != Decimal(p.subtotal).quantize(AMT_PREC) or (
            (Decimal(p.subtotal) + Decimal(p.tax_amount)).quantize(AMT_PREC)
            != Decimal(p.total_amount).quantize(AMT_PREC)
        ):
            purchases_reconciled = False
            break
        pur_ledger = list(
            db.scalars(
                select(StockLedger).where(
                    StockLedger.reference_doc_type == "PURCHASE",
                    StockLedger.reference_doc_id == p.reference_number,
                    StockLedger.movement_type == MovementType.PURCHASE_RECEIPT,
                )
            ).all()
        )
        expected_base = sum((Decimal(it.base_quantity) for it in p.items), Decimal("0.000000")).quantize(QTY_PREC)
        ledger_in = sum((Decimal(le.quantity_in) for le in pur_ledger), Decimal("0.000000")).quantize(QTY_PREC)
        if expected_base != ledger_in:
            purchases_reconciled = False
            break
        if stock_item_id:
            filtered_expected_base = sum(
                (Decimal(it.base_quantity) for it in p.items if it.stock_item_id == stock_item_id),
                Decimal("0.000000"),
            ).quantize(QTY_PREC)
            filtered_ledger_in = sum(
                (Decimal(le.quantity_in) for le in pur_ledger if le.stock_item_id == stock_item_id),
                Decimal("0.000000"),
            ).quantize(QTY_PREC)
            if filtered_expected_base != filtered_ledger_in:
                purchases_reconciled = False
                break

    if not stock_item_id:
        # Compare independent DB purchase headers (posted_tot) against summed line amounts.
        reconciled = purchases_reconciled and (
            abs(posted_line_tot - posted_tot.quantize(AMT_PREC)) <= Decimal("0.05")
        )
    else:
        # When filtered by stock_item_id, posted_tot is line-derived; rely on independent
        # DB header integrity + StockLedger reconciliation checks without self-comparison.
        reconciled = purchases_reconciled

    offset = (page - 1) * page_size
    return PurchaseRegisterReportOut(
        date_range=dr,
        total=len(all_rows),
        page=page,
        page_size=page_size,
        rows=all_rows[offset : offset + page_size],
        posted_total=posted_tot.quantize(AMT_PREC),
        draft_or_reviewed_total=draft_tot.quantize(AMT_PREC),
        cancelled_total=cancel_tot.quantize(AMT_PREC),
        reconciled_with_purchases=reconciled,
    )


def report_stock_summary(
    db: Session,
    *,
    dr: DateRangeMeta,
    category: StockItemType | None = None,
    as_of_date: date | None = None,
) -> StockSummaryReportOut:
    """Reconstruct historical or current inventory balances directly from StockLedger entries."""
    cutoff = as_of_date or dr.date_to
    cutoff_dt = datetime.combine(cutoff, datetime.max.time(), tzinfo=timezone.utc)
    start_dt = datetime.combine(dr.date_from, datetime.min.time(), tzinfo=timezone.utc)

    item_stmt = select(StockItem).order_by(StockItem.item_type.asc(), StockItem.sku.asc())
    if category is not None:
        item_stmt = item_stmt.where(StockItem.item_type == category)
    items = list(db.scalars(item_stmt).all())

    ledger_rows = list(
        db.scalars(select(StockLedger).order_by(StockLedger.transaction_date.asc(), StockLedger.created_at.asc())).all()
    )

    by_item: Dict[str, List[StockLedger]] = {}
    for le in ledger_rows:
        tx_dt = le.transaction_date
        if tx_dt.tzinfo is None:
            tx_dt = tx_dt.replace(tzinfo=timezone.utc)
        if tx_dt <= cutoff_dt:
            by_item.setdefault(le.stock_item_id, []).append(le)

    rows: List[StockSummaryReportRow] = []
    tot_val = Decimal("0.00")

    for si in items:
        entries = by_item.get(si.id, [])
        opening = Decimal("0.000000")
        receipts = Decimal("0.000000")
        issues = Decimal("0.000000")
        adjustments = Decimal("0.000000")
        closing = Decimal("0.000000")
        last_rate = Decimal("0.000000")
        last_val = Decimal("0.0000")

        for le in entries:
            tx_dt = le.transaction_date
            if tx_dt.tzinfo is None:
                tx_dt = tx_dt.replace(tzinfo=timezone.utc)
            net = Decimal(le.quantity_in) - Decimal(le.quantity_out)
            closing += net
            last_rate = Decimal(le.avg_cost_after)
            last_val = Decimal(le.balance_value_after)

            if tx_dt < start_dt:
                opening += net
            else:
                if le.movement_type in {
                    MovementType.OPENING_STOCK,
                    MovementType.PURCHASE_RECEIPT,
                    MovementType.PRODUCTION_OUTPUT,
                    MovementType.SALES_RETURN,
                }:
                    receipts += Decimal(le.quantity_in)
                elif le.movement_type in {
                    MovementType.PRODUCTION_ISSUE,
                    MovementType.SALES_DISPATCH,
                    MovementType.PURCHASE_RETURN,
                }:
                    issues += Decimal(le.quantity_out)
                else:
                    adjustments += net

        closing_q = closing.quantize(QTY_PREC)
        val_display = last_val.quantize(AMT_PREC, rounding=ROUND_HALF_UP) if closing_q > 0 else Decimal("0.00")
        tot_val += val_display
        reorder = Decimal(si.reorder_level)
        if closing_q <= Decimal("0"):
            st_lbl = "OUT_OF_STOCK"
        elif closing_q <= reorder:
            st_lbl = "LOW_STOCK"
        else:
            st_lbl = "HEALTHY"

        rows.append(
            StockSummaryReportRow(
                stock_item_id=si.id,
                item_name=si.name,
                sku=si.sku,
                category=si.item_type.value,
                opening_stock=opening.quantize(QTY_PREC),
                total_receipts=receipts.quantize(QTY_PREC),
                total_issues=issues.quantize(QTY_PREC),
                adjustments=adjustments.quantize(QTY_PREC),
                closing_stock=closing_q,
                base_unit=si.base_unit.symbol,
                weighted_average_rate=last_rate.quantize(QTY_PREC),
                stock_valuation=val_display,
                reorder_level=reorder,
                stock_status=st_lbl,
            )
        )

    has_entries_after_cutoff = any(
        (
            le.transaction_date
            if le.transaction_date.tzinfo is not None
            else le.transaction_date.replace(tzinfo=timezone.utc)
        )
        > cutoff_dt
        for le in ledger_rows
    )
    balances_by_item = {
        b.stock_item_id: b
        for b in db.scalars(select(StockBalance)).all()
    }
    ledger_balance_ok = reconcile_stock_balances(db).all_reconciled
    rows_arithmetic_ok = all(
        (r.opening_stock + r.total_receipts - r.total_issues + r.adjustments).quantize(QTY_PREC)
        == r.closing_stock
        for r in rows
    )
    val_sum_ok = sum((r.stock_valuation for r in rows), Decimal("0.00")).quantize(AMT_PREC) == tot_val.quantize(
        AMT_PREC
    )
    snapshot_matches_balance = True
    if not has_entries_after_cutoff:
        for r in rows:
            bal = balances_by_item.get(r.stock_item_id)
            bal_qty = Decimal(bal.available_quantity).quantize(QTY_PREC) if bal else Decimal("0.000000")
            bal_val = (
                Decimal(bal.total_value).quantize(AMT_PREC, rounding=ROUND_HALF_UP)
                if bal and bal_qty > Decimal("0")
                else Decimal("0.00")
            )
            if r.closing_stock != bal_qty or abs(r.stock_valuation - bal_val) > Decimal("0.01"):
                snapshot_matches_balance = False
                break

    reconciled = ledger_balance_ok and rows_arithmetic_ok and val_sum_ok and snapshot_matches_balance

    return StockSummaryReportOut(
        date_range=dr,
        as_of_date=cutoff,
        category_filter=category.value if category else "ALL",
        rows=rows,
        total_valuation=tot_val.quantize(AMT_PREC),
        reconciled_with_ledger=reconciled,
    )


def report_stock_ledger(
    db: Session,
    *,
    dr: DateRangeMeta,
    stock_item_id: str | None = None,
    category: StockItemType | None = None,
    movement_type: MovementType | None = None,
    reference_doc_type: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> StockLedgerReportOut:
    start_dt = datetime.combine(dr.date_from, datetime.min.time(), tzinfo=timezone.utc)
    end_dt = datetime.combine(dr.date_to, datetime.max.time(), tzinfo=timezone.utc)

    rows_raw = list(
        db.scalars(
            select(StockLedger).order_by(StockLedger.transaction_date.desc(), StockLedger.created_at.desc())
        ).all()
    )
    filtered: List[StockLedgerReportRow] = []
    tot_in = Decimal("0.000000")
    tot_out = Decimal("0.000000")

    for le in rows_raw:
        tx_dt = le.transaction_date
        if tx_dt.tzinfo is None:
            tx_dt = tx_dt.replace(tzinfo=timezone.utc)
        if not (start_dt <= tx_dt <= end_dt):
            continue
        if stock_item_id and le.stock_item_id != stock_item_id:
            continue
        if category is not None and le.stock_item.item_type != category:
            continue
        if movement_type is not None and le.movement_type != movement_type:
            continue
        if reference_doc_type and le.reference_doc_type.upper() != reference_doc_type.strip().upper():
            continue
        q_in = Decimal(le.quantity_in)
        q_out = Decimal(le.quantity_out)
        tot_in += q_in
        tot_out += q_out
        filtered.append(
            StockLedgerReportRow(
                id=le.id,
                transaction_date=le.transaction_date,
                stock_item_id=le.stock_item_id,
                item_name=le.stock_item.name,
                sku=le.stock_item.sku,
                category=le.stock_item.item_type.value,
                movement_type=le.movement_type.value,
                source_document=le.reference_doc_type,
                source_document_id=le.reference_doc_id,
                quantity_in=q_in,
                quantity_out=q_out,
                running_balance=Decimal(le.balance_qty_after),
                unit_valuation=Decimal(le.unit_cost),
                movement_value=Decimal(le.total_value),
                created_by_email=le.creator.email if le.creator else "system@factoryflow.io",
            )
        )

    offset = (page - 1) * page_size
    return StockLedgerReportOut(
        date_range=dr,
        total=len(filtered),
        page=page,
        page_size=page_size,
        rows=filtered[offset : offset + page_size],
        total_quantity_in=tot_in.quantize(QTY_PREC),
        total_quantity_out=tot_out.quantize(QTY_PREC),
    )


def report_production_register(
    db: Session, *, dr: DateRangeMeta, product_id: str | None = None
) -> ProductionRegisterReportOut:
    runs = [
        r
        for r in db.scalars(
            select(ProductionRun).order_by(ProductionRun.production_date.desc(), ProductionRun.created_at.desc())
        )
        .unique()
        .all()
        if dr.date_from <= r.production_date <= dr.date_to
        and (not product_id or r.product_id == product_id)
    ]
    rows: List[ProductionRegisterRow] = []
    tot_good = Decimal("0")
    tot_cost = Decimal("0.00")

    for r in runs:
        cost = build_run_costing(db, r.id)
        wastage = (
            Decimal(r.scrap_quantity) + Decimal(r.damaged_pouches) + Decimal(r.damaged_packets)
        ).quantize(QTY_PREC)
        if r.status in {ProductionStatus.COMPLETED, ProductionStatus.POSTED}:
            tot_good += Decimal(r.actual_good_output)
            tot_cost += cost.total_production_cost
        rows.append(
            ProductionRegisterRow(
                production_run_id=r.id,
                order_number=r.order_number,
                product_name=r.product.name,
                batch_number=r.batch_number,
                production_date=r.production_date,
                bom_version=r.bom_version_snapshot,
                planned_output=Decimal(r.expected_output),
                actual_good_output=Decimal(r.actual_good_output),
                wastage=wastage,
                supervisor_email=r.supervisor.email,
                total_production_cost=cost.total_production_cost,
                cost_per_packet=cost.cost_per_packet_display,
                status=r.status.value,
            )
        )

    runs_reconciled = (
        sum(
            (r.actual_good_output for r in rows if r.status in {ProductionStatus.COMPLETED.value, ProductionStatus.POSTED.value}),
            Decimal("0"),
        )
        == tot_good
        and sum(
            (r.total_production_cost for r in rows if r.status in {ProductionStatus.COMPLETED.value, ProductionStatus.POSTED.value}),
            Decimal("0.00"),
        ).quantize(AMT_PREC)
        == tot_cost.quantize(AMT_PREC)
    )
    if runs_reconciled:
        for r in runs:
            if r.status != ProductionStatus.POSTED:
                continue
            run_ledger = list(
                db.scalars(
                    select(StockLedger).where(
                        StockLedger.reference_doc_type == "PRODUCTION_RUN",
                        StockLedger.reference_doc_id == r.order_number,
                    )
                ).all()
            )
            issued_by_item: Dict[str, Decimal] = {}
            output_qty = Decimal("0.000000")
            for le in run_ledger:
                if le.movement_type == MovementType.PRODUCTION_ISSUE:
                    issued_by_item[le.stock_item_id] = (
                        issued_by_item.get(le.stock_item_id, Decimal("0.000000"))
                        + Decimal(le.quantity_out)
                    ).quantize(QTY_PREC)
                elif le.movement_type == MovementType.PRODUCTION_OUTPUT:
                    output_qty = (output_qty + Decimal(le.quantity_in)).quantize(QTY_PREC)

            expected_issues: Dict[str, Decimal] = {}
            for mat in r.materials:
                qty = Decimal(mat.total_consumed_base_qty).quantize(QTY_PREC)
                if qty > Decimal("0"):
                    expected_issues[mat.stock_item_id] = (
                        expected_issues.get(mat.stock_item_id, Decimal("0.000000")) + qty
                    ).quantize(QTY_PREC)

            if issued_by_item != expected_issues:
                runs_reconciled = False
                break
            expected_out = Decimal(r.actual_good_output).quantize(QTY_PREC)
            if expected_out > Decimal("0") and output_qty != expected_out:
                runs_reconciled = False
                break

    return ProductionRegisterReportOut(
        date_range=dr,
        rows=rows,
        total_good_output=tot_good,
        total_production_cost=tot_cost.quantize(AMT_PREC),
        reconciled_with_runs=runs_reconciled,
    )


def report_production_variance(
    db: Session, *, dr: DateRangeMeta, product_id: str | None = None
) -> ProductionVarianceReportOut:
    runs = [
        r
        for r in db.scalars(
            select(ProductionRun).order_by(ProductionRun.production_date.desc())
        )
        .unique()
        .all()
        if dr.date_from <= r.production_date <= dr.date_to
        and r.status in {ProductionStatus.COMPLETED, ProductionStatus.POSTED}
        and (not product_id or r.product_id == product_id)
    ]
    y_rows: List[ProductionYieldRow] = []
    m_rows: List[ProductionVarianceMaterialLine] = []
    flagged = 0

    for r in runs:
        tol = Decimal(r.variance_tolerance_pct)
        exp = Decimal(r.expected_output)
        act = Decimal(r.actual_good_output)
        y_pct_abs = ((act / exp) * Decimal("100")).quantize(AMT_PREC, rounding=ROUND_HALF_UP) if exp > 0 else Decimal("0.00")
        y_var, y_stat, y_ex = classify_variance(act, exp, tol)
        if y_ex:
            flagged += 1
        warn = r.outputs[-1].packaging_warning if r.outputs else None
        y_rows.append(
            ProductionYieldRow(
                order_number=r.order_number,
                product_name=r.product.name,
                expected_yield=exp,
                actual_output=act,
                yield_pct=y_pct_abs,
                yield_variance_pct=y_var,
                tolerance_status=y_stat,
                exceeds_tolerance=y_ex,
                damaged_pouches=Decimal(r.damaged_pouches),
                wastage_quantity=Decimal(r.scrap_quantity),
                packaging_warning=warn,
            )
        )
        for m in r.materials:
            p_q = Decimal(m.planned_base_quantity)
            a_q = Decimal(m.total_consumed_base_qty)
            v_pct, v_stat, v_ex = classify_variance(a_q, p_q, tol)
            if v_ex:
                flagged += 1
            m_rows.append(
                ProductionVarianceMaterialLine(
                    order_number=r.order_number,
                    product_name=r.product.name,
                    material_name=m.stock_item.name,
                    unit_symbol=m.stock_item.base_unit.symbol,
                    planned_quantity=p_q,
                    actual_quantity=a_q,
                    difference=(a_q - p_q).quantize(QTY_PREC),
                    variance_pct=v_pct,
                    status=v_stat,
                    exceeds_tolerance=v_ex,
                )
            )

    return ProductionVarianceReportOut(
        date_range=dr, yield_rows=y_rows, material_rows=m_rows, flagged_count=flagged
    )


def report_production_costing(
    db: Session, *, dr: DateRangeMeta, product_id: str | None = None
) -> ProductionCostReportOut:
    runs = [
        r
        for r in db.scalars(select(ProductionRun).order_by(ProductionRun.production_date.desc()))
        .unique()
        .all()
        if dr.date_from <= r.production_date <= dr.date_to
        and (not product_id or r.product_id == product_id)
    ]
    rows = []
    tot_mat = Decimal("0.00")
    tot_pkg = Decimal("0.00")
    tot_exp = Decimal("0.00")
    tot_all = Decimal("0.00")
    cost_reconciled = True
    for r in runs:
        c = build_run_costing(db, r.id)
        tot_mat += c.raw_material_cost
        tot_pkg += c.packaging_cost
        tot_exp += c.total_overhead_cost
        tot_all += c.total_production_cost
        rows.append(c.model_dump(mode="json"))

        db_overhead = sum(
            (
                Decimal(e.amount)
                for e in db.scalars(
                    select(ProductionExpense).where(
                        ProductionExpense.production_run_id == r.id,
                        ProductionExpense.status == ExpenseStatus.POSTED,
                    )
                ).all()
            ),
            Decimal("0.00"),
        ).quantize(AMT_PREC)
        if db_overhead != c.total_overhead_cost.quantize(AMT_PREC):
            cost_reconciled = False
            continue

        if r.status == ProductionStatus.POSTED:
            issue_entries = list(
                db.scalars(
                    select(StockLedger).where(
                        StockLedger.reference_doc_type == "PRODUCTION_RUN",
                        StockLedger.reference_doc_id == r.order_number,
                        StockLedger.movement_type == MovementType.PRODUCTION_ISSUE,
                    )
                ).all()
            )
            issued_ledger_val = sum(
                (Decimal(le.total_value) for le in issue_entries),
                Decimal("0.00"),
            ).quantize(AMT_PREC, rounding=ROUND_HALF_UP)
            issued_by_item: Dict[str, Decimal] = {}
            for le in issue_entries:
                issued_by_item[le.stock_item_id] = (
                    issued_by_item.get(le.stock_item_id, Decimal("0.000000"))
                    + Decimal(le.quantity_out)
                ).quantize(QTY_PREC)
            expected_by_item: Dict[str, Decimal] = {}
            for mat in r.materials:
                q = Decimal(mat.total_consumed_base_qty).quantize(QTY_PREC)
                if q > Decimal("0"):
                    expected_by_item[mat.stock_item_id] = (
                        expected_by_item.get(mat.stock_item_id, Decimal("0.000000")) + q
                    ).quantize(QTY_PREC)

            if (
                issued_ledger_val != (c.raw_material_cost + c.packaging_cost).quantize(AMT_PREC)
                or issued_by_item != expected_by_item
            ):
                cost_reconciled = False

    if (tot_mat + tot_pkg + tot_exp).quantize(AMT_PREC) != tot_all.quantize(AMT_PREC):
        cost_reconciled = False

    return ProductionCostReportOut(
        date_range=dr,
        rows=rows,
        total_material_cost=tot_mat.quantize(AMT_PREC),
        total_packaging_cost=tot_pkg.quantize(AMT_PREC),
        total_expense_cost=tot_exp.quantize(AMT_PREC),
        total_production_cost=tot_all.quantize(AMT_PREC),
        reconciled_with_expenses_and_ledger=cost_reconciled,
    )


def report_payments_register(
    db: Session,
    *,
    dr: DateRangeMeta,
    customer_id: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> PaymentRegisterReportOut:
    payments = [
        p
        for p in db.scalars(select(Payment).order_by(Payment.payment_date.desc(), Payment.created_at.desc()))
        .unique()
        .all()
        if dr.date_from <= p.payment_date <= dr.date_to
        and (not customer_id or p.customer_id == customer_id)
    ]
    all_rows = [
        PaymentRegisterRow(
            payment_id=p.id,
            payment_reference=p.payment_reference,
            customer_name=p.customer.name,
            payment_date=p.payment_date,
            payment_method=p.payment_method.value,
            payment_amount=Decimal(p.amount_received),
            allocated_amount=Decimal(p.allocated_amount),
            unallocated_amount=Decimal(p.unallocated_advance),
            status=p.status.value,
        )
        for p in payments
    ]
    posted = [p for p in payments if p.status == CustomerPaymentStatus.POSTED]
    tot_rec = sum((Decimal(p.amount_received) for p in posted), Decimal("0.00")).quantize(AMT_PREC)
    tot_alloc = sum((Decimal(p.allocated_amount) for p in posted), Decimal("0.00")).quantize(AMT_PREC)
    tot_unalloc = sum((Decimal(p.unallocated_advance) for p in posted), Decimal("0.00")).quantize(AMT_PREC)

    alloc_reconciled = all(
        sum((Decimal(a.allocated_amount) for a in p.allocations), Decimal("0.00")).quantize(AMT_PREC)
        == Decimal(p.allocated_amount).quantize(AMT_PREC)
        and (Decimal(p.allocated_amount) + Decimal(p.unallocated_advance)).quantize(AMT_PREC)
        == Decimal(p.amount_received).quantize(AMT_PREC)
        for p in posted
    )

    offset = (page - 1) * page_size
    return PaymentRegisterReportOut(
        date_range=dr,
        total=len(all_rows),
        page=page,
        page_size=page_size,
        rows=all_rows[offset : offset + page_size],
        total_received=tot_rec,
        total_allocated=tot_alloc,
        total_unallocated=tot_unalloc,
        reconciled_with_payments=(tot_rec == (tot_alloc + tot_unalloc).quantize(AMT_PREC))
        and alloc_reconciled,
    )


def report_receivables_audit(
    db: Session, *, customer_id: str | None = None, as_of_date: date | None = None
) -> ReceivablesReportSummaryOut:
    as_of = as_of_date or date.today()
    rec = build_receivables_report(db, customer_id=customer_id, as_of=as_of)
    return ReceivablesReportSummaryOut(
        as_of_date=as_of,
        rows=rec.invoices,
        customers=[c.model_dump(mode="json") for c in rec.customers],
        total_invoiced=rec.total_invoiced,
        total_paid=sum((r.paid_amount for r in rec.invoices), Decimal("0.00")).quantize(AMT_PREC),
        total_outstanding=rec.total_outstanding,
        reconciled_with_invoices=(
            sum((r.outstanding_amount for r in rec.invoices), Decimal("0.00")).quantize(AMT_PREC)
            == rec.total_outstanding
        ),
    )


def report_receivables_ageing_audit(
    db: Session, *, customer_id: str | None = None, as_of_date: date | None = None
) -> ReceivablesAgeingAuditOut:
    ag = build_receivables_ageing_report(db, customer_id=customer_id, as_of=as_of_date)
    bucket_sum = sum((b.outstanding_amount for b in ag.buckets), Decimal("0.00")).quantize(AMT_PREC)
    return ReceivablesAgeingAuditOut(
        **ag.model_dump(),
        reconciled_with_outstanding=(bucket_sum == ag.total_outstanding),
    )
