from datetime import date
from decimal import Decimal
import pytest
from sqlalchemy import func, select

from app.core.permissions import Role
from app.models.inventory import MovementType, StockBalance, StockLedger
from app.models.purchase import Purchase, PurchaseStatus
from app.models.stock_item import StockItem
from app.models.unit import Unit
from app.services import purchase_service
from app.services.master_seed_service import seed_benchmark_master_data
from app.services.phase3_seed_service import seed_opening_inventory, seed_phase3_benchmark_data
from tests.conftest import auth_headers_for


def test_opening_stock_and_mandatory_flour_benchmark(client, db_session):
    seed_benchmark_master_data(db_session)
    admin_headers = auth_headers_for(client, Role.ADMIN)

    # 1. Seed opening inventory only and verify exact opening balances
    created = seed_opening_inventory(db_session)
    assert created == 6

    rm_before = {
        row["sku"]: row
        for row in client.get("/api/v1/inventory/raw-materials", headers=admin_headers).json()["items"]
    }
    assert Decimal(rm_before["RM-FLOUR"]["available_quantity"]) == Decimal("100")
    assert Decimal(rm_before["RM-FLOUR"]["average_cost"]) == Decimal("42")
    assert Decimal(rm_before["RM-OIL"]["available_quantity"]) == Decimal("30")
    assert Decimal(rm_before["RM-SPICE"]["available_quantity"]) == Decimal("5")

    pkg_before = {
        row["sku"]: row
        for row in client.get("/api/v1/inventory/packaging", headers=admin_headers).json()["items"]
    }
    assert Decimal(pkg_before["PKG-POUCH-200"]["available_quantity"]) == Decimal("500")
    assert Decimal(pkg_before["PKG-CARTON"]["available_quantity"]) == Decimal("30")

    fg_before = {
        row["sku"]: row
        for row in client.get("/api/v1/inventory/finished-goods", headers=admin_headers).json()["items"]
    }
    assert Decimal(fg_before["MUR-200"]["available_quantity"]) == Decimal("50")

    # 2. Create draft purchase BENCHMARK-FLOUR-001 (60 kg at 45/kg) -> draft must NOT alter stock!
    sup_id = client.get("/api/v1/suppliers?search=Benchmark", headers=admin_headers).json()["items"][0]["id"]
    flour = db_session.scalar(select(StockItem).where(StockItem.sku == "RM-FLOUR"))
    draft_resp = client.post(
        "/api/v1/purchases",
        headers=admin_headers,
        json={
            "reference_number": "BENCHMARK-FLOUR-001",
            "supplier_id": sup_id,
            "purchase_date": date.today().isoformat(),
            "payment_status": "PAID",
            "items": [
                {
                    "stock_item_id": flour.id,
                    "unit_id": flour.base_unit_id,
                    "quantity": "60",
                    "unit_rate": "45",
                    "tax_rate": "0",
                }
            ],
        },
    )
    assert draft_resp.status_code == 201
    purchase_id = draft_resp.json()["id"]
    assert draft_resp.json()["status"] == "DRAFT"

    # Draft must leave Flour at 100 kg
    flour_still_100 = client.get(f"/api/v1/inventory/items/{flour.id}", headers=admin_headers).json()["item"]
    assert Decimal(flour_still_100["available_quantity"]) == Decimal("100")

    # 3. Post purchase receipt and assert mandatory benchmark calculations
    post_resp = client.post(f"/api/v1/purchases/{purchase_id}/post", headers=admin_headers)
    assert post_resp.status_code == 200
    assert post_resp.json()["status"] == "POSTED"

    flour_after = client.get(f"/api/v1/inventory/items/{flour.id}", headers=admin_headers).json()
    assert Decimal(flour_after["item"]["available_quantity"]) == Decimal("160")
    assert Decimal(flour_after["item"]["average_cost"]) == Decimal("43.125")
    assert Decimal(flour_after["item"]["stock_value"]) == Decimal("6900")
    assert flour_after["reconciled"] is True

    # 4. Duplicate purchase posting must be prevented (409 Conflict)
    dup_post = client.post(f"/api/v1/purchases/{purchase_id}/post", headers=admin_headers)
    assert dup_post.status_code == 409

    # 5. Ledger contains OPENING_STOCK + PURCHASE_RECEIPT and reconciles 100%
    ledger = client.get(f"/api/v1/inventory/ledger/{flour.id}", headers=admin_headers).json()
    movement_types = {e["movement_type"] for e in ledger["items"]}
    assert {"OPENING_STOCK", "PURCHASE_RECEIPT"}.issubset(movement_types)

    rec = client.get("/api/v1/inventory/reconcile", headers=admin_headers)
    assert rec.status_code == 200
    assert rec.json()["all_reconciled"] is True


