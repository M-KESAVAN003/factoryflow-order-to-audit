from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_permissions
from app.core.database import get_db
from app.core.permissions import Permission
from app.models.user import User
from app.schemas.audit_log import AuditLogListResponse, AuditLogOut
from app.services.audit_service import list_audit_logs

router = APIRouter(prefix="/audit-logs", tags=["audit"])


@router.get("", response_model=AuditLogListResponse)
def get_audit_logs(
    action: str | None = Query(default=None),
    actor_role: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _: User = Depends(require_permissions(Permission.AUDIT_READ)),
    db: Session = Depends(get_db),
) -> AuditLogListResponse:
    """Query immutable audit log entries (requires audit:read)."""
    items, total = list_audit_logs(
        db,
        action=action,
        actor_role=actor_role,
        status=status_filter,
        limit=limit,
        offset=offset,
    )
    return AuditLogListResponse(
        items=[AuditLogOut.model_validate(item) for item in items],
        total=total,
    )
