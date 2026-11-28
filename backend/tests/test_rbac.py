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
        (Role.OWNER, 403, 200, 200, 200, 200),
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
        "owner",
    }


def test_owner_role_is_strictly_read_only_across_operational_modules(client):
    owner_h = auth_headers_for(client, Role.OWNER)

    # Owner CAN read executive dashboard, audit trail, reports, and role definitions
    assert client.get("/api/v1/dashboard", headers=owner_h).status_code == 200
    assert client.get("/api/v1/dashboard/owner", headers=owner_h).status_code == 200
    assert client.get("/api/v1/audit-logs", headers=owner_h).status_code == 200
    assert client.get("/api/v1/reports/sales", headers=owner_h).status_code == 200
    assert client.get("/api/v1/reports/export/csv?report_type=sales", headers=owner_h).status_code == 200

    # Owner CANNOT manage users, create/approve orders or invoices, or modify purchases/inventory/production
    assert client.get("/api/v1/users", headers=owner_h).status_code == 403
    assert client.post(
        "/api/v1/users",
        headers=owner_h,
        json={"email": "x@factoryflow.io", "full_name": "X", "password": "Password!123", "role": "auditor"},
    ).status_code == 403
    assert client.post("/api/v1/orders", headers=owner_h, json={"customer_id": "x", "items": []}).status_code == 403
    assert client.post("/api/v1/orders/fake-id/approve", headers=owner_h).status_code == 403
    assert client.post("/api/v1/invoices", headers=owner_h, json={"sales_order_id": "fake-id"}).status_code == 403
    assert client.post("/api/v1/dispatches", headers=owner_h, json={"sales_order_id": "fake-id"}).status_code == 403
    assert client.post("/api/v1/purchases", headers=owner_h, json={}).status_code == 403
    assert client.post("/api/v1/inventory/adjustments", headers=owner_h, json={}).status_code == 403
    assert client.post("/api/v1/production", headers=owner_h, json={}).status_code == 403
    assert client.post("/api/v1/boms", headers=owner_h, json={}).status_code == 403
    assert client.post("/api/v1/payments", headers=owner_h, json={}).status_code == 403
