from datetime import datetime
from typing import List

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.core.permissions import Role


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class UserProfile(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: EmailStr
    full_name: str
    department: str
    role: Role
    role_display_name: str
    is_active: bool
    permissions: List[str]
    created_at: datetime
    last_login_at: datetime | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserProfile


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=6, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class RolePermissionSummary(BaseModel):
    role: Role
    display_name: str
    department: str
    description: str
    permissions: List[str]


class RoleMatrixResponse(BaseModel):
    roles: List[RolePermissionSummary]
    all_permissions: List[str]
