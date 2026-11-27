from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_client_ip, require_permissions
from app.core.database import get_db
from app.core.permissions import Permission, Role
from app.models.user import User
from app.schemas.auth import UserProfile
from app.schemas.user import UserCreate, UserListResponse, UserUpdate
from app.services.user_service import create_user, list_users, to_user_profile, update_user

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=UserListResponse)
def get_users(
    role: Role | None = Query(default=None),
    _: User = Depends(require_permissions(Permission.USERS_READ)),
    db: Session = Depends(get_db),
) -> UserListResponse:
    """List platform users (requires users:read)."""
    users, total = list_users(db, role=role)
    return UserListResponse(items=[to_user_profile(u) for u in users], total=total)


@router.post("", response_model=UserProfile, status_code=status.HTTP_201_CREATED)
def post_user(
    payload: UserCreate,
    request: Request,
    actor: User = Depends(require_permissions(Permission.USERS_MANAGE)),
    db: Session = Depends(get_db),
) -> UserProfile:
    """Provision a new user assigned to one of the five roles (requires users:manage)."""
    user = create_user(db, payload, actor=actor, ip_address=get_client_ip(request))
    return to_user_profile(user)


@router.patch("/{user_id}", response_model=UserProfile)
def patch_user(
    user_id: str,
    payload: UserUpdate,
    request: Request,
    actor: User = Depends(require_permissions(Permission.USERS_MANAGE)),
    db: Session = Depends(get_db),
) -> UserProfile:
    """Update a user's role, department, name, or active status (requires users:manage)."""
    user = update_user(
        db,
        user_id,
        payload,
        actor=actor,
        ip_address=get_client_ip(request),
    )
    return to_user_profile(user)
