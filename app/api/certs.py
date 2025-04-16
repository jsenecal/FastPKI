from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.cert import (
    CertificateCreate,
    CertificateDetailResponse,
    CertificateResponse,
    CertificateRevoke,
)
from app.services.cert import CertificateService

router = APIRouter()


@router.post(
    "/", response_model=CertificateDetailResponse, status_code=status.HTTP_201_CREATED
)
async def create_certificate(
    cert_in: CertificateCreate,
    ca_id: int,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> CertificateDetailResponse:
    """Create a new certificate signed by the specified CA."""
    try:
        cert = await CertificateService.create_certificate(
            db=db,
            ca_id=ca_id,
            common_name=cert_in.common_name,
            subject_dn=cert_in.subject_dn,
            certificate_type=cert_in.certificate_type,
            key_size=cert_in.key_size,
            valid_days=cert_in.valid_days,
            include_private_key=cert_in.include_private_key,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create certificate: {e!s}",
        ) from e
    else:
        return cert


@router.get("/", response_model=list[CertificateResponse])
async def read_certificates(
    ca_id: Optional[int] = Query(None, description="Filter by CA ID"),
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> list[CertificateResponse]:
    """Get all certificates, optionally filtered by CA ID."""
    certs = await CertificateService.list_certificates(db, ca_id=ca_id)
    return certs


@router.get("/{cert_id}", response_model=CertificateResponse)
async def read_certificate(
    cert_id: int,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> CertificateResponse:
    """Get a specific certificate by ID."""
    cert = await CertificateService.get_certificate(db, cert_id)
    if not cert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certificate with ID {cert_id} not found",
        )
    return cert


@router.get("/{cert_id}/private-key", response_model=CertificateDetailResponse)
async def read_certificate_with_private_key(
    cert_id: int,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> CertificateDetailResponse:
    """Get a specific certificate by ID, including private key if available."""
    cert = await CertificateService.get_certificate(db, cert_id)
    if not cert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certificate with ID {cert_id} not found",
        )
    return cert


@router.post("/{cert_id}/revoke", response_model=CertificateResponse)
async def revoke_certificate(
    cert_id: int,
    revoke_data: CertificateRevoke,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> CertificateResponse:
    """Revoke a certificate by ID."""
    cert = await CertificateService.revoke_certificate(
        db, cert_id, reason=revoke_data.reason
    )
    if not cert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certificate with ID {cert_id} not found",
        )
    return cert
