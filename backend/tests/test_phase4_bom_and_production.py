from datetime import date
from decimal import Decimal
import pytest
from sqlalchemy import func, select

from app.core.permissions import Role
from app.models.bom import BomHeader
from app.models.inventory import StockBalance
from app.models.product import Product
from app.models.production import ProductionRun, ProductionStatus
from app.models.stock_item import StockItem
from app.models.unit import Unit
from app.services import production_service
from app.services.master_seed_service import seed_benchmark_master_data
from app.services.phase3_seed_service import seed_phase3_benchmark_data
from app.services.phase4_seed_service import seed_benchmark_bom
from tests.conftest import auth_headers_for


def _setup_full_benchmark_base(db_session):
    seed_benchmark_master_data(db_session)
    seed_phase3_benchmark_data(db_session, post_benchmark_purchase=True)
    seed_benchmark_bom(db_session)


def test_bom_creation_versioning_and_historical_preservation(client, db_session):
    _setup_full_benchmark_base(db_session)
    admin_headers = auth_headers_for(client, Role.ADMIN)

    murukku = db_session.scalar(select(Product).where(Product.sku == "MUR-200"))
    boms = client.get(f"/api/v1/boms?product_id={murukku.id}", headers=admin_headers).json()["items"]
    assert len(boms) == 1
    bom_v1 = boms[0]
    assert bom_v1["version_number"] == 1
    assert bom_v1["is_active"] is True
    assert Decimal(bom_v1["expected_output"]) == Decimal("200")

    # Create production run pinned to BOM v1
    run_v1 = client.post(
        "/api/v1/production",
        headers=admin_headers,
        json={
            "order_number": "PRD-HIST-001",
            "product_id": murukku.id,
            "batch_number": "B-001",
            "production_date": date.today().isoformat(),
            "planned_batches": "1",
        },
    ).json()
    assert run_v1["bom_version_snapshot"] == 1

    # Create and activate BOM v2 (220 packets expected output)
    flour = db_session.scalar(select(StockItem).where(StockItem.sku == "RM-FLOUR"))
    bom_v2 = client.post(
        "/api/v1/boms",
        headers=admin_headers,
        json={
            "product_id": murukku.id,
            "batch_size": "1",
            "expected_output": "220",
            "output_unit_id": murukku.unit_id,
            "effective_date": date.today().isoformat(),
            "activate": True,
            "lines": [
                {"stock_item_id": flour.id, "standard_quantity": "42", "unit_id": flour.base_unit_id}
            ],
        },
    )
    assert bom_v2.status_code == 201
    v2_data = bom_v2.json()
    assert v2_data["version_number"] == 2
    assert v2_data["is_active"] is True

    # Version history returns both v2 and v1; v1 is now INACTIVE
    versions = client.get(f"/api/v1/boms/{v2_data['id']}/versions", headers=admin_headers).json()
    assert [v["version_number"] for v in versions] == [2, 1]
    assert versions[1]["is_active"] is False

    # Existing run_v1 still preserves BOM v1 expected output (200) and 5 planned materials
    run_v1_after = client.get(f"/api/v1/production/{run_v1['id']}", headers=admin_headers).json()
    assert run_v1_after["bom_version_snapshot"] == 1
    assert Decimal(run_v1_after["expected_output"]) == Decimal("200")
    assert len(run_v1_after["materials"]) == 5


