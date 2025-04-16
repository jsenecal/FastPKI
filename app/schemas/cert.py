from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.db.models import CertificateStatus, CertificateType


class CertificateCreate(BaseModel):
    common_name: str
    subject_dn: str
    certificate_type: CertificateType
    key_size: Optional[int] = None
    valid_days: Optional[int] = None
    include_private_key: bool = True


class CertificateResponse(BaseModel):
    id: int
    common_name: str
    subject_dn: str
    certificate_type: CertificateType
    key_size: int
    valid_days: int
    status: CertificateStatus
    certificate: str
    serial_number: str
    not_before: datetime
    not_after: datetime
    revoked_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    issuer_id: int


class CertificateDetailResponse(CertificateResponse):
    private_key: Optional[str] = None


class CertificateRevoke(BaseModel):
    reason: Optional[str] = None
