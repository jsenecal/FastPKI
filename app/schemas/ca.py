from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CACreate(BaseModel):
    name: str
    description: Optional[str] = None
    subject_dn: str
    key_size: Optional[int] = None
    valid_days: Optional[int] = None


class CAResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    name: str
    description: Optional[str] = None
    subject_dn: str
    key_size: int
    valid_days: int
    created_at: datetime
    updated_at: datetime
    certificate: str
    organization_id: Optional[int] = None
    created_by_user_id: Optional[int] = None


class CADetailResponse(CAResponse):
    private_key: str
