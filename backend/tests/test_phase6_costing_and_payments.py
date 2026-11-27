from datetime import date, timedelta
from decimal import Decimal
import pytest
from sqlalchemy import select

from app.core.permissions import Role
from app.models.costing_payment import CustomerPaymentMethod, Payment, PaymentAllocation, ProductionExpense
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
from app.services import payment_service
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


def _setup_phase4_and_5_benchmark(db_session, client):
    """Prepare Phases 2–5 benchmark state: PRD-P6-BASE (188 pkts) + Retailer A invoice (Rs 7,875)."""
    seed_benchmark_master_data(db_session)
    seed_phase3_benchmark_data(db_session, post_benchmark_purchase=True)
    seed_benchmark_bom(db_session)

    sup = db_session.scalar(select(User).where(User.role == Role.FLOOR_SUPERVISOR))
    murukku = db_session.scalar(select(Product).where(Product.sku == "MUR-200"))
    items = {si.sku: si for si in db_session.scalars(select(StockItem)).all()}

    run = create_production_run(
        db_session,
        ProductionRunCreate(
            order_number="PRD-P6-BASE",
            product_id=murukku.id,
            batch_number="B-P6",
            production_date=date(2026, 11, 1),
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
    run = post_production_run(db_session, run.id, actor=sup)

    sales_headers = auth_headers_for(client, Role.ORDER_MANAGER)
    admin_headers = auth_headers_for(client, Role.ADMIN)
    retailer_a = db_session.scalar(select(Customer).where(Customer.gstin == "33RETLA0001A1Z5"))

    so = client.post(
        "/api/v1/orders",
        headers=sales_headers,
        json={
            "order_number": "SO-P6-RETA",
            "customer_id": retailer_a.id,
            "order_date": "2026-11-01",
            "items": [{"product_id": murukku.id, "quantity": "150"}],
        },
    ).json()
    client.post(f"/api/v1/orders/{so['id']}/approve", headers=admin_headers)
    inv = client.post(
        "/api/v1/invoices",
        headers=admin_headers,
        json={"sales_order_id": so["id"], "invoice_date": "2026-11-01"},
    ).json()
    client.post(
        "/api/v1/dispatches",
        headers=admin_headers,
        json={"sales_order_id": so["id"], "dispatch_date": "2026-11-01"},
    )
    return run, murukku, retailer_a, inv


def test_mandatory_benchmark_production_costing_and_expenses(client, db_session):
    run, murukku, _, _ = _setup_phase4_and_5_benchmark(db_session, client)
    sup_headers = auth_headers_for(client, Role.FLOOR_SUPERVISOR)
    admin_headers = auth_headers_for(client, Role.ADMIN)

    # 1. Create Draft Labour expense (Rs 1000 -> edit to Rs 1200 -> post -> duplicate post 409)
    exp_lab = client.post(
        f"/api/v1/production/{run.id}/expenses",
        headers=sup_headers,
        json={
            "category": "LABOUR",
            "description": "Shift cooking & packing labour",
            "amount": "1000.00",
            "expense_date": "2026-11-01",
            "auto_post": False,
        },
    )
    assert exp_lab.status_code == 201
    lab_id = exp_lab.json()["id"]
    assert exp_lab.json()["status"] == "DRAFT"

    edit_lab = client.put(
        f"/api/v1/production/{run.id}/expenses/{lab_id}",
        headers=sup_headers,
        json={"amount": "1200.00"},
    )
    assert edit_lab.status_code == 200
    assert Decimal(edit_lab.json()["amount"]) == Decimal("1200.00")

    post_lab = client.post(f"/api/v1/production/{run.id}/expenses/{lab_id}/post", headers=sup_headers)
    assert post_lab.status_code == 200
    assert post_lab.json()["status"] == "POSTED"

    # Duplicate post & edit after post must return 409 Conflict
    assert client.post(f"/api/v1/production/{run.id}/expenses/{lab_id}/post", headers=sup_headers).status_code == 409
    assert client.put(f"/api/v1/production/{run.id}/expenses/{lab_id}", headers=sup_headers, json={"amount": "1500.00"}).status_code == 409

    # 2. Add & auto-post Gas + Power expenses totaling Rs 600
    assert (
        client.post(
            f"/api/v1/production/{run.id}/expenses",
            headers=sup_headers,
            json={
                "category": "GAS",
                "description": "LPG burner consumption",
                "amount": "400.00",
                "expense_date": "2026-11-01",
                "auto_post": True,
            },
        ).status_code
        == 201
    )
    assert (
        client.post(
            f"/api/v1/production/{run.id}/expenses",
            headers=sup_headers,
            json={
                "category": "POWER",
                "description": "Sealer & mixer electricity",
                "amount": "200.00",
                "expense_date": "2026-11-01",
                "auto_post": True,
            },
        ).status_code
        == 201
    )

    # 3. Verify Run Costing & Product Costing Benchmark Numbers
    cost = client.get(f"/api/v1/costing/production/{run.id}", headers=admin_headers).json()
    assert Decimal(cost["raw_material_cost"]) == Decimal("3435.00")
    assert Decimal(cost["packaging_cost"]) == Decimal("620.00")
    assert Decimal(cost["material_and_packaging_cost"]) == Decimal("4055.00")
    assert Decimal(cost["labour_cost"]) == Decimal("1200.00")
    assert Decimal(cost["gas_and_power_cost"]) == Decimal("600.00")
    assert Decimal(cost["total_production_cost"]) == Decimal("5855.00")
    assert Decimal(cost["actual_good_output"]) == Decimal("188")
    assert Decimal(cost["cost_per_packet_exact"]) == Decimal("31.143617")
    assert Decimal(cost["cost_per_packet_display"]) == Decimal("31.14")
    assert Decimal(cost["selling_price_before_gst"]) == Decimal("50.00")
    assert Decimal(cost["gross_profit_per_packet"]) == Decimal("18.86")
    assert Decimal(cost["gross_margin_pct"]) == Decimal("37.71")

    mat_by_sku = {m["sku"]: m for m in cost["materials"]}
    assert Decimal(mat_by_sku["RM-FLOUR"]["weighted_avg_rate"]) == Decimal("43.125000")
    assert Decimal(mat_by_sku["RM-FLOUR"]["total_cost"]) == Decimal("1725.00")
    assert Decimal(mat_by_sku["RM-OIL"]["total_cost"]) == Decimal("1470.00")
    assert Decimal(mat_by_sku["RM-SPICE"]["total_cost"]) == Decimal("240.00")
    assert Decimal(mat_by_sku["PKG-POUCH-200"]["total_consumed_qty"]) == Decimal("194")
    assert Decimal(mat_by_sku["PKG-POUCH-200"]["total_cost"]) == Decimal("485.00")
    assert Decimal(mat_by_sku["PKG-CARTON"]["total_cost"]) == Decimal("135.00")

    dash = client.get("/api/v1/costing/production", headers=admin_headers).json()
    assert Decimal(dash["total_production_cost"]) == Decimal("5855.00")
    prod_cost = client.get(f"/api/v1/costing/products/{murukku.id}", headers=admin_headers).json()
    assert Decimal(prod_cost["avg_cost_per_packet"]) == Decimal("31.14")

    # 4. Traceable expense reversal & immutability check
    temp_exp = client.post(
        f"/api/v1/production/{run.id}/expenses",
        headers=sup_headers,
        json={"category": "MAINTENANCE", "description": "Temp repair", "amount": "100.00", "auto_post": True},
    ).json()
    rev = client.post(
        f"/api/v1/production/{run.id}/expenses/{temp_exp['id']}/reverse",
        headers=sup_headers,
    )
    assert rev.status_code == 200
    assert Decimal(rev.json()["amount"]) == Decimal("-100.00")
    cost_after_rev = client.get(f"/api/v1/costing/production/{run.id}", headers=admin_headers).json()
    assert Decimal(cost_after_rev["total_production_cost"]) == Decimal("5855.00")


def test_benchmark_retailer_a_payment_multi_invoice_ageing_and_rollback(client, db_session, monkeypatch):
    _, murukku, retailer_a, inv_a = _setup_phase4_and_5_benchmark(db_session, client)
    admin_headers = auth_headers_for(client, Role.ADMIN)
    sales_headers = auth_headers_for(client, Role.ORDER_MANAGER)

    assert Decimal(inv_a["grand_total"]) == Decimal("7875.00")

    # 1. Record Rs 4,000 partial payment for Retailer A allocated to INV/2026-27/0001
    pay_resp = client.post(
        "/api/v1/payments",
        headers=admin_headers,
        json={
            "payment_reference": "PAY-BENCH-001",
            "customer_id": retailer_a.id,
            "payment_date": "2026-11-10",
            "payment_method": "UPI",
            "amount_received": "4000.00",
            "transaction_reference": "UTR-RET-A-4000",
            "allocations": [{"invoice_id": inv_a["id"], "amount": "4000.00"}],
        },
    )
    assert pay_resp.status_code == 201
    pay_data = pay_resp.json()
    assert Decimal(pay_data["allocated_amount"]) == Decimal("4000.00")
    assert Decimal(pay_data["unallocated_advance"]) == Decimal("0.00")

    # Duplicate payment reference or duplicate transaction reference must return 409 Conflict
    assert (
        client.post(
            "/api/v1/payments",
            headers=admin_headers,
            json={
                "payment_reference": "PAY-BENCH-001",
                "customer_id": retailer_a.id,
                "payment_method": "UPI",
                "amount_received": "4000.00",
            },
        ).status_code
        == 409
    )
    assert (
        client.post(
            "/api/v1/payments",
            headers=admin_headers,
            json={
                "payment_reference": "PAY-BENCH-DUP-TX",
                "customer_id": retailer_a.id,
                "payment_method": "UPI",
                "amount_received": "4000.00",
                "transaction_reference": "UTR-RET-A-4000",
            },
        ).status_code
        == 409
    )

    # 2. Check Invoice Payment Status & Customer Outstanding (7875 - 4000 = 3875)
    inv_pay = client.get(f"/api/v1/invoices/{inv_a['id']}/payments", headers=admin_headers).json()
    assert Decimal(inv_pay["invoice"]["invoice_amount"]) == Decimal("7875.00")
    assert Decimal(inv_pay["invoice"]["paid_amount"]) == Decimal("4000.00")
    assert Decimal(inv_pay["invoice"]["outstanding_amount"]) == Decimal("3875.00")
    assert inv_pay["invoice"]["payment_status"] == "PARTIAL"

    rec = client.get(f"/api/v1/receivables/customers/{retailer_a.id}", headers=admin_headers).json()
    assert Decimal(rec["total_outstanding"]) == Decimal("3875.00")

    ledger = client.get(f"/api/v1/customers/{retailer_a.id}/ledger", headers=admin_headers).json()
    assert Decimal(ledger["closing_outstanding"]) == Decimal("3875.00")
    assert Decimal(ledger["entries"][-1]["running_balance"]) == Decimal("3875.00")

    stmt = client.get(f"/api/v1/customers/{retailer_a.id}/statement", headers=admin_headers).json()
    assert Decimal(stmt["closing_balance"]) == Decimal("3875.00")

    # 3. Receivables Ageing Check (inv date 2026-11-01 + 30d term => due 2026-12-01)
    age_cur = client.get("/api/v1/receivables/ageing?as_of_date=2026-11-26", headers=admin_headers).json()
    assert age_cur["rows"][0]["ageing_category"] == "Current / Not Due"
    age_45 = client.get("/api/v1/receivables/ageing?as_of_date=2027-01-15", headers=admin_headers).json()
    assert age_45["rows"][0]["ageing_category"] == "31-60 days overdue"
    assert age_45["rows"][0]["days_overdue"] == 45

    # 4. Create second Retailer A invoice (10 pkts = Rs 525.00) & test multi-invoice allocation + advance + limits
    so2 = client.post(
        "/api/v1/orders",
        headers=sales_headers,
        json={
            "order_number": "SO-P6-RETA-2",
            "customer_id": retailer_a.id,
            "order_date": "2026-11-12",
            "items": [{"product_id": murukku.id, "quantity": "10"}],
        },
    ).json()
    client.post(f"/api/v1/orders/{so2['id']}/approve", headers=admin_headers)
    inv2 = client.post(
        "/api/v1/invoices",
        headers=admin_headers,
        json={"sales_order_id": so2["id"], "invoice_date": "2026-11-12"},
    ).json()

    # Record Rs 5,000 bank transfer with no initial allocations (unallocated advance), then allocate across both
    adv_pay = client.post(
        "/api/v1/payments",
        headers=admin_headers,
        json={
            "payment_reference": "PAY-MULTI-001",
            "customer_id": retailer_a.id,
            "payment_date": "2026-11-15",
            "payment_method": "BANK_TRANSFER",
            "amount_received": "5000.00",
        },
    ).json()
    assert Decimal(adv_pay["unallocated_advance"]) == Decimal("5000.00")

    # Exceeding invoice outstanding (trying 4000 when 3875 owed) must fail 422
    over_alloc = client.post(
        f"/api/v1/payments/{adv_pay['id']}/allocate",
        headers=admin_headers,
        json={"allocations": [{"invoice_id": inv_a["id"], "amount": "4000.00"}]},
    )
    assert over_alloc.status_code == 422

    # Valid split allocation: 3875 -> inv_a (PAID), 525 -> inv2 (PAID), leaving 600 unallocated advance
    multi_alloc = client.post(
        f"/api/v1/payments/{adv_pay['id']}/allocate",
        headers=admin_headers,
        json={
            "allocations": [
                {"invoice_id": inv_a["id"], "amount": "3875.00"},
                {"invoice_id": inv2["id"], "amount": "525.00"},
            ]
        },
    )
    assert multi_alloc.status_code == 200
    assert Decimal(multi_alloc.json()["allocated_amount"]) == Decimal("4400.00")
    assert Decimal(multi_alloc.json()["unallocated_advance"]) == Decimal("600.00")

    assert client.get(f"/api/v1/invoices/{inv_a['id']}/payments", headers=admin_headers).json()["invoice"]["payment_status"] == "PAID"

    # 5. Rollback test on payment creation crash -> no orphan Payment persisted
    def boom(*args, **kwargs):
        raise RuntimeError("Simulated payment DB crash")

    monkeypatch.setattr(payment_service, "record_audit_event", boom)
    with pytest.raises(RuntimeError, match="Simulated payment DB crash"):
        client.post(
            "/api/v1/payments",
            headers=admin_headers,
            json={
                "payment_reference": "PAY-RB-FAIL",
                "customer_id": retailer_a.id,
                "payment_method": "CASH",
                "amount_received": "100.00",
            },
        )
    assert db_session.scalar(select(Payment).where(Payment.payment_reference == "PAY-RB-FAIL")) is None
