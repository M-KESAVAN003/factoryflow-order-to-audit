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
