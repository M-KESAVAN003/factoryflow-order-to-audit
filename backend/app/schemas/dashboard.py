from typing import Dict, List

from pydantic import BaseModel

from app.core.permissions import Role
from app.schemas.audit_log import AuditLogOut


class DashboardStat(BaseModel):
    key: str
    label: str
    value: str
    caption: str


class DashboardModule(BaseModel):
    key: str
    title: str
    description: str
    route: str
    required_permission: str
    enabled: bool
    status: str


class RoleDashboardResponse(BaseModel):
    role: Role
    role_display_name: str
    department: str
    database_connected: bool
    stats: List[DashboardStat]
    modules: List[DashboardModule]
    role_distribution: Dict[str, int]
    recent_activity: List[AuditLogOut]
    permissions: List[str]
