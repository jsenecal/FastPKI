from datetime import datetime

from pydantic import BaseModel

from app.db.models import AuditAction


class AuditLogResponse(BaseModel):
    id: int
    created_at: datetime
    action: AuditAction
    user_id: int | None = None
    username: str | None = None
    organization_id: int | None = None
    resource_type: str | None = None
    resource_id: int | None = None
    detail: str | None = None

    model_config = {"from_attributes": True}
