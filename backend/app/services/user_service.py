from typing import List, Tuple

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.permissions import ROLE_DEFINITIONS, Role, get_permissions_for_role
from app.core.security import hash_password
from app.models.user import User
from app.schemas.auth import UserProfile
from app.schemas.user import UserCreate, UserUpdate
from app.services.audit_service import record_audit_event

DEFAULT_SEED_USERS = [
    ("admin@factoryflow.io", "Elena Vance", "Platform & Governance", Role.ADMIN),
    ("orders@factoryflow.io", "Marcus Chen", "Planning & Orders", Role.ORDER_MANAGER),
    ("floor@factoryflow.io", "Devon Brooks", "Manufacturing Operations", Role.FLOOR_SUPERVISOR),
    ("qa@factoryflow.io", "Priya Nair", "Quality & Release", Role.QA_INSPECTOR),
    ("auditor@factoryflow.io", "Julian Ortiz", "Audit & Regulatory", Role.AUDITOR),
]


def to_user_profile(user: User) -> UserProfile:
    """Convert a User ORM instance into a permission-enriched UserProfile schema."""
    definition = ROLE_DEFINITIONS[user.role]
    return UserProfile(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        department=user.department,
        role=user.role,
        role_display_name=definition.display_name,
        is_active=user.is_active,
        permissions=get_permissions_for_role(user.role),
        created_at=user.created_at,
        last_login_at=user.last_login_at,
    )


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(func.lower(User.email) == email.strip().lower()))


def get_user_by_id(db: Session, user_id: str) -> User | None:
    return db.scalar(select(User).where(User.id == user_id))


def list_users(db: Session, *, role: Role | None = None) -> Tuple[List[User], int]:
    stmt = select(User)
    if role is not None:
        stmt = stmt.where(User.role == role)
    stmt = stmt.order_by(User.created_at.asc())
    users = list(db.scalars(stmt).all())
    return users, len(users)


def create_user(
    db: Session,
    payload: UserCreate,
    *,
    actor: User | None = None,
    ip_address: str | None = None,
) -> User:
    if get_user_by_email(db, payload.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists.",
        )

    user = User(
        email=payload.email.strip().lower(),
        full_name=payload.full_name.strip(),
        department=payload.department.strip(),
        hashed_password=hash_password(payload.password),
        role=payload.role,
        is_active=payload.is_active,
    )
    db.add(user)
    db.flush()

    record_audit_event(
        db,
        actor_id=actor.id if actor else None,
        actor_email=actor.email if actor else "system@factoryflow.io",
        actor_role=actor.role.value if actor else "system",
        action="user.created",
        resource_type="user",
        resource_id=user.id,
        details=f"Provisioned {user.email} with role {user.role.value}",
        ip_address=ip_address,
        commit=False,
    )
    db.commit()
    db.refresh(user)
    return user


def update_user(
    db: Session,
    user_id: str,
    payload: UserUpdate,
    *,
    actor: User,
    ip_address: str | None = None,
) -> User:
    target = get_user_by_id(db, user_id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    if target.id == actor.id and payload.is_active is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Administrators cannot deactivate their own active session account.",
        )

    changes: List[str] = []
    if payload.full_name is not None:
        target.full_name = payload.full_name.strip()
        changes.append("full_name")
    if payload.department is not None:
        target.department = payload.department.strip()
        changes.append("department")
    if payload.role is not None and payload.role != target.role:
        changes.append(f"role:{target.role.value}->{payload.role.value}")
        target.role = payload.role
    if payload.is_active is not None and payload.is_active != target.is_active:
        changes.append(f"is_active:{target.is_active}->{payload.is_active}")
        target.is_active = payload.is_active

    if changes:
        record_audit_event(
            db,
            actor_id=actor.id,
            actor_email=actor.email,
            actor_role=actor.role.value,
            action="user.updated",
            resource_type="user",
            resource_id=target.id,
            details=", ".join(changes),
            ip_address=ip_address,
            commit=False,
        )
        db.commit()
        db.refresh(target)

    return target


def seed_default_users(db: Session, default_password: str) -> int:
    """Idempotently ensure one default account exists for each of the five roles."""
    created = 0
    for email, full_name, department, role in DEFAULT_SEED_USERS:
        if get_user_by_email(db, email) is None:
            create_user(
                db,
                UserCreate(
                    email=email,
                    full_name=full_name,
                    department=department,
                    password=default_password,
                    role=role,
                    is_active=True,
                ),
            )
            created += 1
    return created
