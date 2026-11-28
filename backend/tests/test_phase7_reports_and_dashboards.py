from datetime import date, timedelta
from decimal import Decimal
import io
import zipfile

import pytest
from sqlalchemy import select

from app.core.permissions import Role
from app.models.customer import Customer
from app.models.product import Product
from app.models.stock_item import StockItem
from app.models.user import User
from app.schemas.bom_production import (
    MaterialConsumptionInput,
    ProductionConsumeRequest,
    ProductionOutputInput,
    ProductionRunCreate,
)
from app.services.master_seed_service import seed_benchmark_master_data
from app.services.phase3_seed_service import seed_phase3_benchmark_data
from app.services.phase4_seed_service import seed_benchmark_bom
from app.services.production_service import (
    complete_production_run,
    create_production_run,
    post_production_run,
    record_material_consumption,
    record_production_output,
    start_production_run,
)
from tests.conftest import auth_headers_for


def _seed_full_benchmark_chain(db_session, client):
    """Create full Phases 2-6 benchmark transactions cleanly in an isolated DB."""
    seed_benchmark_master_data(db_session)
    seed_phase3_benchmark_data(db_session, post_benchmark_purchase=True)
    seed_benchmark_bom(db_session)

    sup = db_session.scalar(select(User).where(User.role == Role.FLOOR_SUPERVISOR))
    sup_headers = auth_headers_for(client, Role.FLOOR_SUPERVISOR)
    sales_headers = auth_headers_for(client, Role.ORDER_MANAGER)
    admin_headers = auth_headers_for(client, Role.ADMIN)

    murukku = db_session.scalar(select(Product).where(Product.sku == "MUR-200"))
    items = {si.sku: si for si in db_session.scalars(select(StockItem)).all()}

    run = create_production_run(
        db_session,
        ProductionRunCreate(
            order_number="PRD-P7-BENCH",
            product_id=murukku.id,
            batch_number="B-P7",
            production_date=date(2026, 11, 20),
            planned_batches=Decimal("1"),
        ),
        actor=sup,
    )
    run = start_production_run(db_session, run.id, actor=sup)
    run = record_material_consumption(
        db_session,
        run.id,
        ProductionConsumeRequest(
            materials=[
                MaterialConsumptionInput(stock_item_id=items["RM-FLOUR"].id, actual_quantity=Decimal("40"), damaged_quantity=Decimal("0")),
                MaterialConsumptionInput(stock_item_id=items["RM-OIL"].id, actual_quantity=Decimal("10.5"), damaged_quantity=Decimal("0")),
                MaterialConsumptionInput(stock_item_id=items["RM-SPICE"].id, actual_quantity=Decimal("1.2"), damaged_quantity=Decimal("0")),
                MaterialConsumptionInput(stock_item_id=items["PKG-POUCH-200"].id, actual_quantity=Decimal("188"), damaged_quantity=Decimal("6")),
                MaterialConsumptionInput(stock_item_id=items["PKG-CARTON"].id, actual_quantity=Decimal("9"), damaged_quantity=Decimal("0")),
            ]
        ),
        actor=sup,
    )
    run = record_production_output(
        db_session,
        run.id,
        ProductionOutputInput(good_quantity=Decimal("188"), damaged_packets=Decimal("0"), cartons_used=Decimal("9")),
        actor=sup,
    )
    run = complete_production_run(db_session, run.id, actor=sup)
    post_production_run(db_session, run.id, actor=sup)

    client.post(
        f"/api/v1/production/{run.id}/expenses",
        headers=sup_headers,
        json={"category": "LABOUR", "description": "Bench labour", "amount": "1200.00", "expense_date": "2026-11-20", "auto_post": True},
    )
    client.post(
        f"/api/v1/production/{run.id}/expenses",
        headers=sup_headers,
        json={"category": "GAS", "description": "Bench gas", "amount": "600.00", "expense_date": "2026-11-20", "auto_post": True},
    )

    ret_a = db_session.scalar(select(Customer).where(Customer.gstin == "33RETLA0001A1Z5"))
    dist_b = db_session.scalar(select(Customer).where(Customer.gstin == "29DISTB0002B1Z5"))

    today = date.today()
    disp_day = today + timedelta(days=2)

    so_a = client.post(
        "/api/v1/orders",
        headers=sales_headers,
        json={"order_number": "SO-P7-RETA", "customer_id": ret_a.id, "order_date": today.isoformat(), "items": [{"product_id": murukku.id, "quantity": "150"}]},
    ).json()
    client.post(f"/api/v1/orders/{so_a['id']}/approve", headers=admin_headers)
    inv_a = client.post(
        "/api/v1/invoices",
        headers=admin_headers,
        json={"sales_order_id": so_a["id"], "invoice_date": today.isoformat()},
    ).json()
    client.post(
        "/api/v1/dispatches",
        headers=admin_headers,
        json={"sales_order_id": so_a["id"], "dispatch_date": disp_day.isoformat()},
    )
    client.post(
        "/api/v1/payments",
        headers=admin_headers,
        json={
            "payment_reference": "PAY-P7-RETA",
            "customer_id": ret_a.id,
            "payment_date": today.isoformat(),
            "payment_method": "UPI",
            "amount_received": "4000.00",
            "allocations": [{"invoice_id": inv_a["id"], "amount": "4000.00"}],
        },
    )

    so_b = client.post(
        "/api/v1/orders",
        headers=sales_headers,
        json={"order_number": "SO-P7-DISTB", "customer_id": dist_b.id, "order_date": "2026-11-23", "items": [{"product_id": murukku.id, "quantity": "120"}]},
    ).json()
    client.post(
        f"/api/v1/orders/{so_b['id']}/approve",
        headers=admin_headers,
        json={"hold_if_insufficient": True},
    )
    return run, murukku, ret_a, inv_a


