from app.core.permissions import Role
from tests.conftest import ROLE_EMAILS, SEED_PASSWORD, auth_headers_for


def test_login_success_and_me_profile(client):
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": ROLE_EMAILS[Role.ORDER_MANAGER], "password": SEED_PASSWORD},
    )
    assert login_resp.status_code == 200
    data = login_resp.json()
    assert data["token_type"] == "bearer"
    assert data["user"]["role"] == Role.ORDER_MANAGER.value
    assert "orders:manage" in data["user"]["permissions"]

    me_resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {data['access_token']}"},
    )
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == ROLE_EMAILS[Role.ORDER_MANAGER]


def test_login_invalid_credentials_rejected_and_audited(client):
    bad_resp = client.post(
        "/api/v1/auth/login",
        json={"email": ROLE_EMAILS[Role.ADMIN], "password": "WrongPassword123"},
    )
    assert bad_resp.status_code == 401

    admin_headers = auth_headers_for(client, Role.ADMIN)
    audit_resp = client.get("/api/v1/audit-logs?action=auth.login_failed", headers=admin_headers)
    assert audit_resp.status_code == 200
    assert audit_resp.json()["total"] >= 1


def test_unauthenticated_requests_rejected(client):
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get("/api/v1/dashboard").status_code == 401
    assert client.get("/api/v1/users").status_code == 401
    assert client.get("/api/v1/audit-logs").status_code == 401


def test_change_password_and_relogin(client):
    headers = auth_headers_for(client, Role.QA_INSPECTOR)
    change_resp = client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={"current_password": SEED_PASSWORD, "new_password": "NewSecurePassword!99"},
    )
    assert change_resp.status_code == 200

    old_login = client.post(
        "/api/v1/auth/login",
        json={"email": ROLE_EMAILS[Role.QA_INSPECTOR], "password": SEED_PASSWORD},
    )
    assert old_login.status_code == 401

    new_login = client.post(
        "/api/v1/auth/login",
        json={"email": ROLE_EMAILS[Role.QA_INSPECTOR], "password": "NewSecurePassword!99"},
    )
    assert new_login.status_code == 200
