from typing import List, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def record_audit_event(
    db: Session,
    *,
    actor_id: str | None,
    actor_email: str,
    actor_role: str,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    status: str = "success",
    details: str | None = None,
    ip_address: str | None = None,
    commit: bool = True,
) -> AuditLog:
    """Persist an immutable audit log record."""
    entry = AuditLog(
        actor_id=actor_id,
        actor_email=actor_email,
        actor_role=actor_role,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        status=status,
        details=details,
        ip_address=ip_address,
    )
    db.add(entry)
    if commit:
        db.commit()
        db.refresh(entry)
    return entry


def list_audit_logs(
    db: Session,
    *,
    action: str | None = None,
    actor_role: str | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> Tuple[List[AuditLog], int]:
    """Query audit logs with optional filtering and total count."""
    filters = []
    if action:
        filters.append(AuditLog.action.ilike(f"%{action.strip()}%"))
    if actor_role:
        filters.append(AuditLog.actor_role == actor_role.strip())
    if status:
        filters.append(AuditLog.status == status.strip())

    count_stmt = select(func.count(AuditLog.id)).where(*filters)
    total = int(db.scalar(count_stmt) or 0)

    items_stmt = (
        select(AuditLog)
        .where(*filters)
        .order_by(AuditLog.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    items = list(db.scalars(items_stmt).all())
    return items, total
