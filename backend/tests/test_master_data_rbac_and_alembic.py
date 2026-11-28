from pathlib import Path

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import create_engine, inspect

from app.core.permissions import Role
from app.services.master_seed_service import seed_benchmark_master_data
from tests.conftest import auth_headers_for


@pytest.mark.parametrize(
    "role,prod_r,prod_w,stock_r,sup_r,cust_r,unit_r,unit_w",
    [
        (Role.ADMIN, 200, 201, 200, 200, 200, 200, 201),
        (Role.ORDER_MANAGER, 200, 403, 403, 403, 200, 200, 403),
        (Role.FLOOR_SUPERVISOR, 200, 403, 200, 200, 403, 200, 403),
        (Role.QA_INSPECTOR, 200, 403, 200, 200, 403, 200, 403),
        (Role.AUDITOR, 200, 403, 200, 200, 200, 200, 403),
        (Role.OWNER, 200, 403, 200, 200, 200, 200, 403),
    ],
)
def test_phase2_role_permissions_matrix(
    client,
    db_session,
    role,
    prod_r,
    prod_w,
    stock_r,
    sup_r,
    cust_r,
    unit_r,
    unit_w,
):
    seed_benchmark_master_data(db_session)
    headers = auth_headers_for(client, role)

    assert client.get("/api/v1/products", headers=headers).status_code == prod_r
    assert client.get("/api/v1/raw-materials", headers=headers).status_code == stock_r
    assert client.get("/api/v1/packaging-materials", headers=headers).status_code == stock_r
    assert client.get("/api/v1/suppliers", headers=headers).status_code == sup_r
    assert client.get("/api/v1/customers", headers=headers).status_code == cust_r
    assert client.get("/api/v1/units", headers=headers).status_code == unit_r

    units = client.get("/api/v1/units", headers=headers).json()["items"]
    pkt_id = units[0]["id"]

    create_prod = client.post(
        "/api/v1/products",
        headers=headers,
        json={
            "name": f"Role Test {role.value}",
            "sku": f"RT-{role.value.upper()}",
            "category": "Snacks",
            "pack_size": "100 g",
            "selling_price": "25.00",
            "gst_rate": "5.00",
            "hsn_code": "19059090",
            "unit_id": pkt_id,
        },
    )
    assert create_prod.status_code == prod_w

    create_unit = client.post(
        "/api/v1/units",
        headers=headers,
        json={"name": f"Unit-{role.value}", "symbol": f"u{role.value[:3]}", "dimension": "count"},
    )
    assert create_unit.status_code == unit_w


def test_order_manager_only_sees_assigned_customers_and_active_products(client, db_session):
    seed_benchmark_master_data(db_session)
    admin_headers = auth_headers_for(client, Role.ADMIN)
    sales_headers = auth_headers_for(client, Role.ORDER_MANAGER)

    # Create an unassigned customer and deactivate Murukku's sibling product
    unassigned = client.post(
        "/api/v1/customers",
        headers=admin_headers,
        json={
            "name": "Unassigned Shop",
            "customer_type": "Retailer",
            "gstin": "33UNASG0009Z1Z5",
            "phone": "+91-44-9999-0000",
            "address": "10 Side Lane",
            "city": "Coimbatore",
            "state": "Tamil Nadu",
            "state_code": "33",
            "credit_limit": "10000.00",
        },
    )
    assert unassigned.status_code == 201
    unassigned_id = unassigned.json()["id"]

    # Order manager sees only the 2 assigned benchmark customers, and gets 403 on unassigned customer
    sales_customers = client.get("/api/v1/customers", headers=sales_headers)
    assert sales_customers.status_code == 200
    assert sales_customers.json()["total"] == 2
    assert client.get(f"/api/v1/customers/{unassigned_id}", headers=sales_headers).status_code == 403

    # Create inactive product -> hidden from order_manager
    pkt_id = next(
        u["id"] for u in client.get("/api/v1/units", headers=admin_headers).json()["items"] if u["symbol"] == "packet"
    )
    inactive_prod = client.post(
        "/api/v1/products",
        headers=admin_headers,
        json={
            "name": "Discontinued Mix",
            "sku": "DISC-01",
            "category": "Snacks",
            "pack_size": "200 g",
            "selling_price": "30.00",
            "gst_rate": "5.00",
            "hsn_code": "19059090",
            "unit_id": pkt_id,
            "is_active": False,
        },
    )
    assert inactive_prod.status_code == 201
    sales_products = client.get("/api/v1/products", headers=sales_headers)
    assert sales_products.status_code == 200
    skus = {p["sku"] for p in sales_products.json()["items"]}
    assert "DISC-01" not in skus
    assert "MUR-200" in skus


def test_alembic_upgrade_and_downgrade_execution(tmp_path):
    db_file = tmp_path / "alembic_verify.db"
    backend_dir = Path(__file__).resolve().parents[1]
    alembic_cfg = Config(str(backend_dir / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(backend_dir / "alembic"))
    alembic_cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_file.as_posix()}")

    command.upgrade(alembic_cfg, "head")

    engine = create_engine(f"sqlite:///{db_file.as_posix()}")
    tables = set(inspect(engine).get_table_names())
    assert {
        "users",
        "audit_logs",
        "units",
        "unit_conversions",
        "stock_items",
        "products",
        "suppliers",
        "customers",
    }.issubset(tables)
    engine.dispose()

    command.downgrade(alembic_cfg, "base")
    engine_after = create_engine(f"sqlite:///{db_file.as_posix()}")
    tables_after = set(inspect(engine_after).get_table_names())
    assert "products" not in tables_after
    assert "users" not in tables_after
    engine_after.dispose()
