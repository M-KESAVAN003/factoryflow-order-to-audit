from datetime import date
from decimal import Decimal
import pytest
from sqlalchemy import select

from app.core.permissions import Role
from app.models.customer import Customer
from app.models.inventory import MovementType, StockBalance, StockLedger
from app.models.product import Product
from app.models.sales import Dispatch, Invoice, SalesOrder, SalesOrderStatus, TaxType
from app.models.stock_item import StockItem
from app.services import sales_service
from app.services.gst_service import get_financial_year
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
from app.schemas.bom_production import (
    MaterialConsumptionInput,
    ProductionConsumeRequest,
    ProductionOutputInput,
    ProductionRunCreate,
)
from tests.conftest import auth_headers_for


def _setup_post_phase4_benchmark_stock(db_session, client):
    """Prepare full Phases 2–4 state leaving finished Murukku 200 g at 238 packets."""
    seed_benchmark_master_data(db_session)
    seed_phase3_benchmark_data(db_session, post_benchmark_purchase=True)
    seed_benchmark_bom(db_session)

    sup = db_session.scalar(
        select(__import__("app.models.user", fromlist=["User"]).User).where(
            __import__("app.models.user", fromlist=["User"]).User.role == Role.FLOOR_SUPERVISOR
        )
    )
    murukku = db_session.scalar(select(Product).where(Product.sku == "MUR-200"))
    items = {si.sku: si for si in db_session.scalars(select(StockItem)).all()}

    run = create_production_run(
        db_session,
        ProductionRunCreate(
            order_number="PRD-PHASE4-BASE",
            product_id=murukku.id,
            batch_number="B-238",
            production_date=date(2026, 11, 26),
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


def test_mandatory_phase5_benchmark_retailer_a_and_distributor_b(client, db_session):
    _setup_post_phase4_benchmark_stock(db_session, client)
    sales_headers = auth_headers_for(client, Role.ORDER_MANAGER)
    admin_headers = auth_headers_for(client, Role.ADMIN)

    murukku = db_session.scalar(select(Product).where(Product.sku == "MUR-200"))
    retailer_a = db_session.scalar(select(Customer).where(Customer.gstin == "33RETLA0001A1Z5"))
    distributor_b = db_session.scalar(select(Customer).where(Customer.gstin == "29DISTB0002B1Z5"))

    # Finished stock before Retailer A dispatch must be 238
    fg_pre = client.get("/api/v1/inventory/finished-goods", headers=admin_headers).json()["items"][0]
    assert Decimal(fg_pre["available_quantity"]) == Decimal("238")

    # 1. Salesman submits Retailer A order (150 packets @ Rs 50, intra-state TN 2.5% CGST + 2.5% SGST)
    order_a_resp = client.post(
        "/api/v1/orders",
        headers=sales_headers,
        json={
            "order_number": "SO-BENCH-RET-A",
            "customer_id": retailer_a.id,
            "order_date": "2026-11-26",
            "items": [{"product_id": murukku.id, "quantity": "150"}],
        },
    )
    assert order_a_resp.status_code == 201
    order_a = order_a_resp.json()
    assert order_a["status"] == "SUBMITTED"
    assert order_a["tax_type"] == "INTRA_STATE"
    assert Decimal(order_a["items"][0]["unit_price"]) == Decimal("50.00")
    assert Decimal(order_a["subtotal"]) == Decimal("7500.00")
    assert Decimal(order_a["cgst_amount"]) == Decimal("187.50")
    assert Decimal(order_a["sgst_amount"]) == Decimal("187.50")
    assert Decimal(order_a["igst_amount"]) == Decimal("0.00")
    assert Decimal(order_a["total_amount"]) == Decimal("7875.00")

    # 2. Stock check & Admin approval (prevents duplicate approval)
    sc_a = client.get(f"/api/v1/orders/{order_a['id']}/stock-check", headers=admin_headers).json()
    assert sc_a["all_available"] is True
    assert Decimal(sc_a["lines"][0]["available_stock"]) == Decimal("238")

    app_resp = client.post(f"/api/v1/orders/{order_a['id']}/approve", headers=admin_headers)
    assert app_resp.status_code == 200
    assert app_resp.json()["status"] == "APPROVED"
    assert client.post(f"/api/v1/orders/{order_a['id']}/approve", headers=admin_headers).status_code == 409

    # 3. Generate GST Invoice (must NOT deduct stock yet!)
    inv_resp = client.post(
        "/api/v1/invoices",
        headers=admin_headers,
        json={"sales_order_id": order_a["id"], "invoice_date": "2026-11-26"},
    )
    assert inv_resp.status_code == 201
    inv = inv_resp.json()
    assert inv["invoice_number"] == "INV/2026-27/0001"
    assert inv["financial_year"] == "2026-27"
    assert inv["tax_type"] == "INTRA_STATE"
    assert Decimal(inv["subtotal"]) == Decimal("7500.00")
    assert Decimal(inv["cgst_amount"]) == Decimal("187.50")
    assert Decimal(inv["sgst_amount"]) == Decimal("187.50")
    assert Decimal(inv["grand_total"]) == Decimal("7875.00")
    assert "Seven Thousand Eight Hundred Seventy Five Only" in inv["amount_in_words"]

    # Duplicate invoice prevented
    assert (
        client.post(
            "/api/v1/invoices",
            headers=admin_headers,
            json={"sales_order_id": order_a["id"], "invoice_date": "2026-11-26"},
        ).status_code
        == 409
    )

    # Stock remains 238 before physical dispatch
    fg_mid = client.get("/api/v1/inventory/finished-goods", headers=admin_headers).json()["items"][0]
    assert Decimal(fg_mid["available_quantity"]) == Decimal("238")

    # Download valid GST Tax Invoice PDF
    pdf_resp = client.get(f"/api/v1/invoices/{inv['id']}/pdf", headers=admin_headers)
    assert pdf_resp.status_code == 200
    assert pdf_resp.headers["content-type"].startswith("application/pdf")
    assert pdf_resp.content.startswith(b"%PDF-1.4")
    assert b"INV/2026-27/0001" in pdf_resp.content
    assert b"33RETLA0001A1Z5" in pdf_resp.content
    assert b"7875.00" in pdf_resp.content

    # 4. Dispatch Retailer A -> deducts 150 packets via StockLedger (238 -> 88)
    dsp_resp = client.post(
        "/api/v1/dispatches",
        headers=admin_headers,
        json={
            "sales_order_id": order_a["id"],
            "dispatch_date": "2026-11-26",
            "vehicle_number": "TN-09-AB-1234",
        },
    )
    assert dsp_resp.status_code == 201
    dsp = dsp_resp.json()
    assert dsp["invoice_number"] == "INV/2026-27/0001"

    # Duplicate dispatch prevented
    assert (
        client.post(
            "/api/v1/dispatches",
            headers=admin_headers,
            json={"sales_order_id": order_a["id"], "dispatch_date": "2026-11-26"},
        ).status_code
        == 409
    )

    # Finished goods closing stock must be 88 packets & ledger reconciled
    fg_post = client.get("/api/v1/inventory/finished-goods", headers=admin_headers).json()["items"][0]
    assert Decimal(fg_post["available_quantity"]) == Decimal("88")
    rec = client.get("/api/v1/inventory/reconcile", headers=admin_headers).json()
    assert rec["all_reconciled"] is True

    # 5. Distributor B (Karnataka, 120 requested, 88 available -> 32 shortage, IGST 5% preview)
    order_b_resp = client.post(
        "/api/v1/orders",
        headers=sales_headers,
        json={
            "order_number": "SO-BENCH-DIST-B",
            "customer_id": distributor_b.id,
            "order_date": "2026-11-26",
            "items": [{"product_id": murukku.id, "quantity": "120"}],
        },
    )
    assert order_b_resp.status_code == 201
    order_b = order_b_resp.json()
    assert order_b["tax_type"] == "INTER_STATE"
    assert order_b["has_stock_shortage"] is True
    assert Decimal(order_b["subtotal"]) == Decimal("6000.00")
    assert Decimal(order_b["cgst_amount"]) == Decimal("0.00")
    assert Decimal(order_b["sgst_amount"]) == Decimal("0.00")
    assert Decimal(order_b["igst_amount"]) == Decimal("300.00")
    assert Decimal(order_b["total_amount"]) == Decimal("6300.00")

    sc_b = client.get(f"/api/v1/orders/{order_b['id']}/stock-check", headers=admin_headers).json()
    assert sc_b["all_available"] is False
    assert sc_b["recommended_action"] == "HOLD_AWAITING_STOCK"
    assert Decimal(sc_b["lines"][0]["requested_quantity"]) == Decimal("120")
    assert Decimal(sc_b["lines"][0]["available_stock"]) == Decimal("88")
    assert Decimal(sc_b["lines"][0]["shortage_quantity"]) == Decimal("32")
    assert Decimal(sc_b["igst_preview"]) == Decimal("300.00")

    # Plain approve rejected (422 insufficient stock); hold moves to AWAITING_STOCK
    assert client.post(f"/api/v1/orders/{order_b['id']}/approve", headers=admin_headers).status_code == 422
    held = client.post(
        f"/api/v1/orders/{order_b['id']}/approve",
        headers=admin_headers,
        json={"hold_if_insufficient": True},
    )
    assert held.status_code == 200
    assert held.json()["status"] == "AWAITING_STOCK"

    # Cannot invoice or dispatch an AWAITING_STOCK order (no overselling)
    assert (
        client.post(
            "/api/v1/invoices",
            headers=admin_headers,
            json={"sales_order_id": order_b["id"], "invoice_date": "2026-11-26"},
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/dispatches",
            headers=admin_headers,
            json={"sales_order_id": order_b["id"], "dispatch_date": "2026-11-26"},
        ).status_code
        == 422
    )

    # Stock remains 88 packets
    fg_final = client.get("/api/v1/inventory/finished-goods", headers=admin_headers).json()["items"][0]
    assert Decimal(fg_final["available_quantity"]) == Decimal("88")


def test_customer_assignment_admin_price_edit_immutability_and_rollback(client, db_session, monkeypatch):
    _setup_post_phase4_benchmark_stock(db_session, client)
    sales_headers = auth_headers_for(client, Role.ORDER_MANAGER)
    admin_headers = auth_headers_for(client, Role.ADMIN)

    murukku = db_session.scalar(select(Product).where(Product.sku == "MUR-200"))
    retailer_a = db_session.scalar(select(Customer).where(Customer.gstin == "33RETLA0001A1Z5"))

    # Create unassigned customer and confirm salesman gets 403
    unassigned = client.post(
        "/api/v1/customers",
        headers=admin_headers,
        json={
            "name": "Other Rep Customer",
            "customer_type": "Retailer",
            "gstin": "33OTHER0001Z1Z5",
            "phone": "+91-44-1111-2222",
            "address": "99 West Rd",
            "city": "Madurai",
            "state": "Tamil Nadu",
            "state_code": "33",
            "credit_limit": "20000.00",
        },
    ).json()
    assert (
        client.post(
            "/api/v1/orders",
            headers=sales_headers,
            json={"customer_id": unassigned["id"], "items": [{"product_id": murukku.id, "quantity": "10"}]},
        ).status_code
        == 403
    )

    # Financial year helper check (Apr vs Feb)
    assert get_financial_year(date(2026, 2, 15)) == "2025-26"
    assert get_financial_year(date(2026, 11, 26)) == "2026-27"

    # Salesman creates order; admin edits qty & authorized price; salesman blocked from editing price
    so = client.post(
        "/api/v1/orders",
        headers=sales_headers,
        json={"order_number": "SO-RB-01", "customer_id": retailer_a.id, "items": [{"product_id": murukku.id, "quantity": "20"}]},
    ).json()
    assert (
        client.put(
            f"/api/v1/orders/{so['id']}",
            headers=sales_headers,
            json={"items": [{"product_id": murukku.id, "quantity": "10", "unit_price": "40.00"}]},
        ).status_code
        == 403
    )
    edited = client.put(
        f"/api/v1/orders/{so['id']}",
        headers=admin_headers,
        json={"status": "UNDER_REVIEW", "items": [{"product_id": murukku.id, "quantity": "10", "unit_price": "55.00"}]},
    ).json()
    assert edited["status"] == "UNDER_REVIEW"
    assert Decimal(edited["subtotal"]) == Decimal("550.00")

    client.post(f"/api/v1/orders/{so['id']}/approve", headers=admin_headers)
    inv = client.post("/api/v1/invoices", headers=admin_headers, json={"sales_order_id": so["id"]}).json()

    # Posted invoice immutability & Credit Note issuance
    inv_row = db_session.get(Invoice, inv["id"])
    inv_row.notes = None if hasattr(inv_row, "notes") else None
    inv_row.billing_address = "Tampered"
    with pytest.raises(ValueError, match="immutable"):
        db_session.flush()
    db_session.rollback()

    cn_resp = client.post(
        f"/api/v1/invoices/{inv['id']}/credit-notes",
        headers=admin_headers,
        json={"reason": "Rate correction audit", "amount": "50.00"},
    )
    assert cn_resp.status_code == 201
    assert cn_resp.json()["credit_note_number"].startswith("CN/")

    # Rollback test on Dispatch crash -> stock remains 238 and order stays INVOICED
    def boom(*args, **kwargs):
        raise RuntimeError("Simulated dispatch DB crash")

    monkeypatch.setattr(sales_service, "record_audit_event", boom)
    with pytest.raises(RuntimeError, match="Simulated dispatch DB crash"):
        client.post("/api/v1/dispatches", headers=admin_headers, json={"sales_order_id": so["id"]})

    fg_bal = db_session.scalar(select(StockBalance).where(StockBalance.stock_item_id == murukku.stock_item_id))
    assert Decimal(fg_bal.available_quantity) == Decimal("238")
    assert db_session.get(SalesOrder, so["id"]).status == SalesOrderStatus.INVOICED
