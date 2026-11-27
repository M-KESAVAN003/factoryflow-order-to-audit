from typing import List

from pydantic import BaseModel, EmailStr, Field

from app.core.permissions import Role
from app.schemas.auth import UserProfile


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=120)
    department: str = Field(default="Operations", min_length=2, max_length=120)
    password: str = Field(min_length=8, max_length=128)
    role: Role
    is_active: bool = True


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    department: str | None = Field(default=None, min_length=2, max_length=120)
    role: Role | None = None
    is_active: bool | None = None


class UserListResponse(BaseModel):
    items: List[UserProfile]
    total: int
