from datetime import datetime
from typing import List

from pydantic import BaseModel, ConfigDict


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    actor_id: str | None = None
    actor_email: str
    actor_role: str
    action: str
    resource_type: str
    resource_id: str | None = None
    status: str
    details: str | None = None
    ip_address: str | None = None
    created_at: datetime


class AuditLogListResponse(BaseModel):
    items: List[AuditLogOut]
    total: int