def test_owner_dashboard_reports_and_reconciliation(client, db_session):
    _seed_full_benchmark_chain(db_session, client)
    admin_headers = auth_headers_for(client, Role.ADMIN)
    auditor_headers = auth_headers_for(client, Role.AUDITOR)

    # 1. Owner dashboard metrics & date-range filter
    owner = client.get(
        "/api/v1/dashboard/owner?date_from=2026-11-01&date_to=2026-11-30",
        headers=admin_headers,
    )
    assert owner.status_code == 200
    od = owner.json()
    assert Decimal(od["monthly_taxable_revenue"]) == Decimal("7500.00")
    assert Decimal(od["total_gst_collected"]) == Decimal("375.00")
    assert Decimal(od["monthly_sales"]) == Decimal("7875.00")
    assert Decimal(od["production_output"]) == Decimal("188")
    assert Decimal(od["finished_goods_stock"]) == Decimal("88")
    assert Decimal(od["total_production_cost"]) == Decimal("5855.00")
    assert Decimal(od["average_cost_per_packet"]) == Decimal("31.14")
    assert Decimal(od["gross_margin_pct"]) == Decimal("37.71")
    assert Decimal(od["total_customer_receivables"]) == Decimal("3875.00")
    assert len(od["alerts"]) > 0

    # Invalid custom range -> 422
    assert (
        client.get(
            "/api/v1/dashboard/owner?date_from=2026-12-01&date_to=2026-11-01",
            headers=admin_headers,
        ).status_code
        == 422
    )

    # 2. Sales, Customer, Product, GST, HSN reports (using Auditor read-only access)
    sr = client.get("/api/v1/reports/sales?date_from=2026-11-01&date_to=2026-11-30", headers=auditor_headers).json()
    assert sr["reconciled_with_invoices"] is True
    assert Decimal(sr["total_taxable"]) == Decimal("7500.00")
    assert Decimal(sr["total_cgst"]) == Decimal("187.50")
    assert Decimal(sr["total_sgst"]) == Decimal("187.50")
    assert Decimal(sr["total_invoice_value"]) == Decimal("7875.00")

    cs = client.get("/api/v1/reports/sales/customers?date_from=2026-11-01&date_to=2026-11-30", headers=auditor_headers).json()
    assert Decimal(cs["total_invoice_value"]) == Decimal("7875.00")
    assert Decimal(cs["total_collected"]) == Decimal("4000.00")
    assert Decimal(cs["total_outstanding"]) == Decimal("3875.00")

    ps = client.get("/api/v1/reports/sales/products?date_from=2026-11-01&date_to=2026-11-30", headers=auditor_headers).json()
    assert Decimal(ps["rows"][0]["total_packets_sold"]) == Decimal("150")

    gst = client.get("/api/v1/reports/gst/outward-supplies?date_from=2026-11-01&date_to=2026-11-30", headers=auditor_headers).json()
    assert gst["reconciled_with_invoices"] is True
    assert Decimal(gst["intra_state_taxable"]) == Decimal("7500.00")
    assert "not an official GST portal" in gst["disclaimer"]

    hsn = client.get("/api/v1/reports/gst/hsn-summary?date_from=2026-11-01&date_to=2026-11-30", headers=auditor_headers).json()
    assert hsn["rows"][0]["hsn_code"] == "19059090"

    # 3. Purchase register & Stock historical reconstruction (before dispatch date vs after dispatch)
    pr = client.get("/api/v1/reports/purchases?preset=all", headers=auditor_headers).json()
    assert pr["reconciled_with_purchases"] is True
    assert Decimal(pr["posted_total"]) > Decimal("0")

    # Historical stock BEFORE dispatch (today) vs AFTER dispatch (today + 2 days)
    pre_cut = date.today().isoformat()
    post_cut = (date.today() + timedelta(days=2)).isoformat()
    hist_pre = client.get(
        f"/api/v1/reports/stock/summary?preset=all&category=FINISHED_GOOD&as_of_date={pre_cut}",
        headers=auditor_headers,
    ).json()
    assert Decimal(hist_pre["rows"][0]["closing_stock"]) == Decimal("238")

    # Stock AFTER dispatch: finished Murukku must be 88
    hist_post = client.get(
        f"/api/v1/reports/stock/summary?preset=all&category=FINISHED_GOOD&as_of_date={post_cut}",
        headers=auditor_headers,
    ).json()
    assert Decimal(hist_post["rows"][0]["closing_stock"]) == Decimal("88")

    sl = client.get(f"/api/v1/reports/stock/ledger?date_from=2020-01-01&date_to={post_cut}", headers=auditor_headers).json()
    assert sl["total"] >= 8

    # 4. Production register, variance, costing reconciliation
    prod_var = client.get("/api/v1/reports/production/variance?date_from=2026-11-01&date_to=2026-11-30", headers=auditor_headers).json()
    assert prod_var["flagged_count"] >= 3
    assert Decimal(prod_var["yield_rows"][0]["yield_variance_pct"]) == Decimal("-6.0000")

    prod_cost = client.get("/api/v1/reports/production/costing?date_from=2026-11-01&date_to=2026-11-30", headers=auditor_headers).json()
    assert prod_cost["reconciled_with_expenses_and_ledger"] is True
    assert Decimal(prod_cost["total_production_cost"]) == Decimal("5855.00")

    # 5. Payment register, receivables & ageing
    pay_reg = client.get("/api/v1/reports/payments?date_from=2026-11-01&date_to=2026-11-30", headers=auditor_headers).json()
    assert pay_reg["reconciled_with_payments"] is True
    assert Decimal(pay_reg["total_received"]) == Decimal("4000.00")

    rec_rep = client.get("/api/v1/reports/receivables?as_of_date=2026-11-26", headers=auditor_headers).json()
    assert rec_rep["reconciled_with_invoices"] is True
    assert Decimal(rec_rep["total_outstanding"]) == Decimal("3875.00")

    age_as_of = (date.today() + timedelta(days=75)).isoformat()
    ag_rep = client.get(f"/api/v1/reports/receivables/ageing?as_of_date={age_as_of}", headers=auditor_headers).json()
    assert ag_rep["reconciled_with_outstanding"] is True
    assert ag_rep["rows"][0]["ageing_category"] == "31-60 days overdue"

    # 6. Exports: CSV, real OOXML .xlsx ZIP, multi-section PDF
    csv_r = client.get("/api/v1/reports/export/csv?report_type=sales&date_from=2026-11-01&date_to=2026-11-30", headers=auditor_headers)
    assert csv_r.status_code == 200
    assert b"INV/2026-27/0001" in csv_r.content

    xlsx_r = client.get("/api/v1/reports/export/excel?report_type=sales&date_from=2026-11-01&date_to=2026-11-30", headers=auditor_headers)
    assert xlsx_r.status_code == 200
    assert xlsx_r.content[:2] == b"PK"
    with zipfile.ZipFile(io.BytesIO(xlsx_r.content), "r") as zf:
        sheet = zf.read("xl/worksheets/sheet1.xml")
        assert b"INV/2026-27/0001" in sheet

    pdf_r = client.get("/api/v1/reports/export/pdf?report_type=sales&date_from=2026-11-01&date_to=2026-11-30", headers=auditor_headers)
    assert pdf_r.status_code == 200
    assert pdf_r.content.startswith(b"%PDF-1.4")
    assert b"Page 1 of 1" in pdf_r.content

    # Empty date window returns empty rows without error
    empty_r = client.get("/api/v1/reports/sales?date_from=2020-01-01&date_to=2020-01-31", headers=auditor_headers)
    assert empty_r.status_code == 200
    assert empty_r.json()["rows"] == []


