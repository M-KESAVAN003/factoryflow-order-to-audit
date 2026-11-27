from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.costing_payment import ExpenseCategory, ExpenseStatus, ProductionExpense
from app.models.inventory import MovementType, StockBalance, StockLedger
from app.models.product import Product
from app.models.production import ProductionRun
from app.models.stock_item import StockItemType
from app.models.user import User
from app.schemas.costing_payment import (
    MaterialCostLineOut,
    ProductCostSummaryOut,
    ProductionCostDashboardOut,
    ProductionExpenseCreate,
    ProductionExpenseOut,
    ProductionExpenseUpdate,
    RunCostingOut,
)
from app.services.audit_service import record_audit_event

MONEY_PREC = Decimal("0.01")
RATE_PREC = Decimal("0.000001")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def to_expense_out(exp: ProductionExpense) -> ProductionExpenseOut:
    return ProductionExpenseOut(
        id=exp.id,
        expense_number=exp.expense_number,
        production_run_id=exp.production_run_id,
        order_number=exp.production_run.order_number,
        category=exp.category,
        description=exp.description,
        amount=Decimal(exp.amount),
        expense_date=exp.expense_date,
        status=exp.status,
        reversal_of_id=exp.reversal_of_id,
        recorded_by_email=exp.recorder.email,
        posted_at=exp.posted_at,
        created_at=exp.created_at,
    )


def _next_expense_number(db: Session, exp_date: date) -> str:
    prefix = f"EXP-{exp_date.year}-"
    existing = db.scalars(
        select(ProductionExpense.expense_number).where(
            ProductionExpense.expense_number.like(f"{prefix}%")
        )
    ).all()
    max_seq = 0
    for code in existing:
        tail = code.replace(prefix, "", 1)
        if tail.isdigit():
            max_seq = max(max_seq, int(tail))
    return f"{prefix}{max_seq + 1:04d}"


def list_run_expenses(db: Session, run_id: str) -> List[ProductionExpense]:
    if not db.get(ProductionRun, run_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Production run not found.")
    return list(
        db.scalars(
            select(ProductionExpense)
            .where(ProductionExpense.production_run_id == run_id)
            .order_by(ProductionExpense.expense_date.desc(), ProductionExpense.created_at.desc())
        ).all()
    )


def create_run_expense(
    db: Session,
    run_id: str,
    payload: ProductionExpenseCreate,
    *,
    actor: User,
    ip_address: str | None = None,
) -> ProductionExpense:
    run = db.get(ProductionRun, run_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Production run not found.")

    exp_date = payload.expense_date or date.today()
    exp_number = _next_expense_number(db, exp_date)
    now = _utcnow() if payload.auto_post else None

    exp = ProductionExpense(
        expense_number=exp_number,
        production_run_id=run.id,
        category=payload.category,
        description=payload.description.strip(),
        amount=Decimal(payload.amount).quantize(MONEY_PREC, rounding=ROUND_HALF_UP),
        expense_date=exp_date,
        status=ExpenseStatus.POSTED if payload.auto_post else ExpenseStatus.DRAFT,
        recorded_by=actor.id,
        posted_by=actor.id if payload.auto_post else None,
        posted_at=now,
    )
    db.add(exp)
    db.flush()

    record_audit_event(
        db,
        actor_id=actor.id,
        actor_email=actor.email,
        actor_role=actor.role.value,
        action="production_expense.created",
        resource_type="production_expense",
        resource_id=exp.id,
        details=f"{exp.expense_number} ({exp.category.value}) INR {exp.amount} on {run.order_number} [{exp.status.value}]",
        ip_address=ip_address,
        commit=False,
    )
    db.commit()
    db.refresh(exp)
    return exp


def update_run_expense(
    db: Session,
    run_id: str,
    expense_id: str,
    payload: ProductionExpenseUpdate,
    *,
    actor: User,
    ip_address: str | None = None,
) -> ProductionExpense:
    exp = db.get(ProductionExpense, expense_id)
    if not exp or exp.production_run_id != run_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Production expense not found.")
    if exp.status != ExpenseStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot edit {exp.status.value} expense; post a traceable reversal instead.",
        )

    if payload.category is not None:
        exp.category = payload.category
    if payload.description is not None:
        exp.description = payload.description.strip()
    if payload.amount is not None:
        exp.amount = Decimal(payload.amount).quantize(MONEY_PREC, rounding=ROUND_HALF_UP)
    if payload.expense_date is not None:
        exp.expense_date = payload.expense_date

    record_audit_event(
        db,
        actor_id=actor.id,
        actor_email=actor.email,
        actor_role=actor.role.value,
        action="production_expense.updated",
        resource_type="production_expense",
        resource_id=exp.id,
        details=f"Updated draft {exp.expense_number} INR {exp.amount}",
        ip_address=ip_address,
        commit=False,
    )
    db.commit()
    db.refresh(exp)
    return exp


def post_run_expense(
    db: Session,
    run_id: str,
    expense_id: str,
    *,
    actor: User,
    ip_address: str | None = None,
) -> ProductionExpense:
    exp = db.get(ProductionExpense, expense_id)
    if not exp or exp.production_run_id != run_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Production expense not found.")
    if exp.status != ExpenseStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Expense '{exp.expense_number}' is already {exp.status.value}.",
        )

    exp.status = ExpenseStatus.POSTED
    exp.posted_by = actor.id
    exp.posted_at = _utcnow()

    record_audit_event(
        db,
        actor_id=actor.id,
        actor_email=actor.email,
        actor_role=actor.role.value,
        action="production_expense.posted",
        resource_type="production_expense",
        resource_id=exp.id,
        details=f"Posted {exp.expense_number} ({exp.category.value}) INR {exp.amount}",
        ip_address=ip_address,
        commit=False,
    )
    db.commit()
    db.refresh(exp)
    return exp


