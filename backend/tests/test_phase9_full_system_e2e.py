from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import io
import zipfile

from alembic import command
from alembic.config import Config
from fastapi import HTTPException
import pytest
from sqlalchemy import Numeric, inspect, select
from sqlalchemy.engine import create_engine

from app.api.v1.sales_orders import _enforce_sync_rate_limit, reset_sync_rate_limits
from app.core.database import Base
from app.core.permissions import Role
from app.models.customer import Customer
from app.models.inventory import StockBalance, StockLedger
from app.models.product import Product
from app.models.stock_item import StockItem
from app.models.unit import Unit
from app.models.user import User
from app.schemas.costing_payment import ExpenseCategory
from app.schemas.inventory_purchase import PurchaseCreate, PurchaseItemInput
from app.schemas.bom_production import (
    MaterialConsumptionInput,
    ProductionConsumeRequest,
    ProductionOutputInput,
    ProductionRunCreate,
)
from app.services.costing_service import build_run_costing
from app.services.ledger_service import reconcile_stock_balances
from app.services.master_seed_service import seed_benchmark_master_data
from app.services.phase3_seed_service import seed_opening_inventory
from app.services.phase4_seed_service import seed_benchmark_bom
from app.services.production_service import (
    complete_production_run,
    create_production_run,
    post_production_run,
    record_material_consumption,
    record_production_output,
    start_production_run,
)
from app.services.purchase_service import create_purchase, post_purchase
from app.services.user_service import create_user
from app.schemas.user import UserCreate
from scripts.benchmark_reset_seed import reset_and_seed_benchmark_db, validate_safe_test_database_url
from tests.conftest import SEED_PASSWORD, auth_headers_for


def test_database_schema_integrity_constraints_and_alembic(tmp_path):
    """Verify PKs, FKs, unique constraints, NUMERIC precision, StockLedger immutability, and migrations."""
    db_file = tmp_path / "phase9_integrity.db"
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_file}")
    command.upgrade(cfg, "head")

    engine = create_engine(f"sqlite:///{db_file}")
    insp = inspect(engine)
    tables = set(insp.get_table_names())
    expected_tables = {
        "users",
        "audit_logs",
        "units",
        "unit_conversions",
        "stock_items",
        "products",
        "suppliers",
        "customers",
        "purchases",
        "purchase_items",
        "stock_balances",
        "stock_ledger",
        "stock_adjustments",
        "bom_headers",
        "bom_lines",
        "production_runs",
        "production_materials",
        "production_outputs",
        "production_wastage",
        "sales_orders",
        "sales_order_items",
        "invoices",
        "invoice_items",
        "credit_notes",
        "dispatches",
        "dispatch_items",
        "production_expenses",
        "payments",
        "payment_allocations",
    }
    assert expected_tables.issubset(tables)

    # Every core table has a PK and expected NUMERIC monetary/quantity columns
    for tbl in expected_tables:
        pk = insp.get_pk_constraint(tbl)
        assert pk and pk["constrained_columns"], f"Missing PK on {tbl}"

    # Verify NUMERIC columns never degrade to FLOAT
    for tbl_name, col_names in (
        ("stock_ledger", {"quantity_in", "quantity_out", "unit_cost", "total_value", "balance_qty_after", "avg_cost_after", "balance_value_after"}),
        ("invoices", {"subtotal", "cgst_amount", "sgst_amount", "igst_amount", "tax_amount", "grand_total"}),
        ("production_expenses", {"amount"}),
        ("payments", {"amount_received", "allocated_amount", "unallocated_advance"}),
    ):
        cols = {c["name"]: c["type"] for c in insp.get_columns(tbl_name)}
        for cn in col_names:
            assert isinstance(cols[cn], Numeric), f"{tbl_name}.{cn} must be NUMERIC, got {cols[cn]}"

    # Unique indexes / constraints
    so_uniques = {ix["name"] for ix in insp.get_indexes("sales_orders") if ix["unique"]}
    assert "ix_sales_orders_idempotency_key" in so_uniques
    inv_uqs = {uq["name"] for uq in insp.get_unique_constraints("invoices")}
    assert {"uq_invoice_fy_sequence", "uq_invoice_sales_order"}.issubset(inv_uqs)
    engine.dispose()


