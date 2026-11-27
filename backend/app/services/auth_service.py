from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.schemas.auth import TokenResponse
from app.services.audit_service import record_audit_event
from app.services.user_service import get_user_by_email, to_user_profile


def authenticate_user(
    db: Session,
    *,
    email: str,
    password: str,
    ip_address: str | None = None,
) -> TokenResponse:
    """Authenticate credentials against PostgreSQL/SQLAlchemy and emit an audit log."""
    normalized_email = email.strip().lower()
    user = get_user_by_email(db, normalized_email)

    if not user or not verify_password(password, user.hashed_password):
        record_audit_event(
            db,
            actor_id=user.id if user else None,
            actor_email=normalized_email,
            actor_role=user.role.value if user else "anonymous",
            action="auth.login_failed",
            resource_type="session",
            status="failure",
            details="Invalid email or password",
            ip_address=ip_address,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not user.is_active:
        record_audit_event(
            db,
            actor_id=user.id,
            actor_email=user.email,
            actor_role=user.role.value,
            action="auth.login_blocked",
            resource_type="session",
            status="failure",
            details="Inactive user attempted login",
            ip_address=ip_address,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This user account is deactivated. Contact an administrator.",
        )

    user.last_login_at = datetime.now(timezone.utc)
    record_audit_event(
        db,
        actor_id=user.id,
        actor_email=user.email,
        actor_role=user.role.value,
        action="auth.login_success",
        resource_type="session",
        resource_id=user.id,
        details=f"Authenticated as {user.role.value}",
        ip_address=ip_address,
        commit=False,
    )
    db.commit()
    db.refresh(user)

    settings = get_settings()
    token = create_access_token(subject=user.id, role=user.role.value)
    return TokenResponse(
        access_token=token,
        expires_in=settings.access_token_expire_minutes * 60,
        user=to_user_profile(user),
    )


def change_user_password(
    db: Session,
    *,
    user: User,
    current_password: str,
    new_password: str,
    ip_address: str | None = None,
) -> None:
    """Update the authenticated user's password after verifying current credentials."""
    if not verify_password(current_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect.",
        )

    user.hashed_password = hash_password(new_password)
    record_audit_event(
        db,
        actor_id=user.id,
        actor_email=user.email,
        actor_role=user.role.value,
        action="auth.password_changed",
        resource_type="user",
        resource_id=user.id,
        details="User rotated account password",
        ip_address=ip_address,
        commit=False,
    )
    db.commit()
