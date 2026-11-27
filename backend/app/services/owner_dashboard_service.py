import calendar
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Tuple

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.permissions import Role
from app.models.inventory import MovementType, StockBalance, StockLedger
from app.models.production import ProductionRun, ProductionStatus
from app.models.purchase import Purchase, PurchaseStatus
from app.models.sales import Invoice, SalesOrder, SalesOrderStatus
from app.models.stock_item import StockItemType
from app.models.user import User
from app.schemas.reports import (
    CategoryValuePoint,
    DateRangeMeta,
    DomainDashboardOut,
    OwnerAlertItem,
    OwnerDashboardOut,
    TrendPoint,
)
from app.services.costing_service import build_run_costing
from app.services.payment_service import build_receivables_report
from app.services.production_service import classify_variance

AMT_PREC = Decimal("0.01")


def resolve_date_range(
    *,
    preset: str = "last_30_days",
    date_from: date | None = None,
    date_to: date | None = None,
    month: str | None = None,
    financial_year: str | None = None,
    today: date | None = None,
) -> DateRangeMeta:
    """Resolve date presets, YYYY-MM month, FY YYYY-YY, or custom range cleanly."""
    ref = today or date.today()

    if date_from is not None or date_to is not None:
        start = date_from or ref - timedelta(days=29)
        end = date_to or ref
        if start > end:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="date_from cannot be after date_to.",
            )
        return DateRangeMeta(preset="custom", date_from=start, date_to=end)

    if month:
        try:
            yr, mo = [int(x) for x in month.strip().split("-", 1)]
            last_day = calendar.monthrange(yr, mo)[1]
            return DateRangeMeta(
                preset="month",
                date_from=date(yr, mo, 1),
                date_to=date(yr, mo, last_day),
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid month format; expected YYYY-MM.",
            ) from exc

    if financial_year:
        try:
            start_yr = int(financial_year.strip().split("-", 1)[0])
            return DateRangeMeta(
                preset="financial_year",
                date_from=date(start_yr, 4, 1),
                date_to=date(start_yr + 1, 3, 31),
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid financial_year format; expected YYYY-YY.",
            ) from exc

    p = preset.strip().lower()
    if p == "today":
        return DateRangeMeta(preset=p, date_from=ref, date_to=ref)
    if p == "yesterday":
        y = ref - timedelta(days=1)
        return DateRangeMeta(preset=p, date_from=y, date_to=y)
    if p == "last_7_days":
        return DateRangeMeta(preset=p, date_from=ref - timedelta(days=6), date_to=ref)
    if p == "last_30_days":
        return DateRangeMeta(preset=p, date_from=ref - timedelta(days=29), date_to=ref)
    if p == "current_month":
        return DateRangeMeta(preset=p, date_from=date(ref.year, ref.month, 1), date_to=ref)
    if p == "previous_month":
        first_cur = date(ref.year, ref.month, 1)
        last_prev = first_cur - timedelta(days=1)
        return DateRangeMeta(
            preset=p,
            date_from=date(last_prev.year, last_prev.month, 1),
            date_to=last_prev,
        )
    if p == "financial_year":
        fy_start = ref.year if ref.month >= 4 else ref.year - 1
        return DateRangeMeta(
            preset=p,
            date_from=date(fy_start, 4, 1),
            date_to=date(fy_start + 1, 3, 31),
        )
    if p == "all":
        return DateRangeMeta(preset=p, date_from=date(2000, 1, 1), date_to=ref)
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=f"Unsupported date preset '{preset}'.",
    )


