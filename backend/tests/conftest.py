from typing import Dict, Generator

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.permissions import Role
from app.main import create_app
from app.services.user_service import seed_default_users

SEED_PASSWORD = "FactoryFlow!2026"

ROLE_EMAILS: Dict[Role, str] = {
    Role.ADMIN: "admin@factoryflow.io",
    Role.ORDER_MANAGER: "orders@factoryflow.io",
    Role.FLOOR_SUPERVISOR: "floor@factoryflow.io",
    Role.QA_INSPECTOR: "qa@factoryflow.io",
    Role.AUDITOR: "auditor@factoryflow.io",
}


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    seed_default_users(db, SEED_PASSWORD)
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    app = create_app()

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client


def auth_headers_for(client: TestClient, role: Role) -> Dict[str, str]:
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": ROLE_EMAILS[role], "password": SEED_PASSWORD},
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
