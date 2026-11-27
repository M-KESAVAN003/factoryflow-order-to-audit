import pytest

from app.core.permissions import Role
from tests.conftest import auth_headers_for


@pytest.mark.parametrize(
    "role,expected_users,expected_audit,expected_orders,expected_prod,expected_qa",
    [
        (Role.ADMIN, 200, 200, 200, 200, 200),
        (Role.ORDER_MANAGER, 403, 403, 200, 200, 403),
        (Role.FLOOR_SUPERVISOR, 403, 403, 200, 200, 200),
        (Role.QA_INSPECTOR, 403, 403, 200, 200, 200),
        (Role.AUDITOR, 403, 200, 200, 200, 200),
    ],
)
def test_five_role_rbac_matrix_enforcement(
    client,
    role,
    expected_users,
    expected_audit,
    expected_orders,
    expected_prod,
    expected_qa,
):
    headers = auth_headers_for(client, role)

    assert client.get("/api/v1/dashboard", headers=headers).status_code == 200
    assert client.get("/api/v1/auth/roles", headers=headers).status_code == 200
    assert client.get("/api/v1/users", headers=headers).status_code == expected_users
    assert client.get("/api/v1/audit-logs", headers=headers).status_code == expected_audit
    assert client.get("/api/v1/workspaces/orders", headers=headers).status_code == expected_orders
    assert client.get("/api/v1/workspaces/production", headers=headers).status_code == expected_prod
    assert client.get("/api/v1/workspaces/qa", headers=headers).status_code == expected_qa


def test_role_matrix_contains_all_five_roles(client):
    headers = auth_headers_for(client, Role.AUDITOR)
    resp = client.get("/api/v1/auth/roles", headers=headers)
    assert resp.status_code == 200
    roles = {item["role"] for item in resp.json()["roles"]}
    assert roles == {
        "admin",
        "order_manager",
        "floor_supervisor",
        "qa_inspector",
        "auditor",
    }
