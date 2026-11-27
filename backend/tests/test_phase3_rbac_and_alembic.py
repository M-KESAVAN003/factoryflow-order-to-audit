from datetime import date
from decimal import Decimal
from pathlib import Path

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import create_engine, inspect, select

from app.core.permissions import Role
from app.models.stock_item import StockItem
from app.services.master_seed_service import seed_benchmark_master_data
from app.services.phase3_seed_service import seed_phase3_benchmark_data
from tests.conftest import auth_headers_for


@pytest.mark.parametrize(
    "role,inv_read,pur_read,pur_write,adj_write",
    [
        (Role.ADMIN, 200, 200, 201, 201),
        (Role.FLOOR_SUPERVISOR, 200, 200, 201, 201),
        (Role.AUDITOR, 200, 200, 403, 403),
        (Role.ORDER_MANAGER, 403, 403, 403, 403),
        (Role.QA_INSPECTOR, 403, 403, 403, 403),
    ],
)
def test_phase3_role_permission_enforcement(
    client,
    db_session,
    role,
    inv_read,
    pur_read,
    pur_write,
    adj_write,
):
    seed_benchmark_master_data(db_session)
    seed_phase3_benchmark_data(db_session, post_benchmark_purchase=True)
    headers = auth_headers_for(client, role)

    assert client.get("/api/v1/inventory/summary", headers=headers).status_code == inv_read
    assert client.get("/api/v1/inventory/raw-materials", headers=headers).status_code == inv_read
    assert client.get("/api/v1/inventory/packaging", headers=headers).status_code == inv_read
    assert client.get("/api/v1/inventory/finished-goods", headers=headers).status_code == inv_read
    assert client.get("/api/v1/inventory/ledger", headers=headers).status_code == inv_read
    assert client.get("/api/v1/inventory/alerts", headers=headers).status_code == inv_read
    assert client.get("/api/v1/purchases", headers=headers).status_code == pur_read

    flour = db_session.scalar(select(StockItem).where(StockItem.sku == "RM-FLOUR"))
    admin_headers = auth_headers_for(client, Role.ADMIN)
    sup_id = client.get("/api/v1/suppliers", headers=admin_headers).json()["items"][0]["id"]

    p_resp = client.post(
        "/api/v1/purchases",
        headers=headers,
        json={
            "reference_number": f"PO-PERM-{role.value.upper()}",
            "supplier_id": sup_id,
            "purchase_date": date.today().isoformat(),
            "payment_status": "UNPAID",
            "items": [
                {
                    "stock_item_id": flour.id,
                    "unit_id": flour.base_unit_id,
                    "quantity": "1",
                    "unit_rate": "40",
                    "tax_rate": "0",
                }
            ],
        },
    )
    assert p_resp.status_code == pur_write

    a_resp = client.post(
        "/api/v1/inventory/adjustments",
        headers=headers,
        json={
            "stock_item_id": flour.id,
            "physical_count": "159",
            "reason": "Permission verification check",
            "adjustment_date": date.today().isoformat(),
        },
    )
    assert a_resp.status_code == adj_write


def test_purchase_exports_and_low_stock_alerts(client, db_session):
    seed_benchmark_master_data(db_session)
    seed_phase3_benchmark_data(db_session, post_benchmark_purchase=True)
    headers = auth_headers_for(client, Role.AUDITOR)

    csv_resp = client.get("/api/v1/purchases/export?format=csv", headers=headers)
    assert csv_resp.status_code == 200
    assert "BENCHMARK-FLOUR-001" in csv_resp.text

    pdf_resp = client.get("/api/v1/purchases/export?format=pdf", headers=headers)
    assert pdf_resp.status_code == 200
    assert pdf_resp.content.startswith(b"%PDF-1.4")

    alerts_resp = client.get("/api/v1/inventory/alerts?category=RAW_MATERIAL", headers=headers)
    assert alerts_resp.status_code == 200
    assert alerts_resp.json()["total"] == 3
    for row in alerts_resp.json()["items"]:
        assert row["stock_status"] in {"GREEN", "ORANGE", "RED"}
        assert Decimal(row["available_quantity"]) >= Decimal("0")


def test_alembic_includes_phase3_tables(tmp_path):
    db_file = tmp_path / "alembic_phase3.db"
    backend_dir = Path(__file__).resolve().parents[1]
    alembic_cfg = Config(str(backend_dir / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(backend_dir / "alembic"))
    alembic_cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_file.as_posix()}")

    command.upgrade(alembic_cfg, "head")

    engine = create_engine(f"sqlite:///{db_file.as_posix()}")
    tables = set(inspect(engine).get_table_names())
    assert {
        "stock_balances",
        "stock_ledger",
        "stock_adjustments",
        "purchases",
        "purchase_items",
    }.issubset(tables)
    engine.dispose()
