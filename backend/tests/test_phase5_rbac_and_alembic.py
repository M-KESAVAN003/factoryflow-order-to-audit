from pathlib import Path

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import create_engine, inspect, select

from app.core.permissions import Role
from app.models.customer import Customer
from app.models.product import Product
from app.services.master_seed_service import seed_benchmark_master_data
from app.services.phase3_seed_service import seed_phase3_benchmark_data
from app.services.phase4_seed_service import seed_benchmark_bom
from tests.conftest import auth_headers_for


@pytest.mark.parametrize(
    "role,so_r,so_c,so_app,inv_r,inv_w,dsp_r,dsp_w",
    [
        (Role.ADMIN, 200, 201, 422, 200, 422, 200, 422),
        (Role.ORDER_MANAGER, 200, 201, 403, 403, 403, 403, 403),
        (Role.FLOOR_SUPERVISOR, 403, 403, 403, 403, 403, 403, 403),
        (Role.QA_INSPECTOR, 403, 403, 403, 403, 403, 403, 403),
        (Role.AUDITOR, 200, 403, 403, 200, 403, 200, 403),
    ],
)
def test_phase5_role_permissions_matrix(
    client,
    db_session,
    role,
    so_r,
    so_c,
    so_app,
    inv_r,
    inv_w,
    dsp_r,
    dsp_w,
):
    seed_benchmark_master_data(db_session)
    seed_phase3_benchmark_data(db_session, post_benchmark_purchase=True)
    seed_benchmark_bom(db_session)

    admin_headers = auth_headers_for(client, Role.ADMIN)
    sales_headers = auth_headers_for(client, Role.ORDER_MANAGER)
    headers = auth_headers_for(client, role)

    murukku = db_session.scalar(select(Product).where(Product.sku == "MUR-200"))
    retailer_a = db_session.scalar(select(Customer).where(Customer.gstin == "33RETLA0001A1Z5"))

    # Seed one submitted order from salesman for permission checks
    sample_order = client.post(
        "/api/v1/orders",
        headers=sales_headers,
        json={"customer_id": retailer_a.id, "items": [{"product_id": murukku.id, "quantity": "100"}]},
    ).json()

    assert client.get("/api/v1/orders", headers=headers).status_code == so_r
    assert client.get("/api/v1/orders/overview", headers=headers).status_code == so_r
    assert client.get("/api/v1/invoices", headers=headers).status_code == inv_r
    assert client.get("/api/v1/dispatches", headers=headers).status_code == dsp_r

    create_order = client.post(
        "/api/v1/orders",
        headers=headers,
        json={"customer_id": retailer_a.id, "items": [{"product_id": murukku.id, "quantity": "5"}]},
    )
    assert create_order.status_code == so_c

    # Note: sample_order requests 100 while opening stock is 50 packets -> Admin gets 422 (permitted), others 403
    approve_resp = client.post(f"/api/v1/orders/{sample_order['id']}/approve", headers=headers)
    assert approve_resp.status_code == so_app

    reject_resp = client.post(
        f"/api/v1/orders/{sample_order['id']}/reject",
        headers=headers,
        json={"reason": "Role auth check"},
    )
    assert reject_resp.status_code == (200 if role == Role.ADMIN else 403)

    inv_create = client.post(
        "/api/v1/invoices",
        headers=headers,
        json={"sales_order_id": sample_order["id"]},
    )
    assert inv_create.status_code == inv_w

    dsp_create = client.post(
        "/api/v1/dispatches",
        headers=headers,
        json={"sales_order_id": sample_order["id"]},
    )
    assert dsp_create.status_code == dsp_w

    # Production supervisor retains read access to finished-goods inventory
    if role == Role.FLOOR_SUPERVISOR:
        assert client.get("/api/v1/inventory/finished-goods", headers=headers).status_code == 200
        # Confirm admin still works after matrix
        assert client.get("/api/v1/orders", headers=admin_headers).status_code == 200


def test_alembic_includes_phase5_tables(tmp_path):
    db_file = tmp_path / "alembic_phase5.db"
    backend_dir = Path(__file__).resolve().parents[1]
    alembic_cfg = Config(str(backend_dir / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(backend_dir / "alembic"))
    alembic_cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_file.as_posix()}")

    command.upgrade(alembic_cfg, "head")

    engine = create_engine(f"sqlite:///{db_file.as_posix()}")
    tables = set(inspect(engine).get_table_names())
    assert {
        "sales_orders",
        "sales_order_items",
        "invoices",
        "invoice_items",
        "credit_notes",
        "dispatches",
        "dispatch_items",
    }.issubset(tables)
