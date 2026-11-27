from dataclasses import dataclass
from enum import Enum
from typing import Dict, FrozenSet, List


class Role(str, Enum):
    """Five canonical roles for the FactoryFlow Order-to-Audit platform."""

    ADMIN = "admin"
    ORDER_MANAGER = "order_manager"
    FLOOR_SUPERVISOR = "floor_supervisor"
    QA_INSPECTOR = "qa_inspector"
    AUDITOR = "auditor"


class Permission(str, Enum):
    """Fine-grained RBAC permissions enforced across API endpoints and UI views."""

    # Phase 1 core permissions
    DASHBOARD_VIEW = "dashboard:view"
    ROLES_READ = "roles:read"
    USERS_READ = "users:read"
    USERS_MANAGE = "users:manage"
    AUDIT_READ = "audit:read"
    ORDERS_READ = "orders:read"
    ORDERS_MANAGE = "orders:manage"
    PRODUCTION_READ = "production:read"
    PRODUCTION_MANAGE = "production:manage"
    QA_READ = "qa:read"
    QA_MANAGE = "qa:manage"
    SYSTEM_CONFIGURE = "system:configure"

    # Phase 2 master-data permissions
    PRODUCTS_READ = "products:read"
    PRODUCTS_MANAGE = "products:manage"
    STOCK_ITEMS_READ = "stock_items:read"
    STOCK_ITEMS_MANAGE = "stock_items:manage"
    SUPPLIERS_READ = "suppliers:read"
    SUPPLIERS_MANAGE = "suppliers:manage"
    CUSTOMERS_READ = "customers:read"
    CUSTOMERS_MANAGE = "customers:manage"
    UNITS_READ = "units:read"
    UNITS_MANAGE = "units:manage"

    # Phase 3 inventory & purchase permissions
    INVENTORY_READ = "inventory:read"
    INVENTORY_MANAGE = "inventory:manage"
    PURCHASES_READ = "purchases:read"
    PURCHASES_MANAGE = "purchases:manage"

    # Phase 4 BOM & production permissions
    BOM_READ = "bom:read"
    BOM_MANAGE = "bom:manage"
    PRODUCTION_RUNS_READ = "production_runs:read"
    PRODUCTION_RUNS_MANAGE = "production_runs:manage"

    # Phase 5 sales orders, GST invoicing & dispatch permissions
    SALES_ORDERS_READ = "sales_orders:read"
    SALES_ORDERS_CREATE = "sales_orders:create"
    SALES_ORDERS_APPROVE = "sales_orders:approve"
    INVOICES_READ = "invoices:read"
    INVOICES_MANAGE = "invoices:manage"
    DISPATCHES_READ = "dispatches:read"
    DISPATCHES_MANAGE = "dispatches:manage"

    # Phase 6 production costing, expenses, payments & receivables permissions
    COSTING_READ = "costing:read"
    EXPENSES_MANAGE = "expenses:manage"
    PAYMENTS_READ = "payments:read"
    PAYMENTS_MANAGE = "payments:manage"
    RECEIVABLES_READ = "receivables:read"

    # Phase 7 executive dashboards & audit reporting permissions
    OWNER_DASHBOARD_VIEW = "owner_dashboard:view"
    REPORTS_VIEW = "reports:view"
    REPORTS_EXPORT = "reports:export"


@dataclass(frozen=True)
class RoleDefinition:
    role: Role
    display_name: str
    department: str
    description: str
    permissions: FrozenSet[Permission]


