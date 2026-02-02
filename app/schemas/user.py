from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, field_validator

from app.db.models import UserRole


class UserBase(BaseModel):
    username: str
    email: EmailStr
    role: Optional[UserRole] = UserRole.USER
    is_active: Optional[bool] = True
    organization_id: Optional[int] = None
    can_create_ca: bool = False
    can_create_cert: bool = False
    can_revoke_cert: bool = False
    can_export_private_key: bool = False
    can_delete_ca: bool = False


class UserCreate(UserBase):
    password: str

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Min 8 chars")  # noqa: TRY003
        return v


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    organization_id: Optional[int] = None
    can_create_ca: Optional[bool] = None
    can_create_cert: Optional[bool] = None
    can_revoke_cert: Optional[bool] = None
    can_export_private_key: Optional[bool] = None
    can_delete_ca: Optional[bool] = None

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v) < 8:
            raise ValueError("Min 8 chars")  # noqa: TRY003
        return v


class UserInDBBase(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}  # noqa: RUF012


class User(UserInDBBase):
    pass


class UserInDB(UserInDBBase):
    hashed_password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenPayload(BaseModel):
    sub: Optional[str] = None
    id: Optional[int] = None
    role: Optional[str] = None
    exp: Optional[int] = None
