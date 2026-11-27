from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_client_ip, get_current_user, require_permissions
from app.core.database import get_db
from app.core.permissions import ROLE_DEFINITIONS, Permission, get_permissions_for_role
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    PasswordChangeRequest,
    RoleMatrixResponse,
    RolePermissionSummary,
    TokenResponse,
    UserProfile,
)
from app.services.audit_service import record_audit_event
from app.services.auth_service import authenticate_user, change_user_password
from app.services.user_service import to_user_profile

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Authenticate a user with email and password and issue a JWT bearer token."""
    return authenticate_user(
        db,
        email=payload.email,
        password=payload.password,
        ip_address=get_client_ip(request),
    )


@router.post("/logout", status_code=status.HTTP_200_OK)
def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Record explicit session termination in the audit log."""
    record_audit_event(
        db,
        actor_id=current_user.id,
        actor_email=current_user.email,
        actor_role=current_user.role.value,
        action="auth.logout",
        resource_type="session",
        resource_id=current_user.id,
        details="User signed out",
        ip_address=get_client_ip(request),
    )
    return {"message": "Signed out successfully."}


@router.get("/me", response_model=UserProfile)
def read_current_user(current_user: User = Depends(get_current_user)) -> UserProfile:
    """Return the authenticated user's profile and active RBAC permissions."""
    return to_user_profile(current_user)


@router.post("/change-password", status_code=status.HTTP_200_OK)
def change_password(
    payload: PasswordChangeRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Change the currently authenticated user's password."""
    change_user_password(
        db,
        user=current_user,
        current_password=payload.current_password,
        new_password=payload.new_password,
        ip_address=get_client_ip(request),
    )
    return {"message": "Password updated successfully."}


@router.get("/roles", response_model=RoleMatrixResponse)
def read_role_matrix(
    _: User = Depends(require_permissions(Permission.ROLES_READ)),
) -> RoleMatrixResponse:
    """Return all five canonical FactoryFlow roles and their permission sets."""
    roles = [
        RolePermissionSummary(
            role=defn.role,
            display_name=defn.display_name,
            department=defn.department,
            description=defn.description,
            permissions=get_permissions_for_role(defn.role),
        )
        for defn in ROLE_DEFINITIONS.values()
    ]
    all_permissions = sorted(perm.value for perm in Permission)
    return RoleMatrixResponse(roles=roles, all_permissions=all_permissions)
