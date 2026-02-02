from datetime import datetime
from enum import Enum
from typing import Optional
from zoneinfo import ZoneInfo

from sqlalchemy import Column, DateTime
from sqlmodel import Field, Relationship, SQLModel

UTC = ZoneInfo("UTC")


class UserRole(str, Enum):
    SUPERUSER = "superuser"
    ADMIN = "admin"
    USER = "user"


class PermissionAction(str, Enum):
    READ = "read"
    CREATE_CA = "create_ca"
    CREATE_CERT = "create_cert"
    REVOKE_CERT = "revoke_cert"
    EXPORT_PRIVATE_KEY = "export_private_key"
    DELETE_CA = "delete_ca"


class CertificateStatus(str, Enum):
    VALID = "valid"
    REVOKED = "revoked"
    EXPIRED = "expired"


class CertificateType(str, Enum):
    CA = "ca"
    SERVER = "server"
    CLIENT = "client"


class AuditAction(str, Enum):
    CA_CREATE = "ca_create"
    CA_DELETE = "ca_delete"
    CA_EXPORT_PRIVATE_KEY = "ca_export_private_key"
    CERT_CREATE = "cert_create"
    CERT_REVOKE = "cert_revoke"
    CERT_EXPORT_PRIVATE_KEY = "cert_export_private_key"
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    USER_CREATE = "user_create"
    USER_UPDATE = "user_update"
    ORG_CREATE = "org_create"
    ORG_DELETE = "org_delete"
    ORG_ADD_USER = "org_add_user"
    ORG_REMOVE_USER = "org_remove_user"


class Organization(SQLModel, table=True):
    __tablename__ = "organizations"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(
        sa_column=Column(
            DateTime,
            default=lambda: datetime.now(UTC),
            onupdate=lambda: datetime.now(UTC),
        )
    )

    users: list["User"] = Relationship(back_populates="organization")


class CertificateAuthorityBase(SQLModel):
    name: str = Field(index=True)
    description: Optional[str] = None
    subject_dn: str
    key_size: int
    valid_days: int


class CertificateAuthority(CertificateAuthorityBase, table=True):
    __tablename__ = "certificate_authorities"

    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(
        sa_column=Column(
            DateTime,
            default=lambda: datetime.now(UTC),
            onupdate=lambda: datetime.now(UTC),
        )
    )

    private_key: str  # PEM encoded
    certificate: str  # PEM encoded

    organization_id: Optional[int] = Field(default=None, foreign_key="organizations.id")
    created_by_user_id: Optional[int] = Field(default=None, foreign_key="users.id")

    certificates: list["Certificate"] = Relationship(
        back_populates="issuer",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class CertificateBase(SQLModel):
    common_name: str = Field(index=True)
    subject_dn: str
    certificate_type: CertificateType
    key_size: int
    valid_days: int
    status: CertificateStatus = Field(default=CertificateStatus.VALID)


class Certificate(CertificateBase, table=True):
    __tablename__ = "certificates"

    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(
        sa_column=Column(
            DateTime,
            default=lambda: datetime.now(UTC),
            onupdate=lambda: datetime.now(UTC),
        )
    )

    private_key: Optional[str] = None  # PEM encoded
    certificate: str  # PEM encoded
    serial_number: str = Field(index=True)
    not_before: datetime
    not_after: datetime
    revoked_at: Optional[datetime] = None

    issuer_id: Optional[int] = Field(
        default=None, foreign_key="certificate_authorities.id"
    )
    issuer: Optional[CertificateAuthority] = Relationship(back_populates="certificates")

    organization_id: Optional[int] = Field(default=None, foreign_key="organizations.id")
    created_by_user_id: Optional[int] = Field(default=None, foreign_key="users.id")


class CRLEntry(SQLModel, table=True):
    __tablename__ = "crl_entries"

    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    serial_number: str = Field(index=True)
    revocation_date: datetime
    reason: Optional[str] = None

    ca_id: int = Field(foreign_key="certificate_authorities.id")


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    email: str = Field(index=True, unique=True)
    hashed_password: str
    role: UserRole = Field(default=UserRole.USER)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(
        sa_column=Column(
            DateTime,
            default=lambda: datetime.now(UTC),
            onupdate=lambda: datetime.now(UTC),
        )
    )

    can_create_ca: bool = Field(default=False)
    can_create_cert: bool = Field(default=False)
    can_revoke_cert: bool = Field(default=False)
    can_export_private_key: bool = Field(default=False)
    can_delete_ca: bool = Field(default=False)

    organization_id: Optional[int] = Field(default=None, foreign_key="organizations.id")
    organization: Optional[Organization] = Relationship(back_populates="users")


class AuditLog(SQLModel, table=True):
    __tablename__ = "audit_logs"

    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), index=True)
    action: AuditAction = Field(index=True)
    user_id: Optional[int] = Field(default=None, foreign_key="users.id", index=True)
    username: Optional[str] = None
    organization_id: Optional[int] = Field(
        default=None, foreign_key="organizations.id", index=True
    )
    resource_type: Optional[str] = None
    resource_id: Optional[int] = None
    detail: Optional[str] = None