def reverse_run_expense(
    db: Session,
    run_id: str,
    expense_id: str,
    *,
    actor: User,
    ip_address: str | None = None,
) -> ProductionExpense:
    """Create a traceable negative reversal entry without deleting or editing the posted expense."""
    exp = db.get(ProductionExpense, expense_id)
    if not exp or exp.production_run_id != run_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Production expense not found.")
    if exp.status != ExpenseStatus.POSTED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only POSTED expenses can be reversed.",
        )

    existing_rev = db.scalar(
        select(ProductionExpense).where(ProductionExpense.reversal_of_id == exp.id)
    )
    if existing_rev:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Expense '{exp.expense_number}' already reversed by '{existing_rev.expense_number}'.",
        )

    rev_num = _next_expense_number(db, date.today())
    reversal = ProductionExpense(
        expense_number=rev_num,
        production_run_id=exp.production_run_id,
        category=exp.category,
        description=f"Reversal of {exp.expense_number}: {exp.description}",
        amount=(-Decimal(exp.amount)).quantize(MONEY_PREC),
        expense_date=date.today(),
        status=ExpenseStatus.POSTED,
        reversal_of_id=exp.id,
        recorded_by=actor.id,
        posted_by=actor.id,
        posted_at=_utcnow(),
    )
    db.add(reversal)
    db.flush()

    record_audit_event(
        db,
        actor_id=actor.id,
        actor_email=actor.email,
        actor_role=actor.role.value,
        action="production_expense.reversed",
        resource_type="production_expense",
        resource_id=reversal.id,
        details=f"{rev_num} reversed {exp.expense_number} INR {exp.amount}",
        ip_address=ip_address,
        commit=False,
    )
    db.commit()
    db.refresh(reversal)
    return reversal