@pytest.mark.parametrize(
    "role,owner_dash,reports_code,export_code",
    [
        (Role.ADMIN, 200, 200, 200),
        (Role.OWNER, 200, 200, 200),
        (Role.AUDITOR, 403, 200, 200),
        (Role.ORDER_MANAGER, 403, 403, 403),
        (Role.FLOOR_SUPERVISOR, 403, 403, 403),
        (Role.QA_INSPECTOR, 403, 403, 403),
    ],
)
def test_phase7_rbac_and_auditor_read_only(client, role, owner_dash, reports_code, export_code):
    headers = auth_headers_for(client, role)
    assert client.get("/api/v1/dashboard/owner", headers=headers).status_code == owner_dash
    assert client.get("/api/v1/reports/sales", headers=headers).status_code == reports_code
    assert client.get("/api/v1/reports/gst/outward-supplies", headers=headers).status_code == reports_code
    assert client.get("/api/v1/reports/export/csv?report_type=sales", headers=headers).status_code == export_code

    if role == Role.AUDITOR:
        assert client.get("/api/v1/dashboard/finance", headers=headers).status_code == 200
        # Auditor must not mutate transactions
        assert client.post("/api/v1/orders", headers=headers, json={"customer_id": "x", "items": []}).status_code == 403
        assert client.post("/api/v1/payments", headers=headers, json={"customer_id": "x", "payment_method": "CASH", "amount_received": "10"}).status_code == 403


