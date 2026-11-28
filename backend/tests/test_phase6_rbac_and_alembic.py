from pathlib import Path

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import create_engine, inspect, select

from app.core.permissions import Role
from app.models.customer import Customer
from app.models.product import Product
from app.models.user import User
from app.schemas.bom_production import ProductionRunCreate
from app.services.master_seed_service import seed_benchmark_master_data
from app.services.phase3_seed_service import seed_phase3_benchmark_data
from app.services.phase4_seed_service import seed_benchmark_bom
from app.services.production_service import create_production_run
from tests.conftest import auth_headers_for


@pytest.mark.parametrize(
    "role,cost_r,exp_w,pay_r,pay_w,rec_r",
    [
        (Role.ADMIN, 200, 201, 200, 201, 200),
        (Role.FLOOR_SUPERVISOR, 200, 201, 403, 403, 403),
        (Role.AUDITOR, 200, 403, 200, 403, 200),
        (Role.OWNER, 200, 403, 200, 403, 200),
        (Role.ORDER_MANAGER, 403, 403, 403, 403, 403),
        (Role.QA_INSPECTOR, 403, 403, 403, 403, 403),
    ],
)
def test_phase6_role_permissions_matrix(
    client,
    db_session,
    role,
    cost_r,
    exp_w,
    pay_r,
    pay_w,
    rec_r,
):
    seed_benchmark_master_data(db_session)
    seed_phase3_benchmark_data(db_session, post_benchmark_purchase=True)
    seed_benchmark_bom(db_session)

    sup = db_session.scalar(select(User).where(User.role == Role.FLOOR_SUPERVISOR))
    murukku = db_session.scalar(select(Product).where(Product.sku == "MUR-200"))
    retailer_a = db_session.scalar(select(Customer).where(Customer.gstin == "33RETLA0001A1Z5"))
    run = create_production_run(
        db_session,
        ProductionRunCreate(
            order_number="PRD-PERM-P6",
            product_id=murukku.id,
            batch_number="B-PERM-6",
            production_date=__import__("datetime").date.today(),
            planned_batches=__import__("decimal").Decimal("1"),
        ),
        actor=sup,
    )

    headers = auth_headers_for(client, role)
    assert client.get("/api/v1/costing/production", headers=headers).status_code == cost_r
    assert client.get(f"/api/v1/costing/production/{run.id}", headers=headers).status_code == cost_r
    assert client.get("/api/v1/payments", headers=headers).status_code == pay_r
    assert client.get("/api/v1/receivables", headers=headers).status_code == rec_r
    assert client.get("/api/v1/receivables/ageing", headers=headers).status_code == rec_r
    assert client.get(f"/api/v1/customers/{retailer_a.id}/ledger", headers=headers).status_code == rec_r
    assert client.get(f"/api/v1/customers/{retailer_a.id}/statement", headers=headers).status_code == rec_r

    exp_resp = client.post(
        f"/api/v1/production/{run.id}/expenses",
        headers=headers,
        json={"category": "LABOUR", "description": "RBAC expense", "amount": "500.00"},
    )
    assert exp_resp.status_code == exp_w

    pay_resp = client.post(
        "/api/v1/payments",
        headers=headers,
        json={
            "payment_reference": f"PAY-RBAC-{role.value.upper()}",
            "customer_id": retailer_a.id,
            "payment_method": "CASH",
            "amount_received": "250.00",
        },
    )
    assert pay_resp.status_code == pay_w


def test_alembic_includes_phase6_tables(tmp_path):
    db_file = tmp_path / "alembic_phase6.db"
    backend_dir = Path(__file__).resolve().parents[1]
    alembic_cfg = Config(str(backend_dir / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(backend_dir / "alembic"))
    alembic_cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_file.as_posix()}")

    command.upgrade(alembic_cfg, "head")

    engine = create_engine(f"sqlite:///{db_file.as_posix()}")
    tables = set(inspect(engine).get_table_names())
    assert {
        "production_expenses",
        "payments",
        "payment_allocations",
    }.issubset(tables)