def build_run_costing(db: Session, run_id: str) -> RunCostingOut:
    """Calculate actual raw material, packaging, overhead, cost/packet, and margin for a run."""
    run = db.get(ProductionRun, run_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Production run not found.")

    # Prefer authoritative posted StockLedger PRODUCTION_ISSUE entries for the run
    ledger_rows = list(
        db.scalars(
            select(StockLedger).where(
                StockLedger.reference_doc_type == "PRODUCTION_RUN",
                StockLedger.reference_doc_id == run.order_number,
                StockLedger.movement_type == MovementType.PRODUCTION_ISSUE,
            )
        ).all()
    )
    ledger_by_item: Dict[str, StockLedger] = {le.stock_item_id: le for le in ledger_rows}

    item_ids = [m.stock_item_id for m in run.materials]
    balances = {
        b.stock_item_id: b
        for b in db.scalars(
            select(StockBalance).where(StockBalance.stock_item_id.in_(item_ids))
        ).all()
    } if item_ids else {}

    raw_cost = Decimal("0")
    pkg_cost = Decimal("0")
    mat_lines: List[MaterialCostLineOut] = []

    for m in run.materials:
        consumed = Decimal(m.total_consumed_base_qty)
        if m.stock_item_id in ledger_by_item:
            le = ledger_by_item[m.stock_item_id]
            rate = Decimal(le.unit_cost)
            line_cost = Decimal(le.total_value)
        else:
            bal = balances.get(m.stock_item_id)
            rate = Decimal(bal.average_cost) if bal else Decimal(m.stock_item.purchase_rate)
            line_cost = consumed * rate

        if m.input_category == StockItemType.RAW_MATERIAL:
            raw_cost += line_cost
        else:
            pkg_cost += line_cost

        mat_lines.append(
            MaterialCostLineOut(
                stock_item_id=m.stock_item_id,
                stock_item_name=m.stock_item.name,
                sku=m.stock_item.sku,
                category=m.input_category.value,
                actual_quantity=Decimal(m.actual_quantity),
                damaged_quantity=Decimal(m.damaged_quantity),
                total_consumed_qty=consumed,
                unit_symbol=m.stock_item.base_unit.symbol,
                weighted_avg_rate=rate.quantize(RATE_PREC, rounding=ROUND_HALF_UP),
                total_cost=line_cost.quantize(MONEY_PREC, rounding=ROUND_HALF_UP),
            )
        )

    expenses = list_run_expenses(db, run.id)
    labour = Decimal("0")
    gas_power = Decimal("0")
    other_oh = Decimal("0")
    for e in expenses:
        if e.status != ExpenseStatus.POSTED:
            continue
        amt = Decimal(e.amount)
        if e.category == ExpenseCategory.LABOUR:
            labour += amt
        elif e.category in {ExpenseCategory.GAS, ExpenseCategory.ELECTRICITY, ExpenseCategory.POWER}:
            gas_power += amt
        else:
            other_oh += amt

    raw_cost_q = raw_cost.quantize(MONEY_PREC, rounding=ROUND_HALF_UP)
    pkg_cost_q = pkg_cost.quantize(MONEY_PREC, rounding=ROUND_HALF_UP)
    mat_pkg_total = (raw_cost + pkg_cost).quantize(MONEY_PREC, rounding=ROUND_HALF_UP)
    labour_q = labour.quantize(MONEY_PREC, rounding=ROUND_HALF_UP)
    gas_power_q = gas_power.quantize(MONEY_PREC, rounding=ROUND_HALF_UP)
    other_oh_q = other_oh.quantize(MONEY_PREC, rounding=ROUND_HALF_UP)
    total_oh = (labour + gas_power + other_oh).quantize(MONEY_PREC, rounding=ROUND_HALF_UP)

    total_cost_exact = raw_cost + pkg_cost + labour + gas_power + other_oh
    total_cost_display = total_cost_exact.quantize(MONEY_PREC, rounding=ROUND_HALF_UP)

    good_out = Decimal(run.actual_good_output)
    selling_pre_gst = Decimal(run.product.selling_price).quantize(MONEY_PREC)

    if good_out > Decimal("0"):
        cpp_raw = total_cost_exact / good_out
        cpp_exact = cpp_raw.quantize(RATE_PREC, rounding=ROUND_HALF_UP)
        cpp_display = cpp_raw.quantize(MONEY_PREC, rounding=ROUND_HALF_UP)
        gp_raw = selling_pre_gst - cpp_raw
        gp_display = gp_raw.quantize(MONEY_PREC, rounding=ROUND_HALF_UP)
        margin_pct = (
            ((gp_raw / selling_pre_gst) * Decimal("100")).quantize(MONEY_PREC, rounding=ROUND_HALF_UP)
            if selling_pre_gst > Decimal("0")
            else Decimal("0.00")
        )
    else:
        cpp_exact = Decimal("0.000000")
        cpp_display = Decimal("0.00")
        gp_display = Decimal("0.00")
        margin_pct = Decimal("0.00")

    return RunCostingOut(
        production_run_id=run.id,
        order_number=run.order_number,
        batch_number=run.batch_number,
        product_id=run.product_id,
        product_name=run.product.name,
        product_sku=run.product.sku,
        production_date=run.production_date,
        status=run.status.value,
        actual_good_output=good_out,
        unit_symbol=run.product.unit.symbol,
        raw_material_cost=raw_cost_q,
        packaging_cost=pkg_cost_q,
        material_and_packaging_cost=mat_pkg_total,
        labour_cost=labour_q,
        gas_and_power_cost=gas_power_q,
        other_overhead_cost=other_oh_q,
        total_overhead_cost=total_oh,
        total_production_cost=total_cost_display,
        cost_per_packet_exact=cpp_exact,
        cost_per_packet_display=cpp_display,
        selling_price_before_gst=selling_pre_gst,
        gross_profit_per_packet=gp_display,
        gross_margin_pct=margin_pct,
        materials=mat_lines,
        expenses=[to_expense_out(e) for e in expenses],
    )


def build_costing_dashboard(
    db: Session, *, product_id: str | None = None
) -> ProductionCostDashboardOut:
    stmt = select(ProductionRun).order_by(
        ProductionRun.production_date.desc(), ProductionRun.created_at.desc()
    )
    if product_id:
        stmt = stmt.where(ProductionRun.product_id == product_id)
    runs = list(db.scalars(stmt).unique().all())

    run_costings = [build_run_costing(db, r.id) for r in runs]

    tot_good = sum((c.actual_good_output for c in run_costings), Decimal("0"))
    tot_raw = sum((c.raw_material_cost for c in run_costings), Decimal("0.00")).quantize(MONEY_PREC)
    tot_pkg = sum((c.packaging_cost for c in run_costings), Decimal("0.00")).quantize(MONEY_PREC)
    tot_lab = sum((c.labour_cost for c in run_costings), Decimal("0.00")).quantize(MONEY_PREC)
    tot_gp = sum((c.gas_and_power_cost for c in run_costings), Decimal("0.00")).quantize(MONEY_PREC)
    tot_oth = sum((c.other_overhead_cost for c in run_costings), Decimal("0.00")).quantize(MONEY_PREC)
    tot_cost = sum((c.total_production_cost for c in run_costings), Decimal("0.00")).quantize(MONEY_PREC)

    by_prod: Dict[str, List[RunCostingOut]] = {}
    for c in run_costings:
        by_prod.setdefault(c.product_id, []).append(c)

    product_summaries: List[ProductCostSummaryOut] = []
    for pid, p_runs in by_prod.items():
        first = p_runs[0]
        p_good = sum((r.actual_good_output for r in p_runs), Decimal("0"))
        p_mat = sum((r.material_and_packaging_cost for r in p_runs), Decimal("0.00")).quantize(MONEY_PREC)
        p_exp = sum((r.total_overhead_cost for r in p_runs), Decimal("0.00")).quantize(MONEY_PREC)
        p_tot = sum((r.total_production_cost for r in p_runs), Decimal("0.00")).quantize(MONEY_PREC)
        sell = first.selling_price_before_gst
        if p_good > Decimal("0"):
            avg_cpp = (p_tot / p_good).quantize(MONEY_PREC, rounding=ROUND_HALF_UP)
            gp = (sell - (p_tot / p_good)).quantize(MONEY_PREC, rounding=ROUND_HALF_UP)
            gm = (
                (((sell - (p_tot / p_good)) / sell) * Decimal("100")).quantize(MONEY_PREC, rounding=ROUND_HALF_UP)
                if sell > Decimal("0")
                else Decimal("0.00")
            )
        else:
            avg_cpp = Decimal("0.00")
            gp = Decimal("0.00")
            gm = Decimal("0.00")
        product_summaries.append(
            ProductCostSummaryOut(
                product_id=pid,
                product_name=first.product_name,
                product_sku=first.product_sku,
                runs_count=len(p_runs),
                total_good_output=p_good,
                total_material_cost=p_mat,
                total_expense_cost=p_exp,
                total_production_cost=p_tot,
                avg_cost_per_packet=avg_cpp,
                selling_price_before_gst=sell,
                gross_profit_per_packet=gp,
                gross_margin_pct=gm,
                runs=p_runs,
            )
        )

    avg_cpp_all = (
        (tot_cost / tot_good).quantize(MONEY_PREC, rounding=ROUND_HALF_UP)
        if tot_good > Decimal("0")
        else Decimal("0.00")
    )
    avg_margin_all = (
        (sum((c.gross_margin_pct for c in run_costings), Decimal("0.00")) / Decimal(len(run_costings))).quantize(
            MONEY_PREC, rounding=ROUND_HALF_UP
        )
        if run_costings
        else Decimal("0.00")
    )

    return ProductionCostDashboardOut(
        total_runs_costed=len(run_costings),
        total_good_output=tot_good,
        total_raw_material_cost=tot_raw,
        total_packaging_cost=tot_pkg,
        total_labour_cost=tot_lab,
        total_gas_and_power_cost=tot_gp,
        total_other_overhead_cost=tot_oth,
        total_production_cost=tot_cost,
        avg_cost_per_packet=avg_cpp_all,
        avg_gross_margin_pct=avg_margin_all,
        products=product_summaries,
        runs=run_costings,
    )


def build_product_cost_summary(db: Session, product_id: str) -> ProductCostSummaryOut:
    if not db.get(Product, product_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")
    dash = build_costing_dashboard(db, product_id=product_id)
    if dash.products:
        return dash.products[0]
    prod = db.get(Product, product_id)
    return ProductCostSummaryOut(
        product_id=prod.id,
        product_name=prod.name,
        product_sku=prod.sku,
        runs_count=0,
        total_good_output=Decimal("0"),
        total_material_cost=Decimal("0.00"),
        total_expense_cost=Decimal("0.00"),
        total_production_cost=Decimal("0.00"),
        avg_cost_per_packet=Decimal("0.00"),
        selling_price_before_gst=Decimal(prod.selling_price),
        gross_profit_per_packet=Decimal("0.00"),
        gross_margin_pct=Decimal("0.00"),
        runs=[],
    )
