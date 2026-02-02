from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.db.models import AuditAction, PermissionAction, User, UserRole
from app.db.session import get_session
from app.schemas.ca import CACreate, CADetailResponse, CAResponse
from app.services.audit import AuditService
from app.services.ca import CAService
from app.services.encryption import EncryptionService
from app.services.exceptions import NotFoundError, PermissionDeniedError
from app.services.permission import PermissionService

router = APIRouter()


@router.post("/", response_model=CADetailResponse, status_code=status.HTTP_201_CREATED)
async def create_ca(
    ca_in: CACreate,
    db: AsyncSession = Depends(get_session),  # noqa: B008
    current_user: User = Depends(get_current_active_user),  # noqa: B008
) -> CADetailResponse:
    """Create a new Certificate Authority."""
    perm = PermissionService(db)
    if not perm._user_can_perform(
        current_user,
        current_user.organization_id,
        None,
        PermissionAction.CREATE_CA,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )
    ca_service = CAService(db)
    try:
        ca = await ca_service.create_ca(
            name=ca_in.name,
            subject_dn=ca_in.subject_dn,
            description=ca_in.description,
            key_size=ca_in.key_size,
            valid_days=ca_in.valid_days,
            organization_id=current_user.organization_id,
            created_by_user_id=current_user.id,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create CA: {e!s}",
        ) from e
    else:
        audit_service = AuditService(db)
        await audit_service.log_action(
            action=AuditAction.CA_CREATE,
            user_id=current_user.id,
            username=current_user.username,
            organization_id=current_user.organization_id,
            resource_type="ca",
            resource_id=ca.id,
            detail=f"Created CA '{ca.name}'",
        )
        ca.private_key = EncryptionService.decrypt_private_key(ca.private_key)
        return ca


@router.get("/", response_model=list[CAResponse])
async def read_cas(
    db: AsyncSession = Depends(get_session),  # noqa: B008
    current_user: User = Depends(get_current_active_user),  # noqa: B008
) -> list[CAResponse]:
    """Get all Certificate Authorities."""
    ca_service = CAService(db)
    if current_user.role == UserRole.SUPERUSER:
        cas = await ca_service.list_cas()
    else:
        cas = await ca_service.list_cas(organization_id=current_user.organization_id)
    return cas


@router.get("/{ca_id}", response_model=CAResponse)
async def read_ca(
    ca_id: int,
    db: AsyncSession = Depends(get_session),  # noqa: B008
    current_user: User = Depends(get_current_active_user),  # noqa: B008
) -> CAResponse:
    """Get a specific Certificate Authority by ID."""
    perm = PermissionService(db)
    try:
        ca = await perm.check_ca_access(current_user, ca_id, PermissionAction.READ)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except PermissionDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    return ca


@router.get("/{ca_id}/private-key", response_model=CADetailResponse)
async def read_ca_with_private_key(
    ca_id: int,
    db: AsyncSession = Depends(get_session),  # noqa: B008
    current_user: User = Depends(get_current_active_user),  # noqa: B008
) -> CADetailResponse:
    """Get a specific Certificate Authority by ID, including private key."""
    perm = PermissionService(db)
    try:
        ca = await perm.check_ca_access(
            current_user, ca_id, PermissionAction.EXPORT_PRIVATE_KEY
        )
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except PermissionDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    audit_service = AuditService(db)
    await audit_service.log_action(
        action=AuditAction.CA_EXPORT_PRIVATE_KEY,
        user_id=current_user.id,
        username=current_user.username,
        organization_id=current_user.organization_id,
        resource_type="ca",
        resource_id=ca_id,
    )
    ca.private_key = EncryptionService.decrypt_private_key(ca.private_key)
    return ca


@router.delete("/{ca_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ca(
    ca_id: int,
    db: AsyncSession = Depends(get_session),  # noqa: B008
    current_user: User = Depends(get_current_active_user),  # noqa: B008
) -> None:
    """Delete a Certificate Authority by ID."""
    perm = PermissionService(db)
    try:
        await perm.check_ca_access(current_user, ca_id, PermissionAction.DELETE_CA)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except PermissionDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    ca_service = CAService(db)
    await ca_service.delete_ca(ca_id)
    audit_service = AuditService(db)
    await audit_service.log_action(
        action=AuditAction.CA_DELETE,
        user_id=current_user.id,
        username=current_user.username,
        organization_id=current_user.organization_id,
        resource_type="ca",
        resource_id=ca_id,
    )
