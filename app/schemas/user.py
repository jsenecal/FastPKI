from datetime import datetime

from pydantic import BaseModel, EmailStr, field_validator

from app.db.models import UserRole


class UserBase(BaseModel):
    username: str
    email: EmailStr
    role: UserRole | None = UserRole.USER
    is_active: bool | None = True
    organization_id: int | None = None
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
    email: EmailStr | None = None
    password: str | None = None
    role: UserRole | None = None
    is_active: bool | None = None
    organization_id: int | None = None
    can_create_ca: bool | None = None
    can_create_cert: bool | None = None
    can_revoke_cert: bool | None = None
    can_export_private_key: bool | None = None
    can_delete_ca: bool | None = None

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str | None) -> str | None:
        if v is not None and len(v) < 8:
            raise ValueError("Min 8 chars")  # noqa: TRY003
        return v


class UserInDBBase(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class User(UserInDBBase):
    pass


class UserInDB(UserInDBBase):
    hashed_password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenPayload(BaseModel):
    sub: str | None = None
    id: int | None = None
    role: str | None = None
    exp: int | None = None
