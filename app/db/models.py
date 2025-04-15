from datetime import datetime
from enum import Enum
from typing import List, Optional

from sqlmodel import Field, Relationship, SQLModel


class CertificateStatus(str, Enum):
    VALID = "valid"
    REVOKED = "revoked"
    EXPIRED = "expired"


class CertificateType(str, Enum):
    CA = "ca"
    SERVER = "server"
    CLIENT = "client"


class CertificateAuthorityBase(SQLModel):
    name: str = Field(index=True)
    description: Optional[str] = None
    subject_dn: str
    key_size: int
    valid_days: int


class CertificateAuthority(CertificateAuthorityBase, table=True):
    __tablename__ = "certificate_authorities"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    private_key: str  # PEM encoded
    certificate: str  # PEM encoded
    
    certificates: List["Certificate"] = Relationship(
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
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    private_key: Optional[str] = None  # PEM encoded
    certificate: str  # PEM encoded
    serial_number: str = Field(index=True)
    not_before: datetime
    not_after: datetime
    revoked_at: Optional[datetime] = None
    
    issuer_id: Optional[int] = Field(default=None, foreign_key="certificate_authorities.id")
    issuer: Optional[CertificateAuthority] = Relationship(back_populates="certificates")


class CRLEntry(SQLModel, table=True):
    __tablename__ = "crl_entries"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    serial_number: str = Field(index=True)
    revocation_date: datetime
    reason: Optional[str] = None
    
    ca_id: int = Field(foreign_key="certificate_authorities.id")