from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.db.models import CertificateAuthority
from app.schemas.ca import CACreate, CADetailResponse, CAResponse
from app.services.ca import CAService

router = APIRouter()


@router.post("/", response_model=CADetailResponse, status_code=status.HTTP_201_CREATED)
async def create_ca(
    ca_in: CACreate, 
    db: AsyncSession = Depends(get_db)
) -> CADetailResponse:
    """Create a new Certificate Authority."""
    try:
        ca = await CAService.create_ca(
            db=db,
            name=ca_in.name,
            subject_dn=ca_in.subject_dn,
            description=ca_in.description,
            key_size=ca_in.key_size,
            valid_days=ca_in.valid_days,
        )
        return ca
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create CA: {str(e)}",
        )


@router.get("/", response_model=List[CAResponse])
async def read_cas(
    db: AsyncSession = Depends(get_db)
) -> List[CAResponse]:
    """Get all Certificate Authorities."""
    cas = await CAService.list_cas(db)
    return cas


@router.get("/{ca_id}", response_model=CAResponse)
async def read_ca(
    ca_id: int, 
    db: AsyncSession = Depends(get_db)
) -> CAResponse:
    """Get a specific Certificate Authority by ID."""
    ca = await CAService.get_ca(db, ca_id)
    if not ca:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certificate Authority with ID {ca_id} not found",
        )
    return ca


@router.get("/{ca_id}/private-key", response_model=CADetailResponse)
async def read_ca_with_private_key(
    ca_id: int, 
    db: AsyncSession = Depends(get_db)
) -> CADetailResponse:
    """Get a specific Certificate Authority by ID, including private key."""
    ca = await CAService.get_ca(db, ca_id)
    if not ca:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certificate Authority with ID {ca_id} not found",
        )
    return ca


@router.delete("/{ca_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ca(
    ca_id: int, 
    db: AsyncSession = Depends(get_db)
) -> None:
    """Delete a Certificate Authority by ID."""
    success = await CAService.delete_ca(db, ca_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certificate Authority with ID {ca_id} not found",
        )