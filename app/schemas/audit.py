from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.db.models import AuditAction


class AuditLogResponse(BaseModel):
    id: int
    created_at: datetime
    action: AuditAction
    user_id: Optional[int] = None
    username: Optional[str] = None
    organization_id: Optional[int] = None
    resource_type: Optional[str] = None
    resource_id: Optional[int] = None
    detail: Optional[str] = None

    model_config = {"from_attributes": True}
