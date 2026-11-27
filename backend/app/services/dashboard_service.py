from typing import Dict, List

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import check_database_connection
from app.core.permissions import (
    ROLE_DEFINITIONS,
    Permission,
    Role,
    get_permissions_for_role,
    role_has_permission,
)
from app.models.audit_log import AuditLog
from app.models.user import User
from app.schemas.audit_log import AuditLogOut
from app.schemas.dashboard import DashboardModule, DashboardStat, RoleDashboardResponse


def _build_modules(role: Role) -> List[DashboardModule]:
    catalog = [
        (
            "orders",
            "Customer Orders & Batch Release",
            "Order intake, priority scheduling, and production release authority.",
            "/dashboard",
            Permission.ORDERS_MANAGE,
            "Active in Phase 2",
        ),
        (
            "production",
            "Shop Floor Execution",
            "Work-order routing, operator handoffs, and stage completion logging.",
            "/dashboard",
            Permission.PRODUCTION_MANAGE,
            "Active in Phase 2",
        ),
        (
            "qa",
            "Quality Inspection & Holds",
            "In-process inspection gates, NCR tracking, and batch sign-off.",
            "/dashboard",
            Permission.QA_MANAGE,
            "Active in Phase 2",
        ),
        (
            "users",
            "User & Role Provisioning",
            "Manage plant personnel, role assignments, and account status.",
            "/users",
            Permission.USERS_MANAGE,
            "Live",
        ),
        (
            "audit",
            "Immutable Audit Trail",
            "Inspect chronological security, RBAC, and compliance events.",
            "/audit-logs",
            Permission.AUDIT_READ,
            "Live",
        ),
        (
            "permissions",
            "Five-Role Permission Matrix",
            "Inspect role boundaries across Order-to-Audit operations.",
            "/permissions",
            Permission.ROLES_READ,
            "Live",
        ),
    ]
    return [
        DashboardModule(
            key=key,
            title=title,
            description=description,
            route=route,
            required_permission=perm.value,
            enabled=role_has_permission(role, perm),
            status=status_label,
        )
        for key, title, description, route, perm, status_label in catalog
    ]


def build_role_dashboard(db: Session, user: User) -> RoleDashboardResponse:
    """Compute a live DB-backed dashboard payload scoped to the user's role."""
    definition = ROLE_DEFINITIONS[user.role]
    db_ok = check_database_connection(db)

    total_users = int(db.scalar(select(func.count(User.id))) or 0)
    active_users = int(db.scalar(select(func.count(User.id)).where(User.is_active.is_(True))) or 0)
    total_audit_events = int(db.scalar(select(func.count(AuditLog.id))) or 0)
    failed_auth_events = int(
        db.scalar(
            select(func.count(AuditLog.id)).where(AuditLog.status == "failure")
        )
        or 0
    )

    role_counts_rows = db.execute(
        select(User.role, func.count(User.id)).group_by(User.role)
    ).all()
    role_distribution: Dict[str, int] = {r.value: 0 for r in Role}
    for role_val, cnt in role_counts_rows:
        role_distribution[role_val.value if isinstance(role_val, Role) else str(role_val)] = int(cnt)

    can_read_all_audit = role_has_permission(user.role, Permission.AUDIT_READ)
    activity_stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(10)
    if not can_read_all_audit:
        activity_stmt = (
            select(AuditLog)
            .where(AuditLog.actor_id == user.id)
            .order_by(AuditLog.created_at.desc())
            .limit(10)
        )
    recent_logs = [AuditLogOut.model_validate(item) for item in db.scalars(activity_stmt).all()]

    permissions = get_permissions_for_role(user.role)

    stats = _build_role_stats(
        user=user,
        db_ok=db_ok,
        total_users=total_users,
        active_users=active_users,
        total_audit_events=total_audit_events,
        failed_auth_events=failed_auth_events,
        role_distribution=role_distribution,
        permissions_count=len(permissions),
        personal_events_count=len(recent_logs),
    )

    return RoleDashboardResponse(
        role=user.role,
        role_display_name=definition.display_name,
        department=definition.department,
        database_connected=db_ok,
        stats=stats,
        modules=_build_modules(user.role),
        role_distribution=role_distribution,
        recent_activity=recent_logs,
        permissions=permissions,
    )


