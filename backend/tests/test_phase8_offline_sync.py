from datetime import datetime, timedelta, timezone
from decimal import Decimal
import time

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import inspect, select
from sqlalchemy.engine import create_engine

from app.api.v1.sales_orders import reset_sync_rate_limits
from app.core.permissions import Role
from app.models.audit_log import AuditLog
from app.models.customer import Customer
from app.models.inventory import StockBalance, StockLedger
from app.models.product import Product
from app.models.sales import Dispatch, Invoice, SalesOrder, SalesOrderStatus
from app.models.user import User
from app.services.master_seed_service import seed_benchmark_master_data
from tests.conftest import auth_headers_for


def test_phase8_alembic_includes_sync_columns(tmp_path):
    db_file = tmp_path / "phase8_alembic.db"
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_file}")
    command.upgrade(cfg, "head")

    engine = create_engine(f"sqlite:///{db_file}")
    insp = inspect(engine)
    so_cols = {c["name"] for c in insp.get_columns("sales_orders")}
    soi_cols = {c["name"] for c in insp.get_columns("sales_order_items")}
    assert {
        "idempotency_key",
        "local_order_id",
        "is_offline_order",
        "offline_created_at",
        "synced_at",
        "price_review_required",
        "price_conflict_notes",
    }.issubset(so_cols)
    assert "submitted_unit_price" in soi_cols
    engine.dispose()