def test_benchmark_reset_seed_safety_guards(tmp_path, monkeypatch):
    """Ensure reset/seed script rejects production/main DBs and runs cleanly on isolated test DBs."""
    with pytest.raises(RuntimeError, match="production"):
        monkeypatch.setenv("ENVIRONMENT", "production")
        validate_safe_test_database_url("sqlite:///./safe_test.db")

    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/factoryflow_main")
    with pytest.raises(RuntimeError, match="main DATABASE_URL"):
        validate_safe_test_database_url("postgresql://user:pass@localhost:5432/factoryflow_main")

    with pytest.raises(RuntimeError, match="test"):
        validate_safe_test_database_url("postgresql://user:pass@localhost:5432/neondb")

    isolated_db = tmp_path / "isolated_benchmark_test.db"
    res = reset_and_seed_benchmark_db(f"sqlite:///{isolated_db}")
    assert res["idempotency_verified"] is True
    assert res["users_created"] == 5
    assert res["opening_entries"] == 6
    assert res["boms_created"] == 1


def test_complete_10_step_internship_benchmark_reports_exports_and_sync(client, db_session):
    """Execute the entire official internship benchmark Steps 1-10 + Reports + Exports + PWA Sync."""
    reset_sync_rate_limits()
    seed_benchmark_master_data(db_session)
    admin = db_session.scalar(select(User).where(User.role == Role.ADMIN))
    sup = db_session.scalar(select(User).where(User.role == Role.FLOOR_SUPERVISOR))
    seed_opening_inventory(db_session, actor=admin)
    seed_benchmark_bom(db_session)

    admin_h = auth_headers_for(client, Role.ADMIN)
    sup_h = auth_headers_for(client, Role.FLOOR_SUPERVISOR)
    sales_h = auth_headers_for(client, Role.ORDER_MANAGER)
    auditor_h = auth_headers_for(client, Role.AUDITOR)

    # StockLedger immutability check (event listeners reject updates/deletes)
    first_ledger = db_session.scalar(select(StockLedger).limit(1))
    first_ledger.quantity_in = Decimal("999.000000")
    with pytest.raises(ValueError, match="immutable"):
        db_session.flush()
    db_session.rollback()

    items = {si.sku: si for si in db_session.scalars(select(StockItem)).all()}
    supplier = db_session.scalar(select(Product).where(Product.sku == "MUR-200"))  # check supplier next
    from app.models.supplier import Supplier

    bench_sup = db_session.scalar(select(Supplier).where(Supplier.gstin == "33BENCH0001A1Z5"))
    murukku = db_session.scalar(select(Product).where(Product.sku == "MUR-200"))
    ret_a = db_session.scalar(select(Customer).where(Customer.gstin == "33RETLA0001A1Z5"))
    dist_b = db_session.scalar(select(Customer).where(Customer.gstin == "29DISTB0002B1Z5"))

    # STEP 1 - PURCHASE: 60 kg Flour @ Rs 45 -> 160 kg @ avg Rs 43.125 = Rs 6,900
    purch = create_purchase(
        db_session,
        PurchaseCreate(
            reference_number="BENCH-QA-FLOUR-001",
            supplier_id=bench_sup.id,
            purchase_date=date.today(),
            items=[
                PurchaseItemInput(
                    stock_item_id=items["RM-FLOUR"].id,
                    unit_id=items["RM-FLOUR"].base_unit_id,
                    quantity=Decimal("60.000000"),
                    unit_rate=Decimal("45.000000"),
                    tax_rate=Decimal("0.00"),
                )
            ],
        ),
        actor=admin,
    )
    post_purchase(db_session, purch.id, actor=admin)

    flour_bal = db_session.scalar(select(StockBalance).where(StockBalance.stock_item_id == items["RM-FLOUR"].id))
    assert Decimal(flour_bal.available_quantity) == Decimal("160.000000")
    assert Decimal(flour_bal.average_cost) == Decimal("43.125000")
    assert Decimal(flour_bal.total_value) == Decimal("6900.0000")

    # STEP 2 - PRODUCTION: Expected 200 -> Flour 40, Oil 10.5, Spice 1.2, 188 good + 6 damaged pouches, 9 cartons
    run = create_production_run(
        db_session,
        ProductionRunCreate(
            order_number="PRD-QA-BENCH",
            product_id=murukku.id,
            batch_number="B-QA-01",
            production_date=date.today(),
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

    # STEP 3 - INVENTORY VALIDATION AFTER PRODUCTION
    expected_post_prod = {
        "RM-FLOUR": Decimal("120.000000"),
        "RM-OIL": Decimal("19.500000"),
        "RM-SPICE": Decimal("3.800000"),
        "PKG-POUCH-200": Decimal("306.000000"),
        "PKG-CARTON": Decimal("21.000000"),
        "MUR-200": Decimal("238.000000"),
    }
    for sku, exp_qty in expected_post_prod.items():
        bal = db_session.scalar(select(StockBalance).where(StockBalance.stock_item_id == items[sku].id))
        assert Decimal(bal.available_quantity) == exp_qty, f"{sku} expected {exp_qty}, got {bal.available_quantity}"

    recon = reconcile_stock_balances(db_session)
    assert recon.all_reconciled is True

    # STEP 4 - VARIANCE VALIDATION
    var_r = client.get(f"/api/v1/production/{run.id}/variance", headers=admin_h)
    assert var_r.status_code == 200
    vd = var_r.json()
    assert Decimal(vd["yield_variance_pct"]) == Decimal("-6.0000")
    assert "8 packets remain unpacked" in vd["packaging_warning"]
    mat_v = {m["material_name"]: Decimal(m["variance_pct"]) for m in vd["materials"]}
    assert mat_v["Cooking oil"] == Decimal("5.0000")
    assert mat_v["200 g pouch"] == Decimal("-3.0000")
    assert mat_v["Carton"] == Decimal("-10.0000")

    # STEP 5 & 6 - RETAILER A ORDER -> APPROVAL -> GST INVOICE & PDF
    so_a = client.post(
        "/api/v1/orders",
        headers=sales_h,
        json={"order_number": "SO-QA-RETA", "customer_id": ret_a.id, "order_date": date.today().isoformat(), "items": [{"product_id": murukku.id, "quantity": "150"}]},
    ).json()
    assert client.post(f"/api/v1/orders/{so_a['id']}/approve", headers=admin_h).status_code == 200

    inv_resp = client.post(
        "/api/v1/invoices",
        headers=admin_h,
        json={"sales_order_id": so_a["id"], "invoice_date": date.today().isoformat()},
    )
    assert inv_resp.status_code == 201
    inv_a = inv_resp.json()
    assert Decimal(inv_a["subtotal"]) == Decimal("7500.00")
    assert Decimal(inv_a["cgst_amount"]) == Decimal("187.50")
    assert Decimal(inv_a["sgst_amount"]) == Decimal("187.50")
    assert Decimal(inv_a["tax_amount"]) == Decimal("375.00")
    assert Decimal(inv_a["grand_total"]) == Decimal("7875.00")

    inv_pdf = client.get(f"/api/v1/invoices/{inv_a['id']}/pdf", headers=auditor_h)
    assert inv_pdf.status_code == 200
    assert inv_pdf.content.startswith(b"%PDF-1.4")
    assert inv_a["invoice_number"].encode() in inv_pdf.content
    assert b"Retailer A" in inv_pdf.content

    # STEP 7 - DISPATCH 150 PACKETS -> FINISHED STOCK = 88
    disp = client.post(
        "/api/v1/dispatches",
        headers=admin_h,
        json={"sales_order_id": so_a["id"], "dispatch_date": date.today().isoformat()},
    )
    assert disp.status_code == 201
    fg_bal = db_session.scalar(select(StockBalance).where(StockBalance.stock_item_id == items["MUR-200"].id))
    assert Decimal(fg_bal.available_quantity) == Decimal("88.000000")

    # STEP 8 - DISTRIBUTOR B SHORTAGE (120 vs 88 -> shortage 32, IGST 5% preview, no invoice/dispatch)
    so_b = client.post(
        "/api/v1/orders",
        headers=sales_h,
        json={"order_number": "SO-QA-DISTB", "customer_id": dist_b.id, "order_date": date.today().isoformat(), "items": [{"product_id": murukku.id, "quantity": "120"}]},
    ).json()
    sc_b = client.get(f"/api/v1/orders/{so_b['id']}/stock-check", headers=admin_h).json()
    assert sc_b["all_available"] is False
    assert sc_b["tax_type"] == "INTER_STATE"
    assert Decimal(sc_b["igst_preview"]) == Decimal("300.00")
    assert Decimal(sc_b["total_preview"]) == Decimal("6300.00")
    assert Decimal(sc_b["lines"][0]["shortage_quantity"]) == Decimal("32.000000")

    hold_b = client.post(f"/api/v1/orders/{so_b['id']}/approve", headers=admin_h, json={"hold_if_insufficient": True})
    assert hold_b.status_code == 200
    assert hold_b.json()["status"] == "AWAITING_STOCK"
    # Cannot invoice or dispatch AWAITING_STOCK
    assert client.post("/api/v1/invoices", headers=admin_h, json={"sales_order_id": so_b["id"]}).status_code in (409, 422)

    # STEP 9 - RETAILER A PAYMENT Rs 4,000 -> OUTSTANDING Rs 3,875
    pay_resp = client.post(
        "/api/v1/payments",
        headers=admin_h,
        json={
            "payment_reference": "PAY-QA-RETA-001",
            "customer_id": ret_a.id,
            "payment_date": date.today().isoformat(),
            "payment_method": "BANK_TRANSFER",
            "amount_received": "4000.00",
            "allocations": [{"invoice_id": inv_a["id"], "amount": "4000.00"}],
        },
    )
    assert pay_resp.status_code == 201
    rec = client.get(f"/api/v1/reports/receivables?as_of_date={date.today().isoformat()}", headers=auditor_h).json()
    assert Decimal(rec["total_invoiced"]) == Decimal("7875.00")
    assert Decimal(rec["total_paid"]) == Decimal("4000.00")
    assert Decimal(rec["total_outstanding"]) == Decimal("3875.00")
    assert rec["reconciled_with_invoices"] is True

    # STEP 10 - PRODUCTION COSTING: Materials+Pkg = 4055 + Labour 1200 + Gas 600 = 5855; 31.143617; 37.71%
    assert client.post(
        f"/api/v1/production/{run.id}/expenses",
        headers=sup_h,
        json={"category": "LABOUR", "description": "Shift labour", "amount": "1200.00", "expense_date": date.today().isoformat(), "auto_post": True},
    ).status_code == 201
    assert client.post(
        f"/api/v1/production/{run.id}/expenses",
        headers=sup_h,
        json={"category": "GAS", "description": "Fryer LPG + power", "amount": "600.00", "expense_date": date.today().isoformat(), "auto_post": True},
    ).status_code == 201

    costing = build_run_costing(db_session, run.id)
    mat_costs = {m.stock_item_name: m.total_cost for m in costing.materials}
    assert mat_costs["Flour"] == Decimal("1725.00")
    assert mat_costs["Cooking oil"] == Decimal("1470.00")
    assert mat_costs["Salt and spice mix"] == Decimal("240.00")
    assert mat_costs["200 g pouch"] == Decimal("485.00")
    assert mat_costs["Carton"] == Decimal("135.00")
    assert costing.raw_material_cost == Decimal("3435.00")  # 1725 + 1470 + 240
    assert costing.packaging_cost == Decimal("620.00")      # 485 + 135
    assert costing.raw_material_cost + costing.packaging_cost == Decimal("4055.00")
    assert costing.total_overhead_cost == Decimal("1800.00")
    assert costing.total_production_cost == Decimal("5855.00")
    assert abs(costing.cost_per_packet_exact - Decimal("31.143617")) <= Decimal("0.000001")
    assert costing.cost_per_packet_display == Decimal("31.14")
    assert costing.gross_profit_per_packet == Decimal("18.86")
    assert costing.gross_margin_pct == Decimal("37.71")

    # ALL DASHBOARD + REPORTS + EXPORTS RECONCILE
    od = client.get("/api/v1/dashboard/owner?preset=all", headers=admin_h).json()
    assert Decimal(od["finished_goods_stock"]) == Decimal("88")
    assert Decimal(od["total_production_cost"]) == Decimal("5855.00")
    assert Decimal(od["total_customer_receivables"]) == Decimal("3875.00")

    for ep in (
        "/api/v1/reports/sales?preset=all",
        "/api/v1/reports/sales/customers?preset=all",
        "/api/v1/reports/sales/products?preset=all",
        "/api/v1/reports/sales/salesmen?preset=all",
        "/api/v1/reports/gst/outward-supplies?preset=all",
        "/api/v1/reports/gst/hsn-summary?preset=all",
        "/api/v1/reports/purchases?preset=all",
        "/api/v1/reports/stock/summary?preset=all",
        "/api/v1/reports/stock/ledger?preset=all",
        "/api/v1/reports/production?preset=all",
        "/api/v1/reports/production/variance?preset=all",
        "/api/v1/reports/production/costing?preset=all",
        "/api/v1/reports/payments?preset=all",
        "/api/v1/reports/receivables",
        "/api/v1/reports/receivables/ageing",
    ):
        assert client.get(ep, headers=auditor_h).status_code == 200, f"Failed report {ep}"

    # Verify purchase report reconciliation check actually validates
    purch_rep = client.get("/api/v1/reports/purchases?preset=all", headers=auditor_h).json()
    assert purch_rep["reconciled_with_purchases"] is True
    assert Decimal(purch_rep["posted_total"]) == Decimal("2700.00")

    # Export reconciliation (CSV, XLSX, PDF all carry INV number and Rs 7,875)
    for fmt in ("csv", "excel", "pdf"):
        er = client.get(f"/api/v1/reports/export/{fmt}?report_type=sales&preset=all", headers=auditor_h)
        assert er.status_code == 200
        if fmt == "excel":
            with zipfile.ZipFile(io.BytesIO(er.content), "r") as zf:
                assert b"7875.00" in zf.read("xl/worksheets/sheet1.xml")
        elif fmt == "csv":
            assert b"7875.00" in er.content
        else:
            assert er.content.startswith(b"%PDF-1.4") and b"7875.00" in er.content


def test_phase9_security_duplicates_and_negative_controls(client, db_session):
    """Comprehensive security, cross-salesman isolation, duplicate prevention, and financial/stock bounds."""
    reset_sync_rate_limits()
    seed_benchmark_master_data(db_session)
    admin = db_session.scalar(select(User).where(User.role == Role.ADMIN))
    seed_opening_inventory(db_session, actor=admin)

    # Create a second salesman (Salesman B) not assigned to Retailer A
    salesman_b = create_user(
        db_session,
        UserCreate(
            email="salesman_b@factoryflow.io",
            full_name="Salesman B",
            department="Field Sales",
            role=Role.ORDER_MANAGER,
            password=SEED_PASSWORD,
        ),
        actor=admin,
    )
    sales_b_login = client.post(
        "/api/v1/auth/login",
        json={"email": "salesman_b@factoryflow.io", "password": SEED_PASSWORD},
    )
    assert sales_b_login.status_code == 200
    sales_b_h = {"Authorization": f"Bearer {sales_b_login.json()['access_token']}"}

    sales_a_h = auth_headers_for(client, Role.ORDER_MANAGER)
    admin_h = auth_headers_for(client, Role.ADMIN)
    auditor_h = auth_headers_for(client, Role.AUDITOR)

    ret_a = db_session.scalar(select(Customer).where(Customer.gstin == "33RETLA0001A1Z5"))
    murukku = db_session.scalar(select(Product).where(Product.sku == "MUR-200"))

    # 1. Invalid login & unauthenticated access
    assert client.post("/api/v1/auth/login", json={"email": "admin@factoryflow.io", "password": "Wrong!"}).status_code == 401
    assert client.get("/api/v1/orders").status_code == 401

    # 2. Salesman A submits order -> Salesman B cannot read or submit for Salesman A's customer
    so = client.post(
        "/api/v1/orders",
        headers=sales_a_h,
        json={"order_number": "SO-QA-SEC-01", "customer_id": ret_a.id, "items": [{"product_id": murukku.id, "quantity": "10"}]},
    ).json()
    assert client.get(f"/api/v1/orders/{so['id']}", headers=sales_b_h).status_code == 403
    assert client.post(
        "/api/v1/orders",
        headers=sales_b_h,
        json={"customer_id": ret_a.id, "items": [{"product_id": murukku.id, "quantity": "5"}]},
    ).status_code == 403

    # 3. Duplicate invoice & dispatch prevented cleanly (409)
    client.post(f"/api/v1/orders/{so['id']}/approve", headers=admin_h)
    assert client.post("/api/v1/invoices", headers=admin_h, json={"sales_order_id": so["id"]}).status_code == 201
    assert client.post("/api/v1/invoices", headers=admin_h, json={"sales_order_id": so["id"]}).status_code == 409
    assert client.post("/api/v1/dispatches", headers=admin_h, json={"sales_order_id": so["id"]}).status_code == 201
    assert client.post("/api/v1/dispatches", headers=admin_h, json={"sales_order_id": so["id"]}).status_code == 409

    # 4. Duplicate payment transaction reference prevented cleanly (409)
    inv_id = client.get(f"/api/v1/orders/{so['id']}", headers=admin_h).json()["invoice_id"]
    p1 = {
        "payment_reference": "PAY-SEC-001",
        "customer_id": ret_a.id,
        "payment_method": "UPI",
        "transaction_reference": "UTR-UNIQUE-999",
        "amount_received": "100.00",
        "allocations": [{"invoice_id": inv_id, "amount": "100.00"}],
    }
    assert client.post("/api/v1/payments", headers=admin_h, json=p1).status_code == 201
    p1_dup = {**p1, "payment_reference": "PAY-SEC-002"}
    assert client.post("/api/v1/payments", headers=admin_h, json=p1_dup).status_code == 409

    # 5. Negative stock adjustment / negative financial values / invalid unit conversions blocked (422)
    flour = db_session.scalar(select(StockItem).where(StockItem.sku == "RM-FLOUR"))
    assert (
        client.post(
            "/api/v1/inventory/adjustments",
            headers=admin_h,
            json={"stock_item_id": flour.id, "physical_count": "-5", "reason": "Test", "adjustment_date": date.today().isoformat()},
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/payments",
            headers=admin_h,
            json={"customer_id": ret_a.id, "payment_method": "CASH", "amount_received": "-50.00"},
        ).status_code
        == 422
    )
    kg = db_session.scalar(select(Unit).where(Unit.symbol == "kg"))
    litre = db_session.scalar(select(Unit).where(Unit.symbol == "litre"))
    assert (
        client.post(
            "/api/v1/unit-conversions",
            headers=admin_h,
            json={"from_unit_id": kg.id, "to_unit_id": litre.id, "conversion_factor": "1.0"},
        ).status_code
        == 422
    )

    # 6. Auditor blocked from all write/delete operations
    assert client.post("/api/v1/orders", headers=auditor_h, json={"customer_id": ret_a.id, "items": []}).status_code == 403
    assert client.post("/api/v1/purchases", headers=auditor_h, json={}).status_code == 403
    assert client.post("/api/v1/inventory/adjustments", headers=auditor_h, json={}).status_code == 403
    assert client.delete("/api/v1/audit-logs", headers=auditor_h).status_code == 405

    # 7. Sync rate limiter enforces 429 cleanly after threshold
    reset_sync_rate_limits()
    for _ in range(120):
        _enforce_sync_rate_limit(salesman_b.id)
    with pytest.raises(HTTPException) as exc:
        _enforce_sync_rate_limit(salesman_b.id)
    assert exc.value.status_code == 429
    reset_sync_rate_limits()