def _build_role_stats(
    *,
    user: User,
    db_ok: bool,
    total_users: int,
    active_users: int,
    total_audit_events: int,
    failed_auth_events: int,
    role_distribution: Dict[str, int],
    permissions_count: int,
    personal_events_count: int,
) -> List[DashboardStat]:
    db_label = "Connected" if db_ok else "Degraded"

    if user.role == Role.ADMIN:
        return [
            DashboardStat(key="users", label="Provisioned Accounts", value=str(total_users), caption=f"{active_users} active across 5 roles"),
            DashboardStat(key="audit", label="Audit Events Recorded", value=str(total_audit_events), caption=f"{failed_auth_events} security/auth alerts"),
            DashboardStat(key="permissions", label="Granted Permissions", value=str(permissions_count), caption="Full governance authority"),
            DashboardStat(key="database", label="PostgreSQL Status", value=db_label, caption="Neon SSL connection verified"),
        ]
    if user.role == Role.AUDITOR:
        return [
            DashboardStat(key="audit", label="Total Audit Records", value=str(total_audit_events), caption="Immutable chronological ledger"),
            DashboardStat(key="alerts", label="Failed Auth Events", value=str(failed_auth_events), caption="Access denials & invalid attempts"),
            DashboardStat(key="accounts", label="Audited Identities", value=str(total_users), caption=f"{active_users} active personnel"),
            DashboardStat(key="database", label="Ledger Integrity", value=db_label, caption="Read-only compliance posture"),
        ]
    if user.role == Role.ORDER_MANAGER:
        return [
            DashboardStat(key="planners", label="Order Managers", value=str(role_distribution.get(Role.ORDER_MANAGER.value, 0)), caption="Planning & release team"),
            DashboardStat(key="supervisors", label="Floor Supervisors", value=str(role_distribution.get(Role.FLOOR_SUPERVISOR.value, 0)), caption="Available for batch handoff"),
            DashboardStat(key="permissions", label="Order Capabilities", value=str(permissions_count), caption="Order write & floor read"),
            DashboardStat(key="database", label="Core Sync", value=db_label, caption=f"{personal_events_count} recent session events"),
        ]
    if user.role == Role.FLOOR_SUPERVISOR:
        return [
            DashboardStat(key="supervisors", label="Floor Supervisors", value=str(role_distribution.get(Role.FLOOR_SUPERVISOR.value, 0)), caption="Active shift leadership"),
            DashboardStat(key="qa", label="QA Inspectors", value=str(role_distribution.get(Role.QA_INSPECTOR.value, 0)), caption="Available for inspection gates"),
            DashboardStat(key="permissions", label="Floor Capabilities", value=str(permissions_count), caption="Production write & QA read"),
            DashboardStat(key="database", label="Line Connectivity", value=db_label, caption=f"{personal_events_count} recent shift events"),
        ]
    # QA_INSPECTOR
    return [
        DashboardStat(key="qa_team", label="QA Inspectors", value=str(role_distribution.get(Role.QA_INSPECTOR.value, 0)), caption="Inspection & release roster"),
        DashboardStat(key="auditors", label="Compliance Auditors", value=str(role_distribution.get(Role.AUDITOR.value, 0)), caption="Traceability oversight"),
        DashboardStat(key="permissions", label="QA Capabilities", value=str(permissions_count), caption="Inspection & hold authority"),
        DashboardStat(key="database", label="Compliance Link", value=db_label, caption=f"{personal_events_count} recent inspection logs"),
    ]