def test_offline_sync_idempotency_and_no_auto_dispatch(client, db_session):
    reset_sync_rate_limits()
    seed_benchmark_master_data(db_session)
    sales_headers = auth_headers_for(client, Role.ORDER_MANAGER)
    admin_headers = auth_headers_for(client, Role.ADMIN)

    ret_a = db_session.scalar(select(Customer).where(Customer.gstin == "33RETLA0001A1Z5"))
    murukku = db_session.scalar(select(Product).where(Product.sku == "MUR-200"))

    ledgers_before = len(db_session.scalars(select(StockLedger)).all())
    invoices_before = len(db_session.scalars(select(Invoice)).all())
    dispatches_before = len(db_session.scalars(select(Dispatch)).all())

    payload = {
        "local_order_id": "LOC-20261127-ABCD",
        "idempotency_key": "idem-offline-ret-a-0001",
        "customer_id": ret_a.id,
        "offline_created_at": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
        "notes": "Placed offline at retailer shop",
        "items": [
            {
                "product_id": murukku.id,
                "product_name_snapshot": murukku.name,
                "quantity": "150",
                "cached_unit_price": "50.00",
                "cached_price_timestamp": (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat(),
            }
        ],
    }

    r1 = client.post("/api/v1/orders/sync", headers=sales_headers, json=payload)
    assert r1.status_code == 200, r1.text
    d1 = r1.json()
    assert d1["local_order_id"] == "LOC-20261127-ABCD"
    assert d1["idempotency_key"] == "idem-offline-ret-a-0001"
    assert d1["duplicate"] is False
    assert d1["server_status"] == "SUBMITTED"
    assert d1["sync_status"] == "SYNCED"
    assert d1["price_review_required"] is False
    assert Decimal(d1["order"]["subtotal"]) == Decimal("7500.00")
    assert Decimal(d1["order"]["total_amount"]) == Decimal("7875.00")
    assert d1["order"]["is_offline_order"] is True
    assert d1["order"]["invoice_id"] is None
    assert d1["order"]["dispatch_id"] is None

    # Replay same idempotency_key -> duplicate=True, exact same server_order_id
    r2 = client.post("/api/v1/orders/sync", headers=sales_headers, json=payload)
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["duplicate"] is True
    assert d2["server_order_id"] == d1["server_order_id"]
    assert d2["server_order_number"] == d1["server_order_number"]

    # Confirm zero duplicate rows & zero inventory / invoice / dispatch side effects
    all_orders = db_session.scalars(
        select(SalesOrder).where(SalesOrder.idempotency_key == "idem-offline-ret-a-0001")
    ).all()
    assert len(all_orders) == 1
    assert len(db_session.scalars(select(StockLedger)).all()) == ledgers_before
    assert len(db_session.scalars(select(Invoice)).all()) == invoices_before
    assert len(db_session.scalars(select(Dispatch)).all()) == dispatches_before

    # Admin sees synchronized order as SUBMITTED needing admin approval
    admin_list = client.get("/api/v1/orders", headers=admin_headers)
    assert admin_list.status_code == 200
    assert any(o["id"] == d1["server_order_id"] and o["status"] == "SUBMITTED" for o in admin_list.json()["items"])

    # Audit log captures creation & replay
    actions = {
        a.action
        for a in db_session.scalars(select(AuditLog)).all()
    }
    assert "sales_order.sync_created" in actions
    assert "sales_order.sync_idempotent_replay" in actions


def test_offline_sync_price_conflict_preserved_and_flagged(client, db_session):
    reset_sync_rate_limits()
    seed_benchmark_master_data(db_session)
    sales_headers = auth_headers_for(client, Role.ORDER_MANAGER)
    admin_headers = auth_headers_for(client, Role.ADMIN)

    ret_a = db_session.scalar(select(Customer).where(Customer.gstin == "33RETLA0001A1Z5"))
    murukku = db_session.scalar(select(Product).where(Product.sku == "MUR-200"))

    # Server price increases from Rs 50 -> Rs 55 while salesman is offline
    upd = client.put(
        f"/api/v1/products/{murukku.id}",
        headers=admin_headers,
        json={"selling_price": "55.00"},
    )
    assert upd.status_code == 200

    payload = {
        "local_order_id": "LOC-20261127-PRICE",
        "idempotency_key": "idem-offline-price-drift-01",
        "customer_id": ret_a.id,
        "offline_created_at": datetime.now(timezone.utc).isoformat(),
        "items": [
            {
                "product_id": murukku.id,
                "product_name_snapshot": murukku.name,
                "quantity": "10",
                "cached_unit_price": "50.00",
                "cached_price_timestamp": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
            }
        ],
    }

    res = client.post("/api/v1/orders/sync", headers=sales_headers, json=payload)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["price_review_required"] is True
    assert body["sync_status"] == "NEEDS_REVIEW"
    assert body["server_status"] == "SUBMITTED"
    assert len(body["price_conflicts"]) == 1
    assert Decimal(body["price_conflicts"][0]["submitted_unit_price"]) == Decimal("50.00")
    assert Decimal(body["price_conflicts"][0]["current_server_price"]) == Decimal("55.00")
    assert Decimal(body["order"]["items"][0]["submitted_unit_price"]) == Decimal("50.00")
    assert Decimal(body["order"]["items"][0]["unit_price"]) == Decimal("55.00")


def test_offline_sync_security_assignment_and_safe_retry(client, db_session):
    reset_sync_rate_limits()
    seed_benchmark_master_data(db_session)
    sales_headers = auth_headers_for(client, Role.ORDER_MANAGER)
    admin_headers = auth_headers_for(client, Role.ADMIN)

    ret_a = db_session.scalar(select(Customer).where(Customer.gstin == "33RETLA0001A1Z5"))
    dist_b = db_session.scalar(select(Customer).where(Customer.gstin == "29DISTB0002B1Z5"))
    murukku = db_session.scalar(select(Product).where(Product.sku == "MUR-200"))

    # Unassign Distributor B from salesman -> syncing order for Distributor B must fail (403)
    dist_b.assigned_salesman_id = None
    db_session.commit()

    bad_cust_resp = client.post(
        "/api/v1/orders/sync",
        headers=sales_headers,
        json={
            "local_order_id": "LOC-BAD-CUST",
            "idempotency_key": "idem-unassigned-cust-001",
            "customer_id": dist_b.id,
            "offline_created_at": datetime.now(timezone.utc).isoformat(),
            "items": [
                {
                    "product_id": murukku.id,
                    "quantity": "5",
                    "cached_unit_price": "50.00",
                    "cached_price_timestamp": datetime.now(timezone.utc).isoformat(),
                }
            ],
        },
    )
    assert bad_cust_resp.status_code == 403

    # Non-existent product rejected (404)
    bad_prod_resp = client.post(
        "/api/v1/orders/sync",
        headers=sales_headers,
        json={
            "local_order_id": "LOC-BAD-PROD",
            "idempotency_key": "idem-missing-prod-001",
            "customer_id": ret_a.id,
            "offline_created_at": datetime.now(timezone.utc).isoformat(),
            "items": [
                {
                    "product_id": "nonexistent-product-id",
                    "quantity": "5",
                    "cached_unit_price": "50.00",
                    "cached_price_timestamp": datetime.now(timezone.utc).isoformat(),
                }
            ],
        },
    )
    assert bad_prod_resp.status_code == 404

    # Invalid quantity rejected (422)
    bad_qty_resp = client.post(
        "/api/v1/orders/sync",
        headers=sales_headers,
        json={
            "local_order_id": "LOC-BAD-QTY",
            "idempotency_key": "idem-zero-qty-001",
            "customer_id": ret_a.id,
            "offline_created_at": datetime.now(timezone.utc).isoformat(),
            "items": [
                {
                    "product_id": murukku.id,
                    "quantity": "0",
                    "cached_unit_price": "50.00",
                    "cached_price_timestamp": datetime.now(timezone.utc).isoformat(),
                }
            ],
        },
    )
    assert bad_qty_resp.status_code == 422

    # Safe retry after customer is reassigned cleanly succeeds with same idempotency key
    salesman = db_session.scalar(select(User).where(User.role == Role.ORDER_MANAGER))
    dist_b.assigned_salesman_id = salesman.id
    db_session.commit()

    retry_ok = client.post(
        "/api/v1/orders/sync",
        headers=sales_headers,
        json={
            "local_order_id": "LOC-BAD-CUST",
            "idempotency_key": "idem-unassigned-cust-001",
            "customer_id": dist_b.id,
            "offline_created_at": datetime.now(timezone.utc).isoformat(),
            "items": [
                {
                    "product_id": murukku.id,
                    "quantity": "5",
                    "cached_unit_price": "50.00",
                    "cached_price_timestamp": datetime.now(timezone.utc).isoformat(),
                }
            ],
        },
    )
    assert retry_ok.status_code == 200
    assert retry_ok.json()["duplicate"] is False

    # Unauthorized roles blocked
    for role in (Role.AUDITOR, Role.FLOOR_SUPERVISOR, Role.QA_INSPECTOR):
        h = auth_headers_for(client, role)
        r = client.post(
            "/api/v1/orders/sync",
            headers=h,
            json={
                "local_order_id": "LOC-UNAUTH",
                "idempotency_key": f"idem-unauth-{role.value}",
                "customer_id": ret_a.id,
                "offline_created_at": datetime.now(timezone.utc).isoformat(),
                "items": [
                    {
                        "product_id": murukku.id,
                        "quantity": "1",
                        "cached_unit_price": "50.00",
                        "cached_price_timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                ],
            },
        )
        assert r.status_code == 403
