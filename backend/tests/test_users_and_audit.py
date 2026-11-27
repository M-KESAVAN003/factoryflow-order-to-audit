from app.core.permissions import Role
from tests.conftest import auth_headers_for


def test_admin_can_provision_and_update_user_with_audit_trail(client):
    admin_headers = auth_headers_for(client, Role.ADMIN)

    create_resp = client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={
            "email": "new.supervisor@factoryflow.io",
            "full_name": "Alex Rivera",
            "department": "Assembly Line B",
            "password": "StrongPassword!123",
            "role": "floor_supervisor",
        },
    )
    assert create_resp.status_code == 201
    created = create_resp.json()
    assert created["role"] == "floor_supervisor"

    patch_resp = client.patch(
        f"/api/v1/users/{created['id']}",
        headers=admin_headers,
        json={"role": "qa_inspector", "is_active": False},
    )
    assert patch_resp.status_code == 200
    updated = patch_resp.json()
    assert updated["role"] == "qa_inspector"
    assert updated["is_active"] is False

    # Deactivated user must not be able to log in
    blocked_login = client.post(
        "/api/v1/auth/login",
        json={"email": "new.supervisor@factoryflow.io", "password": "StrongPassword!123"},
    )
    assert blocked_login.status_code == 403

    # Auditor can inspect the user provisioning and update events
    auditor_headers = auth_headers_for(client, Role.AUDITOR)
    audit_resp = client.get("/api/v1/audit-logs?action=user.", headers=auditor_headers)
    assert audit_resp.status_code == 200
    actions = {item["action"] for item in audit_resp.json()["items"]}
    assert "user.created" in actions
    assert "user.updated" in actions


def test_non_admin_cannot_create_users(client):
    supervisor_headers = auth_headers_for(client, Role.FLOOR_SUPERVISOR)
    resp = client.post(
        "/api/v1/users",
        headers=supervisor_headers,
        json={
            "email": "rogue@factoryflow.io",
            "full_name": "Rogue User",
            "password": "StrongPassword!123",
            "role": "admin",
        },
    )
    assert resp.status_code == 403


def test_dashboard_returns_role_specific_stats_for_each_role(client):
    for role in Role:
        headers = auth_headers_for(client, role)
        resp = client.get("/api/v1/dashboard", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["role"] == role.value
        assert body["database_connected"] is True
        assert len(body["stats"]) == 4
        assert len(body["modules"]) == 6