def test_report_reconciliations_detect_database_mismatches(client, db_session):
    """Verify report reconciliation flags reflect real database state and flip to False on mismatches."""
    from app.models.costing_payment import Payment
    from app.models.inventory import StockBalance
    from app.models.production import ProductionMaterial, ProductionRun
    from app.models.purchase import Purchase, PurchaseStatus
    from app.models.sales import Invoice

    _seed_full_benchmark_chain(db_session, client)
    owner_headers = auth_headers_for(client, Role.OWNER)

    # Sanity check: reconciled prior to injected mismatches
    assert client.get("/api/v1/reports/stock/summary?preset=all", headers=owner_headers).json()["reconciled_with_ledger"] is True
    assert client.get("/api/v1/reports/production?preset=all", headers=owner_headers).json()["reconciled_with_runs"] is True
    assert client.get("/api/v1/reports/production/costing?preset=all", headers=owner_headers).json()["reconciled_with_expenses_and_ledger"] is True
    assert client.get("/api/v1/reports/purchases?preset=all", headers=owner_headers).json()["reconciled_with_purchases"] is True
    assert client.get("/api/v1/reports/sales?preset=all", headers=owner_headers).json()["reconciled_with_invoices"] is True
    assert client.get("/api/v1/reports/payments?preset=all", headers=owner_headers).json()["reconciled_with_payments"] is True

    # 1. Inject StockBalance drift vs StockLedger -> stock summary must report False
    bal = db_session.scalar(select(StockBalance).limit(1))
    orig_bal_qty = bal.available_quantity
    bal.available_quantity = Decimal("9999.000000")
    db_session.commit()
    assert client.get("/api/v1/reports/stock/summary?preset=all", headers=owner_headers).json()["reconciled_with_ledger"] is False
    bal.available_quantity = orig_bal_qty
    db_session.commit()

    # 2. Inject ProductionMaterial mismatch vs StockLedger(PRODUCTION_ISSUE) -> production register & costing must report False
    pmat = db_session.scalar(select(ProductionMaterial).limit(1))
    orig_consumed = pmat.total_consumed_base_qty
    pmat.total_consumed_base_qty = Decimal("999.000000")
    db_session.commit()
    assert client.get("/api/v1/reports/production?preset=all", headers=owner_headers).json()["reconciled_with_runs"] is False
    assert client.get("/api/v1/reports/production/costing?preset=all", headers=owner_headers).json()["reconciled_with_expenses_and_ledger"] is False
    pmat.total_consumed_base_qty = orig_consumed
    db_session.commit()

    # 3. Inject Purchase header total mismatch vs line subtotals+tax -> purchase register must report False
    pur = db_session.scalar(select(Purchase).where(Purchase.status == PurchaseStatus.POSTED).limit(1))
    orig_pur_tot = pur.total_amount
    pur.total_amount = Decimal("99999.00")
    db_session.commit()
    assert client.get("/api/v1/reports/purchases?preset=all", headers=owner_headers).json()["reconciled_with_purchases"] is False
    pur.total_amount = orig_pur_tot
    db_session.commit()

    # 4. Inject Invoice grand_total mismatch vs line totals (via direct SQL to simulate out-of-band corruption)
    from sqlalchemy import text

    inv = db_session.scalar(select(Invoice).limit(1))
    orig_inv_tot = inv.grand_total
    db_session.execute(
        text("UPDATE invoices SET grand_total = :val WHERE id = :id"),
        {"val": "99999.00", "id": inv.id},
    )
    db_session.commit()
    db_session.expire_all()
    assert client.get("/api/v1/reports/sales?preset=all", headers=owner_headers).json()["reconciled_with_invoices"] is False
    db_session.execute(
        text("UPDATE invoices SET grand_total = :val WHERE id = :id"),
        {"val": str(orig_inv_tot), "id": inv.id},
    )
    db_session.commit()
    db_session.expire_all()

    # 5. Inject Payment allocation mismatch -> payment register must report False
    pay = db_session.scalar(select(Payment).limit(1))
    orig_pay_alloc = pay.allocated_amount
    pay.allocated_amount = Decimal("1.00")
    db_session.commit()
    assert client.get("/api/v1/reports/payments?preset=all", headers=owner_headers).json()["reconciled_with_payments"] is False
    pay.allocated_amount = orig_pay_alloc
    db_session.commit()

    # 6. Inject ProductionRun actual_good_output drift vs StockLedger(PRODUCTION_OUTPUT) -> production register must report False
    run = db_session.scalar(select(ProductionRun).limit(1))
    orig_good = run.actual_good_output
    run.actual_good_output = Decimal("500.000000")
    db_session.commit()
    assert client.get("/api/v1/reports/production?preset=all", headers=owner_headers).json()["reconciled_with_runs"] is False
    run.actual_good_output = orig_good
    db_session.commit()