def test_purchase_unit_conversion_and_reversal_cancellation(client, db_session):
    seed_benchmark_master_data(db_session)
    seed_opening_inventory(db_session)
    admin_headers = auth_headers_for(client, Role.ADMIN)

    sup_id = client.get("/api/v1/suppliers", headers=admin_headers).json()["items"][0]["id"]
    flour = db_session.scalar(select(StockItem).where(StockItem.sku == "RM-FLOUR"))
    gram_unit = db_session.scalar(select(Unit).where(Unit.symbol == "g"))

    # Purchase 5000 g of Flour at ₹0.05/g (= 5 kg @ ₹50/kg, subtotal ₹250)
    create_resp = client.post(
        "/api/v1/purchases",
        headers=admin_headers,
        json={
            "reference_number": "PO-GRAM-TEST-01",
            "supplier_id": sup_id,
            "purchase_date": date.today().isoformat(),
            "payment_status": "UNPAID",
            "items": [
                {
                    "stock_item_id": flour.id,
                    "unit_id": gram_unit.id,
                    "quantity": "5000",
                    "unit_rate": "0.05",
                    "tax_rate": "0",
                }
            ],
        },
    )
    assert create_resp.status_code == 201
    p_id = create_resp.json()["id"]
    assert Decimal(create_resp.json()["items"][0]["base_quantity"]) == Decimal("5")

    assert client.post(f"/api/v1/purchases/{p_id}/post", headers=admin_headers).status_code == 200
    after_post = client.get(f"/api/v1/inventory/items/{flour.id}", headers=admin_headers).json()["item"]
    assert Decimal(after_post["available_quantity"]) == Decimal("105")
    assert Decimal(after_post["stock_value"]) == Decimal("4450")

    # Cancel posted purchase -> traceable REVERSAL ledger entry restores 100 kg
    cancel_resp = client.post(
        f"/api/v1/purchases/{p_id}/cancel",
        headers=admin_headers,
        json={"reason": "Damaged bags returned to vendor"},
    )
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "CANCELLED"

    after_cancel = client.get(f"/api/v1/inventory/items/{flour.id}", headers=admin_headers).json()
    assert Decimal(after_cancel["item"]["available_quantity"]) == Decimal("100")
    assert Decimal(after_cancel["item"]["stock_value"]) == Decimal("4200")
    assert any(m["movement_type"] == "REVERSAL" for m in after_cancel["recent_movements"])


def test_stock_adjustment_negative_stock_and_immutability(client, db_session):
    seed_benchmark_master_data(db_session)
    seed_opening_inventory(db_session)
    admin_headers = auth_headers_for(client, Role.ADMIN)

    spice = db_session.scalar(select(StockItem).where(StockItem.sku == "RM-SPICE"))

    # Adjustment reducing Spice from 5 kg to 4 kg (approved)
    adj_resp = client.post(
        "/api/v1/inventory/adjustments",
        headers=admin_headers,
        json={
            "stock_item_id": spice.id,
            "physical_count": "4",
            "reason": "Humidity moisture loss during cycle count",
            "adjustment_date": date.today().isoformat(),
        },
    )
    assert adj_resp.status_code == 201
    adj_id = adj_resp.json()["id"]

    app_resp = client.post(
        f"/api/v1/inventory/adjustments/{adj_id}/approve",
        headers=admin_headers,
    )
    assert app_resp.status_code == 200
    assert app_resp.json()["status"] == "APPROVED"

    spice_after = client.get(f"/api/v1/inventory/items/{spice.id}", headers=admin_headers).json()
    assert Decimal(spice_after["item"]["available_quantity"]) == Decimal("4")
    assert spice_after["reconciled"] is True

    # Negative stock prevention: physical_count < 0 rejected by validation, and excessive outflow rejected
    neg_resp = client.post(
        "/api/v1/inventory/adjustments",
        headers=admin_headers,
        json={
            "stock_item_id": spice.id,
            "physical_count": "-1",
            "reason": "Invalid negative count",
            "adjustment_date": date.today().isoformat(),
        },
    )
    assert neg_resp.status_code == 422

    # Two concurrent/stale adjustments that would make stock negative on second approval
    adj_a = client.post(
        "/api/v1/inventory/adjustments",
        headers=admin_headers,
        json={
            "stock_item_id": spice.id,
            "physical_count": "1",
            "reason": "Write-off A (-3 kg)",
            "adjustment_date": date.today().isoformat(),
        },
    ).json()["id"]
    adj_b = client.post(
        "/api/v1/inventory/adjustments",
        headers=admin_headers,
        json={
            "stock_item_id": spice.id,
            "physical_count": "1",
            "reason": "Write-off B (-3 kg)",
            "adjustment_date": date.today().isoformat(),
        },
    ).json()["id"]
    assert client.post(f"/api/v1/inventory/adjustments/{adj_a}/approve", headers=admin_headers).status_code == 200
    # Second approval attempts -3 kg when only 1 kg remains -> must fail with 422!
    assert client.post(f"/api/v1/inventory/adjustments/{adj_b}/approve", headers=admin_headers).status_code == 422

    # Ledger immutability check: ORM delete/update raises ValueError
    ledger_row = db_session.scalar(select(StockLedger).limit(1))
    with pytest.raises(ValueError, match="append-only"):
        db_session.delete(ledger_row)
        db_session.flush()
    db_session.rollback()


