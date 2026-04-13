from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.db.models import AuditAction, PermissionAction, User, UserRole
from app.db.session import get_session
from app.schemas.cert import (
    CertificateCreate,
    CertificateDetailResponse,
    CertificateResponse,
    CertificateRevoke,
)
from app.services.audit import AuditService
from app.services.cert import CertificateService
from app.services.encryption import EncryptionService
from app.services.exceptions import (
    LeafCertNotAllowedError,
    NotFoundError,
    PermissionDeniedError,
)
from app.services.permission import PermissionService

router = APIRouter()


@router.post(
    "/", response_model=CertificateDetailResponse, status_code=status.HTTP_201_CREATED
)
async def create_certificate(
    cert_in: CertificateCreate,
    ca_id: int,
    request: Request,
    db: AsyncSession = Depends(get_session),  # noqa: B008
    current_user: User = Depends(get_current_active_user),  # noqa: B008
) -> CertificateDetailResponse:
    """Create a new certificate signed by the specified CA."""
    perm = PermissionService(db)
    try:
        await perm.check_ca_access(current_user, ca_id, PermissionAction.CREATE_CERT)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except PermissionDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    cert_service = CertificateService(db)
    try:
        base_url = str(request.base_url).rstrip("/")
        cert = await cert_service.create_certificate(
            ca_id=ca_id,
            common_name=cert_in.common_name,
            subject_dn=cert_in.subject_dn,
            certificate_type=cert_in.certificate_type,
            key_size=cert_in.key_size,
            valid_days=cert_in.valid_days,
            include_private_key=cert_in.include_private_key,
            organization_id=current_user.organization_id,
            created_by_user_id=current_user.id,
            base_url=base_url,
        )
    except LeafCertNotAllowedError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
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
        audit_service = AuditService(db)
        await audit_service.log_action(
            action=AuditAction.CERT_CREATE,
            user_id=current_user.id,
            username=current_user.username,
            organization_id=current_user.organization_id,
            resource_type="certificate",
            resource_id=cert.id,
            detail=f"Created certificate '{cert.common_name}'",
        )
        cert.private_key = EncryptionService.decrypt_optional_private_key(
            cert.private_key
        )
        return cert


@router.get("/", response_model=list[CertificateResponse])
async def read_certificates(
    ca_id: Optional[int] = Query(None, description="Filter by CA ID"),
    db: AsyncSession = Depends(get_session),  # noqa: B008
    current_user: User = Depends(get_current_active_user),  # noqa: B008
) -> list[CertificateResponse]:
    """Get all certificates, optionally filtered by CA ID."""
    cert_service = CertificateService(db)
    if current_user.role == UserRole.SUPERUSER:
        certs = await cert_service.list_certificates(ca_id=ca_id)
    else:
        certs = await cert_service.list_certificates(
            ca_id=ca_id,
            organization_id=current_user.organization_id,
        )
    return certs


@router.get("/{cert_id}", response_model=CertificateResponse)
async def read_certificate(
    cert_id: int,
    db: AsyncSession = Depends(get_session),  # noqa: B008
    current_user: User = Depends(get_current_active_user),  # noqa: B008
) -> CertificateResponse:
    """Get a specific certificate by ID."""
    perm = PermissionService(db)
    try:
        cert = await perm.check_cert_access(
            current_user, cert_id, PermissionAction.READ
        )
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except PermissionDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    return cert


@router.get("/{cert_id}/private-key", response_model=CertificateDetailResponse)
async def read_certificate_with_private_key(
    cert_id: int,
    db: AsyncSession = Depends(get_session),  # noqa: B008
    current_user: User = Depends(get_current_active_user),  # noqa: B008
) -> CertificateDetailResponse:
    """Get a specific certificate by ID, including private key if available."""
    perm = PermissionService(db)
    try:
        cert = await perm.check_cert_access(
            current_user, cert_id, PermissionAction.EXPORT_PRIVATE_KEY
        )
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except PermissionDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    audit_service = AuditService(db)
    await audit_service.log_action(
        action=AuditAction.CERT_EXPORT_PRIVATE_KEY,
        user_id=current_user.id,
        username=current_user.username,
        organization_id=current_user.organization_id,
        resource_type="certificate",
        resource_id=cert_id,
    )
    cert.private_key = EncryptionService.decrypt_optional_private_key(cert.private_key)
    return cert


@router.post("/{cert_id}/revoke", response_model=CertificateResponse)
async def revoke_certificate(
    cert_id: int,
    revoke_data: CertificateRevoke,
    db: AsyncSession = Depends(get_session),  # noqa: B008
    current_user: User = Depends(get_current_active_user),  # noqa: B008
) -> CertificateResponse:
    """Revoke a certificate by ID."""
    perm = PermissionService(db)
    try:
        await perm.check_cert_access(
            current_user, cert_id, PermissionAction.REVOKE_CERT
        )
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except PermissionDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    cert_service = CertificateService(db)
    try:
        cert = await cert_service.revoke_certificate(cert_id, reason=revoke_data.reason)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        ) from e
    if not cert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certificate with ID {cert_id} not found",
        )
    audit_service = AuditService(db)
    await audit_service.log_action(
        action=AuditAction.CERT_REVOKE,
        user_id=current_user.id,
        username=current_user.username,
        organization_id=current_user.organization_id,
        resource_type="certificate",
        resource_id=cert_id,
        detail=f"Revoked certificate '{cert.common_name}'",
    )
    return cert