def test_mandatory_benchmark_production_run_and_variances(client, db_session):
    _setup_full_benchmark_base(db_session)
    sup_headers = auth_headers_for(client, Role.FLOOR_SUPERVISOR)
    admin_headers = auth_headers_for(client, Role.ADMIN)

    murukku = db_session.scalar(select(Product).where(Product.sku == "MUR-200"))
    items_by_sku = {
        si.sku: si for si in db_session.scalars(select(StockItem)).all()
    }

    # Verify pre-production balances
    pre_inv = {
        r["sku"]: Decimal(r["available_quantity"])
        for r in (
            client.get("/api/v1/inventory/raw-materials", headers=admin_headers).json()["items"]
            + client.get("/api/v1/inventory/packaging", headers=admin_headers).json()["items"]
            + client.get("/api/v1/inventory/finished-goods", headers=admin_headers).json()["items"]
        )
    }
    assert pre_inv["RM-FLOUR"] == Decimal("160")
    assert pre_inv["RM-OIL"] == Decimal("30")
    assert pre_inv["RM-SPICE"] == Decimal("5")
    assert pre_inv["PKG-POUCH-200"] == Decimal("500")
    assert pre_inv["PKG-CARTON"] == Decimal("30")
    assert pre_inv["MUR-200"] == Decimal("50")

    # 1. Create & start production run
    create_resp = client.post(
        "/api/v1/production",
        headers=sup_headers,
        json={
            "order_number": "BENCHMARK-PRD-001",
            "product_id": murukku.id,
            "batch_number": "MUR-BATCH-01",
            "production_date": date.today().isoformat(),
            "planned_batches": "1",
        },
    )
    assert create_resp.status_code == 201
    run_id = create_resp.json()["id"]
    assert Decimal(create_resp.json()["expected_output"]) == Decimal("200")

    assert client.post(f"/api/v1/production/{run_id}/start", headers=sup_headers).status_code == 200

    # 2. Record actual material & packaging consumption
    consume_resp = client.post(
        f"/api/v1/production/{run_id}/consume",
        headers=sup_headers,
        json={
            "materials": [
                {"stock_item_id": items_by_sku["RM-FLOUR"].id, "actual_quantity": "40", "damaged_quantity": "0"},
                {"stock_item_id": items_by_sku["RM-OIL"].id, "actual_quantity": "10.5", "damaged_quantity": "0"},
                {"stock_item_id": items_by_sku["RM-SPICE"].id, "actual_quantity": "1.2", "damaged_quantity": "0"},
                {"stock_item_id": items_by_sku["PKG-POUCH-200"].id, "actual_quantity": "188", "damaged_quantity": "6"},
                {"stock_item_id": items_by_sku["PKG-CARTON"].id, "actual_quantity": "9", "damaged_quantity": "0"},
            ]
        },
    )
    assert consume_resp.status_code == 200
    assert Decimal(consume_resp.json()["damaged_pouches"]) == Decimal("6")

    # 3. Record actual output (188 good packets, 9 cartons used -> 8 unpacked warning)
    out_resp = client.post(
        f"/api/v1/production/{run_id}/output",
        headers=sup_headers,
        json={"good_quantity": "188", "damaged_packets": "0", "cartons_used": "9"},
    )
    assert out_resp.status_code == 200
    out_data = out_resp.json()
    assert "9 cartons hold 180 packets" in out_data["packaging_warning"]
    assert "8 packets remain unpacked" in out_data["packaging_warning"]

    # Record wastage log entry
    w_resp = client.post(
        f"/api/v1/production/{run_id}/wastage",
        headers=sup_headers,
        json={
            "stock_item_id": items_by_sku["PKG-POUCH-200"].id,
            "wastage_type": "DAMAGED_POUCH",
            "quantity": "6",
            "reason": "Heat-seal seam tear during packing",
        },
    )
    assert w_resp.status_code == 200

    # 4. Complete and post production run
    assert client.post(f"/api/v1/production/{run_id}/complete", headers=sup_headers).status_code == 200
    post_resp = client.post(f"/api/v1/production/{run_id}/post", headers=sup_headers)
    assert post_resp.status_code == 200
    assert post_resp.json()["status"] == "POSTED"

    # 5. Prevent duplicate production posting (409 Conflict)
    dup_post = client.post(f"/api/v1/production/{run_id}/post", headers=sup_headers)
    assert dup_post.status_code == 409

    # 6. Assert post-production benchmark inventory balances
    post_inv = {
        r["sku"]: Decimal(r["available_quantity"])
        for r in (
            client.get("/api/v1/inventory/raw-materials", headers=admin_headers).json()["items"]
            + client.get("/api/v1/inventory/packaging", headers=admin_headers).json()["items"]
            + client.get("/api/v1/inventory/finished-goods", headers=admin_headers).json()["items"]
        )
    }
    assert post_inv["RM-FLOUR"] == Decimal("120")
    assert post_inv["RM-OIL"] == Decimal("19.5")
    assert post_inv["RM-SPICE"] == Decimal("3.8")
    assert post_inv["PKG-POUCH-200"] == Decimal("306")
    assert post_inv["PKG-CARTON"] == Decimal("21")
    assert post_inv["MUR-200"] == Decimal("238")

    # 7. Assert exact variance calculations & statuses
    var_report = client.get(f"/api/v1/production/{run_id}/variance", headers=sup_headers).json()
    assert Decimal(var_report["yield_variance_pct"]) == Decimal("-6")
    assert var_report["yield_status"] == "RED"
    assert var_report["yield_exceeds_tolerance"] is True

    var_by_sku = {m["sku"]: m for m in var_report["materials"]}
    assert Decimal(var_by_sku["RM-OIL"]["variance_pct"]) == Decimal("5")
    assert var_by_sku["RM-OIL"]["status"] == "RED"
    assert var_by_sku["RM-OIL"]["exceeds_tolerance"] is True

    # Pouches at -3% boundary -> NOT flagged as exceeding 3% tolerance
    assert Decimal(var_by_sku["PKG-POUCH-200"]["variance_pct"]) == Decimal("-3")
    assert var_by_sku["PKG-POUCH-200"]["status"] == "ORANGE"
    assert var_by_sku["PKG-POUCH-200"]["exceeds_tolerance"] is False

    # Cartons at -10% -> flagged RED
    assert Decimal(var_by_sku["PKG-CARTON"]["variance_pct"]) == Decimal("-10")
    assert var_by_sku["PKG-CARTON"]["status"] == "RED"
    assert var_by_sku["PKG-CARTON"]["exceeds_tolerance"] is True

    # 8. Assert StockLedger links to PRODUCTION_RUN and reconciles 100%
    ledger = client.get(
        "/api/v1/inventory/ledger?reference_doc_id=BENCHMARK-PRD-001", headers=admin_headers
    ).json()
    assert ledger["total"] == 6  # 5 PRODUCTION_ISSUE + 1 PRODUCTION_OUTPUT
    rec = client.get("/api/v1/inventory/reconcile", headers=admin_headers).json()
    assert rec["all_reconciled"] is True