def test_purchase_register_stock_item_filter_and_reconciliation(client, db_session):
    """Verify stock_item_id filtering computes line-level totals incl. allocated GST without masking DB mismatches."""
    from sqlalchemy import text

    from app.models.inventory import MovementType, StockLedger
    from app.models.purchase import PaymentStatus, Purchase, PurchaseStatus
    from app.models.supplier import Supplier
    from app.schemas.inventory_purchase import PurchaseCreate, PurchaseItemInput
    from app.services.purchase_service import create_purchase, post_purchase

    seed_benchmark_master_data(db_session)
    seed_phase3_benchmark_data(db_session, post_benchmark_purchase=True)

    admin = db_session.scalar(select(User).where(User.role == Role.ADMIN))
    supplier = db_session.scalar(select(Supplier).where(Supplier.name == "Benchmark Supplier").limit(1))
    items = {si.sku: si for si in db_session.scalars(select(StockItem)).all()}
    auditor_headers = auth_headers_for(client, Role.AUDITOR)

    # 1. Multi-item POSTED purchase with 5% GST: Flour 500 + 25 = 525.00; Oil 700 + 35 = 735.00 (total 1,260.00)
    multi_posted = create_purchase(
        db_session,
        PurchaseCreate(
            reference_number="PUR-MULTI-POSTED-01",
            supplier_id=supplier.id,
            purchase_date=date.today(),
            payment_status=PaymentStatus.PAID,
            items=[
                PurchaseItemInput(
                    stock_item_id=items["RM-FLOUR"].id,
                    unit_id=items["RM-FLOUR"].base_unit_id,
                    quantity=Decimal("10.000000"),
                    unit_rate=Decimal("50.000000"),
                    tax_rate=Decimal("5.00"),
                ),
                PurchaseItemInput(
                    stock_item_id=items["RM-OIL"].id,
                    unit_id=items["RM-OIL"].base_unit_id,
                    quantity=Decimal("5.000000"),
                    unit_rate=Decimal("140.000000"),
                    tax_rate=Decimal("5.00"),
                ),
            ],
        ),
        actor=admin,
    )
    post_purchase(db_session, multi_posted.id, actor=admin)

    # 2. Multi-item DRAFT purchase: Flour 200.00 + Oil 300.00 (total 500.00)
    create_purchase(
        db_session,
        PurchaseCreate(
            reference_number="PUR-MULTI-DRAFT-01",
            supplier_id=supplier.id,
            purchase_date=date.today(),
            payment_status=PaymentStatus.UNPAID,
            items=[
                PurchaseItemInput(
                    stock_item_id=items["RM-FLOUR"].id,
                    unit_id=items["RM-FLOUR"].base_unit_id,
                    quantity=Decimal("4.000000"),
                    unit_rate=Decimal("50.000000"),
                    tax_rate=Decimal("0.00"),
                ),
                PurchaseItemInput(
                    stock_item_id=items["RM-OIL"].id,
                    unit_id=items["RM-OIL"].base_unit_id,
                    quantity=Decimal("2.000000"),
                    unit_rate=Decimal("150.000000"),
                    tax_rate=Decimal("0.00"),
                ),
            ],
        ),
        actor=admin,
    )

    # 3. Multi-item CANCELLED purchase: Flour 100.00 + Spice 200.00 (total 300.00)
    multi_cancel = create_purchase(
        db_session,
        PurchaseCreate(
            reference_number="PUR-MULTI-CANCEL-01",
            supplier_id=supplier.id,
            purchase_date=date.today(),
            payment_status=PaymentStatus.UNPAID,
            items=[
                PurchaseItemInput(
                    stock_item_id=items["RM-FLOUR"].id,
                    unit_id=items["RM-FLOUR"].base_unit_id,
                    quantity=Decimal("2.000000"),
                    unit_rate=Decimal("50.000000"),
                    tax_rate=Decimal("0.00"),
                ),
                PurchaseItemInput(
                    stock_item_id=items["RM-SPICE"].id,
                    unit_id=items["RM-SPICE"].base_unit_id,
                    quantity=Decimal("1.000000"),
                    unit_rate=Decimal("200.000000"),
                    tax_rate=Decimal("0.00"),
                ),
            ],
        ),
        actor=admin,
    )
    cancel_resp = client.post(
        f"/api/v1/purchases/{multi_cancel.id}/cancel",
        headers=auth_headers_for(client, Role.ADMIN),
        json={"reason": "Cancelled order regression test"},
    )
    assert cancel_resp.status_code == 200

    # Unfiltered totals preserve full purchase header totals (2700 + 1260 = 3960, draft 500, cancelled 300)
    unfiltered = client.get("/api/v1/reports/purchases?preset=all", headers=auditor_headers).json()
    assert unfiltered["total"] == 7
    assert Decimal(unfiltered["posted_total"]) == Decimal("3960.00")
    assert Decimal(unfiltered["draft_or_reviewed_total"]) == Decimal("500.00")
    assert Decimal(unfiltered["cancelled_total"]) == Decimal("300.00")
    assert unfiltered["reconciled_with_purchases"] is True

    # Flour filter: posted 2700 + 525 = 3225.00 (incl. allocated GST), draft 200.00, cancelled 100.00
    flour_rep = client.get(
        f"/api/v1/reports/purchases?preset=all&stock_item_id={items['RM-FLOUR'].id}",
        headers=auditor_headers,
    ).json()
    assert flour_rep["total"] == 4
    assert Decimal(flour_rep["posted_total"]) == Decimal("3225.00")
    assert Decimal(flour_rep["draft_or_reviewed_total"]) == Decimal("200.00")
    assert Decimal(flour_rep["cancelled_total"]) == Decimal("100.00")
    assert flour_rep["reconciled_with_purchases"] is True

    # Pagination independence: page_size=1 returns 1 row while totals reflect all 4 matching rows
    flour_paged = client.get(
        f"/api/v1/reports/purchases?preset=all&stock_item_id={items['RM-FLOUR'].id}&page=1&page_size=1",
        headers=auditor_headers,
    ).json()
    assert flour_paged["total"] == 4
    assert len(flour_paged["rows"]) == 1
    assert Decimal(flour_paged["posted_total"]) == Decimal("3225.00")
    assert Decimal(flour_paged["draft_or_reviewed_total"]) == Decimal("200.00")
    assert Decimal(flour_paged["cancelled_total"]) == Decimal("100.00")

    # Oil filter: posted 735.00, draft 300.00, cancelled 0.00
    oil_rep = client.get(
        f"/api/v1/reports/purchases?preset=all&stock_item_id={items['RM-OIL'].id}",
        headers=auditor_headers,
    ).json()
    assert oil_rep["total"] == 2
    assert Decimal(oil_rep["posted_total"]) == Decimal("735.00")
    assert Decimal(oil_rep["draft_or_reviewed_total"]) == Decimal("300.00")
    assert Decimal(oil_rep["cancelled_total"]) == Decimal("0.00")
    assert oil_rep["reconciled_with_purchases"] is True

    # Empty filtered result
    empty_rep = client.get(
        f"/api/v1/reports/purchases?preset=all&stock_item_id={items['PKG-CARTON'].id}",
        headers=auditor_headers,
    ).json()
    assert empty_rep["total"] == 0
    assert empty_rep["rows"] == []
    assert Decimal(empty_rep["posted_total"]) == Decimal("0.00")
    assert Decimal(empty_rep["draft_or_reviewed_total"]) == Decimal("0.00")
    assert Decimal(empty_rep["cancelled_total"]) == Decimal("0.00")
    assert empty_rep["reconciled_with_purchases"] is True

    # Filtered query must NOT mask database mismatches on header or stock ledger
    orig_tot = multi_posted.total_amount
    multi_posted.total_amount = Decimal("99999.00")
    db_session.commit()
    assert (
        client.get(
            f"/api/v1/reports/purchases?preset=all&stock_item_id={items['RM-FLOUR'].id}",
            headers=auditor_headers,
        ).json()["reconciled_with_purchases"]
        is False
    )
    multi_posted.total_amount = orig_tot
    db_session.commit()

    led = db_session.scalar(
        select(StockLedger).where(
            StockLedger.reference_doc_type == "PURCHASE",
            StockLedger.reference_doc_id == "PUR-MULTI-POSTED-01",
            StockLedger.stock_item_id == items["RM-FLOUR"].id,
            StockLedger.movement_type == MovementType.PURCHASE_RECEIPT,
        )
    )
    orig_qty_in = led.quantity_in
    db_session.execute(
        text("UPDATE stock_ledger SET quantity_in = :val WHERE id = :id"),
        {"val": "999.000000", "id": led.id},
    )
    db_session.commit()
    db_session.expire_all()
    assert (
        client.get(
            f"/api/v1/reports/purchases?preset=all&stock_item_id={items['RM-FLOUR'].id}",
            headers=auditor_headers,
        ).json()["reconciled_with_purchases"]
        is False
    )
    db_session.execute(
        text("UPDATE stock_ledger SET quantity_in = :val WHERE id = :id"),
        {"val": str(orig_qty_in), "id": led.id},
    )
    db_session.commit()