ROLE_DEFINITIONS: Dict[Role, RoleDefinition] = {
    Role.ADMIN: RoleDefinition(
        role=Role.ADMIN,
        display_name="System Administrator",
        department="Platform & Governance",
        description="Full system access for user provisioning, master data, inventory, purchasing, BOM governance, and production corrections.",
        permissions=frozenset(Permission),
    ),
    Role.ORDER_MANAGER: RoleDefinition(
        role=Role.ORDER_MANAGER,
        display_name="Order & Production Manager",
        department="Planning & Orders",
        description="Manages customer orders and reads active products, assigned customers, and units.",
        permissions=frozenset(
            {
                Permission.DASHBOARD_VIEW,
                Permission.ROLES_READ,
                Permission.ORDERS_READ,
                Permission.ORDERS_MANAGE,
                Permission.PRODUCTION_READ,
                Permission.PRODUCTS_READ,
                Permission.CUSTOMERS_READ,
                Permission.UNITS_READ,
                Permission.SALES_ORDERS_READ,
                Permission.SALES_ORDERS_CREATE,
            }
        ),
    ),
    Role.FLOOR_SUPERVISOR: RoleDefinition(
        role=Role.FLOOR_SUPERVISOR,
        display_name="Shop Floor Supervisor",
        department="Manufacturing Operations",
        description="Creates and executes production runs, issues materials, records output/wastage, and manages inventory receipts.",
        permissions=frozenset(
            {
                Permission.DASHBOARD_VIEW,
                Permission.ROLES_READ,
                Permission.ORDERS_READ,
                Permission.PRODUCTION_READ,
                Permission.PRODUCTION_MANAGE,
                Permission.QA_READ,
                Permission.PRODUCTS_READ,
                Permission.STOCK_ITEMS_READ,
                Permission.SUPPLIERS_READ,
                Permission.UNITS_READ,
                Permission.INVENTORY_READ,
                Permission.INVENTORY_MANAGE,
                Permission.PURCHASES_READ,
                Permission.PURCHASES_MANAGE,
                Permission.BOM_READ,
                Permission.PRODUCTION_RUNS_READ,
                Permission.PRODUCTION_RUNS_MANAGE,
                Permission.COSTING_READ,
                Permission.EXPENSES_MANAGE,
            }
        ),
    ),
    Role.QA_INSPECTOR: RoleDefinition(
        role=Role.QA_INSPECTOR,
        display_name="Quality Assurance Inspector",
        department="Quality & Release",
        description="Conducts quality inspections and holds read-only visibility across production runs, BOMs, materials, and suppliers.",
        permissions=frozenset(
            {
                Permission.DASHBOARD_VIEW,
                Permission.ROLES_READ,
                Permission.ORDERS_READ,
                Permission.PRODUCTION_READ,
                Permission.QA_READ,
                Permission.QA_MANAGE,
                Permission.PRODUCTS_READ,
                Permission.STOCK_ITEMS_READ,
                Permission.SUPPLIERS_READ,
                Permission.UNITS_READ,
                Permission.BOM_READ,
                Permission.PRODUCTION_RUNS_READ,
            }
        ),
    ),
    Role.AUDITOR: RoleDefinition(
        role=Role.AUDITOR,
        display_name="Compliance Auditor",
        department="Audit & Regulatory",
        description="Read-only end-to-end traceability across master data, inventory, purchases, BOMs, production runs, QA, and audit trails.",
        permissions=frozenset(
            {
                Permission.DASHBOARD_VIEW,
                Permission.ROLES_READ,
                Permission.AUDIT_READ,
                Permission.ORDERS_READ,
                Permission.PRODUCTION_READ,
                Permission.QA_READ,
                Permission.PRODUCTS_READ,
                Permission.STOCK_ITEMS_READ,
                Permission.SUPPLIERS_READ,
                Permission.CUSTOMERS_READ,
                Permission.UNITS_READ,
                Permission.INVENTORY_READ,
                Permission.PURCHASES_READ,
                Permission.BOM_READ,
                Permission.PRODUCTION_RUNS_READ,
                Permission.SALES_ORDERS_READ,
                Permission.INVOICES_READ,
                Permission.DISPATCHES_READ,
                Permission.COSTING_READ,
                Permission.PAYMENTS_READ,
                Permission.RECEIVABLES_READ,
                Permission.REPORTS_VIEW,
                Permission.REPORTS_EXPORT,
            }
        ),
    ),
}


def get_permissions_for_role(role: Role | str) -> List[str]:
    """Return sorted permission codes granted to a role."""
    resolved = role if isinstance(role, Role) else Role(role)
    return sorted(perm.value for perm in ROLE_DEFINITIONS[resolved].permissions)


def role_has_permission(role: Role | str, permission: Permission) -> bool:
    """Return True if the given role includes the requested permission."""
    resolved = role if isinstance(role, Role) else Role(role)
    return permission in ROLE_DEFINITIONS[resolved].permissions