def test_bom_unit_conversion_negative_stock_and_rollback(client, db_session, monkeypatch):
    _setup_full_benchmark_base(db_session)
    admin_headers = auth_headers_for(client, Role.ADMIN)

    murukku = db_session.scalar(select(Product).where(Product.sku == "MUR-200"))
    flour = db_session.scalar(select(StockItem).where(StockItem.sku == "RM-FLOUR"))
    gram_unit = db_session.scalar(select(Unit).where(Unit.symbol == "g"))

    # Create a BOM using grams (5000 g = 5 kg) to test unit conversion inside BOM & production
    bom_gram = client.post(
        "/api/v1/boms",
        headers=admin_headers,
        json={
            "product_id": murukku.id,
            "batch_size": "1",
            "expected_output": "25",
            "output_unit_id": murukku.unit_id,
            "effective_date": date.today().isoformat(),
            "activate": True,
            "lines": [
                {"stock_item_id": flour.id, "standard_quantity": "5000", "unit_id": gram_unit.id}
            ],
        },
    ).json()
    assert Decimal(bom_gram["lines"][0]["base_quantity"]) == Decimal("5")

    # Negative stock prevention: try consuming 500000 g (500 kg > 160 kg available)
    run = client.post(
        "/api/v1/production",
        headers=admin_headers,
        json={
            "order_number": "PRD-NEG-01",
            "product_id": murukku.id,
            "bom_id": bom_gram["id"],
            "batch_number": "B-NEG",
            "production_date": date.today().isoformat(),
            "planned_batches": "1",
        },
    ).json()
    client.post(f"/api/v1/production/{run['id']}/start", headers=admin_headers)
    client.post(
        f"/api/v1/production/{run['id']}/consume",
        headers=admin_headers,
        json={"materials": [{"stock_item_id": flour.id, "actual_quantity": "500000", "damaged_quantity": "0"}]},
    )
    client.post(
        f"/api/v1/production/{run['id']}/output",
        headers=admin_headers,
        json={"good_quantity": "25", "damaged_packets": "0", "cartons_used": "1"},
    )
    client.post(f"/api/v1/production/{run['id']}/complete", headers=admin_headers)
    neg_post = client.post(f"/api/v1/production/{run['id']}/post", headers=admin_headers)
    assert neg_post.status_code == 422

    # Rollback test: simulate error on finished-goods receipt after material issue
    run_rb = client.post(
        "/api/v1/production",
        headers=admin_headers,
        json={
            "order_number": "PRD-RB-01",
            "product_id": murukku.id,
            "bom_id": bom_gram["id"],
            "batch_number": "B-RB",
            "production_date": date.today().isoformat(),
            "planned_batches": "1",
        },
    ).json()
    client.post(f"/api/v1/production/{run_rb['id']}/start", headers=admin_headers)
    client.post(
        f"/api/v1/production/{run_rb['id']}/consume",
        headers=admin_headers,
        json={"materials": [{"stock_item_id": flour.id, "actual_quantity": "5000", "damaged_quantity": "0"}]},
    )
    client.post(
        f"/api/v1/production/{run_rb['id']}/output",
        headers=admin_headers,
        json={"good_quantity": "25", "damaged_packets": "0", "cartons_used": "1"},
    )
    client.post(f"/api/v1/production/{run_rb['id']}/complete", headers=admin_headers)

    real_apply = production_service.apply_stock_movement
    calls = 0

    def fail_on_output(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("Simulated crash before finished-good receipt")
        return real_apply(*args, **kwargs)

    monkeypatch.setattr(production_service, "apply_stock_movement", fail_on_output)
    with pytest.raises(RuntimeError, match="Simulated crash"):
        client.post(f"/api/v1/production/{run_rb['id']}/post", headers=admin_headers)

    # Flour must remain untouched at 160 kg and run must remain COMPLETED
    flour_bal = db_session.scalar(select(StockBalance).where(StockBalance.stock_item_id == flour.id))
    assert Decimal(flour_bal.available_quantity) == Decimal("160")
    assert db_session.get(ProductionRun, run_rb["id"]).status == ProductionStatus.COMPLETED


def test_phase4_seed_idempotency(db_session):
    seed_benchmark_master_data(db_session)
    seed_phase3_benchmark_data(db_session, post_benchmark_purchase=True)
    first = seed_benchmark_bom(db_session)
    assert first == {"boms_created": 1}

    second = seed_benchmark_bom(db_session)
    assert second == {"boms_created": 0}
    assert db_session.scalar(select(func.count(BomHeader.id))) == 1
