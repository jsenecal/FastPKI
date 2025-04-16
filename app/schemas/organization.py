from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator


class OrganizationBase(BaseModel):
    name: str
    description: Optional[str] = None


class OrganizationCreate(OrganizationBase):
    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Organization name must not be empty")
        return v


class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("Organization name must not be empty")
        return v


class OrganizationInDBBase(OrganizationBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class Organization(OrganizationInDBBase):
    pass


class OrganizationWithUsers(Organization):
    user_count: int