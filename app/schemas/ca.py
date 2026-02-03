from datetime import datetime
from typing import Optional

from pydantic import BaseModel, computed_field


class CACreate(BaseModel):
    name: str
    description: Optional[str] = None
    subject_dn: str
    key_size: Optional[int] = None
    valid_days: Optional[int] = None
    parent_ca_id: Optional[int] = None
    path_length: Optional[int] = None
    allow_leaf_certs: Optional[bool] = None


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
    parent_ca_id: Optional[int] = None
    path_length: Optional[int] = None
    allow_leaf_certs: bool

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_root(self) -> bool:
        return self.parent_ca_id is None


class CADetailResponse(CAResponse):
    private_key: str