def build_owner_dashboard(
    db: Session,
    *,
    preset: str = "last_30_days",
    date_from: date | None = None,
    date_to: date | None = None,
    month: str | None = None,
    financial_year: str | None = None,
) -> OwnerDashboardOut:
    dr = resolve_date_range(
        preset=preset,
        date_from=date_from,
        date_to=date_to,
        month=month,
        financial_year=financial_year,
    )
    ref_today = date.today()

    # Load actual DB records
    orders = list(db.scalars(select(SalesOrder)).unique().all())
    invoices = list(db.scalars(select(Invoice)).unique().all())
    purchases = list(db.scalars(select(Purchase)).unique().all())
    runs = list(db.scalars(select(ProductionRun)).unique().all())
    balances = list(db.scalars(select(StockBalance)).all())

    todays_orders = sum(
        1
        for o in orders
        if o.order_date == ref_today
        and o.status not in {SalesOrderStatus.REJECTED, SalesOrderStatus.CANCELLED}
    )
    pending_orders_list = [
        o
        for o in orders
        if o.status
        in {SalesOrderStatus.SUBMITTED, SalesOrderStatus.UNDER_REVIEW, SalesOrderStatus.AWAITING_STOCK}
    ]

    in_range_invoices = [
        inv for inv in invoices if dr.date_from <= inv.invoice_date <= dr.date_to
    ]
    todays_sales = sum(
        (Decimal(i.grand_total) for i in invoices if i.invoice_date == ref_today),
        Decimal("0.00"),
    ).quantize(AMT_PREC)
    period_sales = sum(
        (Decimal(i.grand_total) for i in in_range_invoices), Decimal("0.00")
    ).quantize(AMT_PREC)
    period_taxable = sum(
        (Decimal(i.subtotal) for i in in_range_invoices), Decimal("0.00")
    ).quantize(AMT_PREC)
    period_gst = sum(
        (Decimal(i.tax_amount) for i in in_range_invoices), Decimal("0.00")
    ).quantize(AMT_PREC)

    in_range_posted_purchases = [
        p
        for p in purchases
        if p.status == PurchaseStatus.POSTED and dr.date_from <= p.purchase_date <= dr.date_to
    ]
    purchase_value = sum(
        (Decimal(p.total_amount) for p in in_range_posted_purchases), Decimal("0.00")
    ).quantize(AMT_PREC)

    in_range_runs = [
        r
        for r in runs
        if r.status in {ProductionStatus.COMPLETED, ProductionStatus.POSTED}
        and dr.date_from <= r.production_date <= dr.date_to
    ]
    run_costings = [build_run_costing(db, r.id) for r in in_range_runs]
    production_output = sum(
        (Decimal(r.actual_good_output) for r in in_range_runs), Decimal("0")
    )
    total_production_cost = sum(
        (c.total_production_cost for c in run_costings), Decimal("0.00")
    ).quantize(AMT_PREC)
    avg_cpp = (
        (total_production_cost / production_output).quantize(AMT_PREC, rounding=ROUND_HALF_UP)
        if production_output > Decimal("0")
        else Decimal("0.00")
    )
    avg_margin = (
        (
            sum((c.gross_margin_pct for c in run_costings), Decimal("0.00"))
            / Decimal(len(run_costings))
        ).quantize(AMT_PREC, rounding=ROUND_HALF_UP)
        if run_costings
        else Decimal("0.00")
    )

    fg_stock = Decimal("0")
    rm_value = Decimal("0.00")
    alerts: List[OwnerAlertItem] = []

    for b in balances:
        si = b.stock_item
        qty = Decimal(b.available_quantity)
        val = Decimal(b.total_value)
        if si.item_type == StockItemType.FINISHED_GOOD:
            fg_stock += qty
        elif si.item_type == StockItemType.RAW_MATERIAL:
            rm_value += val
        if qty <= Decimal(si.reorder_level):
            if si.item_type == StockItemType.RAW_MATERIAL:
                alerts.append(
                    OwnerAlertItem(
                        severity="HIGH" if qty == 0 else "MEDIUM",
                        category="Low Raw Material Stock",
                        message=f"{si.name} ({si.sku}) at {qty} {si.base_unit.symbol} (reorder {si.reorder_level}).",
                        reference_id=si.id,
                    )
                )
            elif si.item_type == StockItemType.PACKAGING:
                alerts.append(
                    OwnerAlertItem(
                        severity="HIGH" if qty == 0 else "MEDIUM",
                        category="Low Packaging Stock",
                        message=f"{si.name} ({si.sku}) at {qty} {si.base_unit.symbol} (reorder {si.reorder_level}).",
                        reference_id=si.id,
                    )
                )

    rm_value = rm_value.quantize(AMT_PREC)

    # Receivables & Overdue
    rec = build_receivables_report(db, as_of=dr.date_to)
    overdue_rec = sum(
        (r.outstanding_amount for r in rec.invoices if r.days_overdue > 0), Decimal("0.00")
    ).quantize(AMT_PREC)

    for inv_row in rec.invoices:
        if inv_row.days_overdue > 0:
            alerts.append(
                OwnerAlertItem(
                    severity="HIGH",
                    category="Overdue Customer Invoice",
                    message=f"{inv_row.invoice_number} ({inv_row.customer_name}) overdue by {inv_row.days_overdue}d — Rs {inv_row.outstanding_amount:.2f}.",
                    reference_id=inv_row.invoice_id,
                )
            )
        elif inv_row.outstanding_amount > Decimal("0.00"):
            alerts.append(
                OwnerAlertItem(
                    severity="MEDIUM",
                    category="Unpaid Invoice",
                    message=f"{inv_row.invoice_number} ({inv_row.customer_name}) pending Rs {inv_row.outstanding_amount:.2f}.",
                    reference_id=inv_row.invoice_id,
                )
            )

    for o in pending_orders_list:
        alerts.append(
            OwnerAlertItem(
                severity="HIGH" if o.has_stock_shortage else "MEDIUM",
                category="Insufficient Finished Goods" if o.has_stock_shortage else "Pending Order",
                message=f"{o.order_number} ({o.customer.name}) — {o.status.value}"
                + (f": {o.shortage_notes}" if o.shortage_notes else ""),
                reference_id=o.id,
            )
        )

    for r in in_range_runs:
        tol = Decimal(r.variance_tolerance_pct)
        y_pct, _, y_ex = classify_variance(Decimal(r.actual_good_output), Decimal(r.expected_output), tol)
        if y_ex:
            alerts.append(
                OwnerAlertItem(
                    severity="HIGH",
                    category="Production Yield Variance",
                    message=f"{r.order_number} ({r.product.name}) yield variance {y_pct}% exceeds {tol}% tolerance.",
                    reference_id=r.id,
                )
            )
        for m in r.materials:
            if m.variance_pct is not None and abs(Decimal(m.variance_pct)) > tol:
                alerts.append(
                    OwnerAlertItem(
                        severity="MEDIUM",
                        category="Excess Material Consumption",
                        message=f"{r.order_number} {m.stock_item.name} variance {m.variance_pct}% (> {tol}%).",
                        reference_id=r.id,
                    )
                )

    # 10 Live Analytics Charts
    daily_sales_map: Dict[str, Decimal] = {}
    monthly_rev_map: Dict[str, Decimal] = {}
    prod_sales_map: Dict[str, Tuple[Decimal, Decimal]] = {}
    cust_sales_map: Dict[str, Decimal] = {}

    for inv in in_range_invoices:
        d_key = inv.invoice_date.isoformat()
        m_key = inv.invoice_date.strftime("%Y-%m")
        daily_sales_map[d_key] = (daily_sales_map.get(d_key, Decimal("0.00")) + Decimal(inv.grand_total)).quantize(AMT_PREC)
        monthly_rev_map[m_key] = (monthly_rev_map.get(m_key, Decimal("0.00")) + Decimal(inv.subtotal)).quantize(AMT_PREC)
        cust_sales_map[inv.customer_name] = (cust_sales_map.get(inv.customer_name, Decimal("0.00")) + Decimal(inv.grand_total)).quantize(AMT_PREC)
        for it in inv.items:
            val, qty = prod_sales_map.get(it.product_name, (Decimal("0.00"), Decimal("0")))
            prod_sales_map[it.product_name] = (
                (val + Decimal(it.taxable_value)).quantize(AMT_PREC),
                qty + Decimal(it.quantity),
            )

    purch_by_date: Dict[str, Decimal] = {}
    for p in in_range_posted_purchases:
        dk = p.purchase_date.isoformat()
        purch_by_date[dk] = (purch_by_date.get(dk, Decimal("0.00")) + Decimal(p.total_amount)).quantize(AMT_PREC)
    all_ps_dates = sorted(set(daily_sales_map.keys()) | set(purch_by_date.keys()))

    mat_comp_map: Dict[str, Tuple[Decimal, Decimal]] = {}
    wastage_map: Dict[str, Decimal] = {}
    for r in in_range_runs:
        for m in r.materials:
            p_q, a_q = mat_comp_map.get(m.stock_item.name, (Decimal("0"), Decimal("0")))
            mat_comp_map[m.stock_item.name] = (
                p_q + Decimal(m.planned_base_quantity),
                a_q + Decimal(m.total_consumed_base_qty),
            )
        w_sum = Decimal(r.scrap_quantity) + Decimal(r.damaged_pouches) + Decimal(r.damaged_packets)
        wastage_map[r.order_number] = wastage_map.get(r.order_number, Decimal("0")) + w_sum

    rec_by_date: Dict[str, Decimal] = {}
    for row in rec.invoices:
        dk = row.invoice_date.isoformat()
        rec_by_date[dk] = (rec_by_date.get(dk, Decimal("0.00")) + row.outstanding_amount).quantize(AMT_PREC)

    return OwnerDashboardOut(
        date_range=dr,
        todays_orders=todays_orders,
        pending_orders=len(pending_orders_list),
        todays_sales=todays_sales,
        monthly_sales=period_sales,
        monthly_taxable_revenue=period_taxable,
        total_gst_collected=period_gst,
        purchase_value=purchase_value,
        production_output=production_output,
        finished_goods_stock=fg_stock,
        raw_material_stock_value=rm_value,
        total_production_cost=total_production_cost,
        average_cost_per_packet=avg_cpp,
        gross_margin_pct=avg_margin,
        total_customer_receivables=rec.total_outstanding,
        overdue_receivables=overdue_rec,
        daily_sales_trend=[
            TrendPoint(label=k, value=v) for k, v in sorted(daily_sales_map.items())
        ],
        monthly_revenue_trend=[
            TrendPoint(label=k, value=v) for k, v in sorted(monthly_rev_map.items())
        ],
        product_wise_sales=[
            CategoryValuePoint(name=k, value=v[0], quantity=v[1])
            for k, v in sorted(prod_sales_map.items(), key=lambda x: x[1][0], reverse=True)
        ],
        customer_wise_sales=[
            CategoryValuePoint(name=k, value=v)
            for k, v in sorted(cust_sales_map.items(), key=lambda x: x[1], reverse=True)
        ],
        purchase_vs_sales_trend=[
            TrendPoint(
                label=dk,
                value=daily_sales_map.get(dk, Decimal("0.00")),
                secondary_value=purch_by_date.get(dk, Decimal("0.00")),
            )
            for dk in all_ps_dates
        ],
        production_planned_vs_actual=[
            TrendPoint(
                label=r.order_number,
                value=Decimal(r.actual_good_output),
                secondary_value=Decimal(r.expected_output),
            )
            for r in in_range_runs
        ],
        material_consumption_comparison=[
            CategoryValuePoint(name=k, value=v[1], quantity=v[0])
            for k, v in sorted(mat_comp_map.items())
        ],
        production_wastage=[
            CategoryValuePoint(name=k, value=v) for k, v in sorted(wastage_map.items())
        ],
        cost_per_packet_trend=[
            TrendPoint(label=c.order_number, value=c.cost_per_packet_display)
            for c in run_costings
        ],
        outstanding_receivables_trend=[
            TrendPoint(label=k, value=v) for k, v in sorted(rec_by_date.items())
        ],
        alerts=alerts,
    )


