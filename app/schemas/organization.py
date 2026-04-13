from datetime import datetime

from pydantic import BaseModel, field_validator


class OrganizationBase(BaseModel):
    name: str
    description: str | None = None


class OrganizationCreate(OrganizationBase):
    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Organization name must not be empty")  # noqa: TRY003
        return v


class OrganizationUpdate(BaseModel):
    name: str | None = None
    description: str | None = None

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, v: str | None) -> str | None:
        if v is not None and not v.strip():
            raise ValueError("Organization name must not be empty")  # noqa: TRY003
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
