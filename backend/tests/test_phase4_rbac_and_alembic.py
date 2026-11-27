from datetime import date
from pathlib import Path

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import create_engine, inspect, select

from app.core.permissions import Role
from app.models.product import Product
from app.models.stock_item import StockItem
from app.services.master_seed_service import seed_benchmark_master_data
from app.services.phase3_seed_service import seed_phase3_benchmark_data
from app.services.phase4_seed_service import seed_benchmark_bom
from tests.conftest import auth_headers_for


@pytest.mark.parametrize(
    "role,bom_r,bom_w,prod_r,prod_w",
    [
        (Role.ADMIN, 200, 201, 200, 201),
        (Role.FLOOR_SUPERVISOR, 200, 403, 200, 201),
        (Role.QA_INSPECTOR, 200, 403, 200, 403),
        (Role.AUDITOR, 200, 403, 200, 403),
        (Role.ORDER_MANAGER, 403, 403, 403, 403),
    ],
)
def test_phase4_role_permissions_matrix(
    client,
    db_session,
    role,
    bom_r,
    bom_w,
    prod_r,
    prod_w,
):
    seed_benchmark_master_data(db_session)
    seed_phase3_benchmark_data(db_session, post_benchmark_purchase=True)
    seed_benchmark_bom(db_session)
    headers = auth_headers_for(client, role)

    assert client.get("/api/v1/boms", headers=headers).status_code == bom_r
    assert client.get("/api/v1/production", headers=headers).status_code == prod_r
    assert client.get("/api/v1/production/dashboard", headers=headers).status_code == prod_r
    assert client.get("/api/v1/production/variance/summary", headers=headers).status_code == prod_r

    murukku = db_session.scalar(select(Product).where(Product.sku == "MUR-200"))
    pouch = db_session.scalar(select(StockItem).where(StockItem.sku == "PKG-POUCH-200"))
    bom_create = client.post(
        "/api/v1/boms",
        headers=headers,
        json={
            "product_id": murukku.id,
            "batch_size": "1",
            "expected_output": "200",
            "output_unit_id": murukku.unit_id,
            "effective_date": date.today().isoformat(),
            "activate": False,
            "lines": [
                {
                    "stock_item_id": pouch.id,
                    "standard_quantity": "200",
                    "unit_id": pouch.base_unit_id,
                }
            ],
        },
    )
    assert bom_create.status_code == bom_w

    run_create = client.post(
        "/api/v1/production",
        headers=headers,
        json={
            "order_number": f"PRD-PERM-{role.value.upper()}",
            "product_id": murukku.id,
            "batch_number": "B-PERM",
            "production_date": date.today().isoformat(),
            "planned_batches": "1",
        },
    )
    assert run_create.status_code == prod_w


def test_alembic_includes_phase4_tables(tmp_path):
    db_file = tmp_path / "alembic_phase4.db"
    backend_dir = Path(__file__).resolve().parents[1]
    alembic_cfg = Config(str(backend_dir / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(backend_dir / "alembic"))
    alembic_cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_file.as_posix()}")

    command.upgrade(alembic_cfg, "head")

    engine = create_engine(f"sqlite:///{db_file.as_posix()}")
    tables = set(inspect(engine).get_table_names())
    assert {
        "bom_headers",
        "bom_lines",
        "production_runs",
        "production_materials",
        "production_outputs",
        "production_wastage",
    }.issubset(tables)
    engine.dispose()