def build_domain_dashboard(
    db: Session, *, domain: str, actor: User, dr: DateRangeMeta
) -> DomainDashboardOut:
    """Focused metrics payload for /dashboard/sales, /production, /inventory, /finance."""
    if domain == "sales":
        stmt = select(SalesOrder)
        if actor.role == Role.ORDER_MANAGER:
            stmt = stmt.where(SalesOrder.salesman_id == actor.id)
        orders = [
            o for o in db.scalars(stmt).unique().all() if dr.date_from <= o.order_date <= dr.date_to
        ]
        invoices = [
            i
            for i in db.scalars(select(Invoice)).unique().all()
            if dr.date_from <= i.invoice_date <= dr.date_to
            and (actor.role != Role.ORDER_MANAGER or i.sales_order.salesman_id == actor.id)
        ]
        return DomainDashboardOut(
            domain="sales",
            date_range=dr,
            metrics={
                "orders_count": len(orders),
                "dispatched_count": sum(1 for o in orders if o.status == SalesOrderStatus.DISPATCHED),
                "awaiting_stock_count": sum(1 for o in orders if o.status == SalesOrderStatus.AWAITING_STOCK),
                "invoices_count": len(invoices),
                "taxable_sales": str(sum((Decimal(i.subtotal) for i in invoices), Decimal("0.00")).quantize(AMT_PREC)),
                "gst_collected": str(sum((Decimal(i.tax_amount) for i in invoices), Decimal("0.00")).quantize(AMT_PREC)),
                "invoice_total": str(sum((Decimal(i.grand_total) for i in invoices), Decimal("0.00")).quantize(AMT_PREC)),
            },
        )
    if domain == "production":
        runs = [
            r
            for r in db.scalars(select(ProductionRun)).unique().all()
            if dr.date_from <= r.production_date <= dr.date_to
        ]
        costings = [build_run_costing(db, r.id) for r in runs if r.status in {ProductionStatus.COMPLETED, ProductionStatus.POSTED}]
        return DomainDashboardOut(
            domain="production",
            date_range=dr,
            metrics={
                "runs_count": len(runs),
                "good_output": str(sum((Decimal(r.actual_good_output) for r in runs), Decimal("0"))),
                "total_cost": str(sum((c.total_production_cost for c in costings), Decimal("0.00")).quantize(AMT_PREC)),
            },
        )
    if domain == "inventory":
        bals = list(db.scalars(select(StockBalance)).all())
        ledger_cnt = len(list(db.scalars(select(StockLedger)).all()))
        return DomainDashboardOut(
            domain="inventory",
            date_range=dr,
            metrics={
                "tracked_items": len(bals),
                "total_valuation": str(sum((Decimal(b.total_value) for b in bals), Decimal("0.00")).quantize(AMT_PREC)),
                "low_stock_items": sum(1 for b in bals if Decimal(b.available_quantity) <= Decimal(b.stock_item.reorder_level)),
                "ledger_movements": ledger_cnt,
            },
        )
    rec = build_receivables_report(db, as_of=dr.date_to)
    return DomainDashboardOut(
        domain="finance",
        date_range=dr,
        metrics={
            "total_invoiced": str(rec.total_invoiced),
            "total_collected": str(rec.total_collected),
            "total_outstanding": str(rec.total_outstanding),
            "total_unallocated_advances": str(rec.total_unallocated_advances),
        },
    )