def test_transaction_rollback_on_post_failure(client, db_session, monkeypatch):
    seed_benchmark_master_data(db_session)
    seed_opening_inventory(db_session)
    admin_headers = auth_headers_for(client, Role.ADMIN)

    sup_id = client.get("/api/v1/suppliers", headers=admin_headers).json()["items"][0]["id"]
    flour = db_session.scalar(select(StockItem).where(StockItem.sku == "RM-FLOUR"))
    oil = db_session.scalar(select(StockItem).where(StockItem.sku == "RM-OIL"))

    p = client.post(
        "/api/v1/purchases",
        headers=admin_headers,
        json={
            "reference_number": "PO-ROLLBACK-01",
            "supplier_id": sup_id,
            "purchase_date": date.today().isoformat(),
            "payment_status": "UNPAID",
            "items": [
                {"stock_item_id": flour.id, "unit_id": flour.base_unit_id, "quantity": "10", "unit_rate": "45", "tax_rate": "0"},
                {"stock_item_id": oil.id, "unit_id": oil.base_unit_id, "quantity": "5", "unit_rate": "140", "tax_rate": "0"},
            ],
        },
    ).json()

    call_count = 0
    real_apply = purchase_service.apply_stock_movement

    def failing_on_second_item(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise RuntimeError("Simulated DB crash mid-posting")
        return real_apply(*args, **kwargs)

    monkeypatch.setattr(purchase_service, "apply_stock_movement", failing_on_second_item)

    with pytest.raises(RuntimeError, match="Simulated DB crash"):
        client.post(f"/api/v1/purchases/{p['id']}/post", headers=admin_headers)

    # First item's movement must be rolled back completely!
    flour_bal = db_session.scalar(select(StockBalance).where(StockBalance.stock_item_id == flour.id))
    assert Decimal(flour_bal.available_quantity) == Decimal("100")
    purchase_row = db_session.get(Purchase, p["id"])
    assert purchase_row.status == PurchaseStatus.DRAFT


def test_phase3_seed_idempotency(db_session):
    seed_benchmark_master_data(db_session)
    first = seed_phase3_benchmark_data(db_session, post_benchmark_purchase=True)
    assert first["opening_entries"] == 6
    assert first["benchmark_purchases"] == 1

    second = seed_phase3_benchmark_data(db_session, post_benchmark_purchase=True)
    assert second == {"opening_entries": 0, "benchmark_purchases": 0}

    assert db_session.scalar(select(func.count(Purchase.id))) == 1
    flour = db_session.scalar(select(StockItem).where(StockItem.sku == "RM-FLOUR"))
    flour_bal = db_session.scalar(select(StockBalance).where(StockBalance.stock_item_id == flour.id))
    assert Decimal(flour_bal.available_quantity) == Decimal("160")
    assert Decimal(flour_bal.average_cost) == Decimal("43.125")
    assert Decimal(flour_bal.total_value) == Decimal("6900")
