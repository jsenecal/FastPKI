from typing import cast

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_active_admin_user,
    get_current_active_superuser,
    get_current_active_user,
    get_db,
)
from app.db.models import User
from app.schemas.organization import (
    Organization,
    OrganizationCreate,
    OrganizationUpdate,
)
from app.schemas.user import User as UserSchema
from app.services.organization import OrganizationService

router = APIRouter()


@router.post("/", response_model=Organization, status_code=status.HTTP_201_CREATED)
async def create_organization(
    *,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    organization_in: OrganizationCreate,
    current_user: User = Depends(get_current_active_admin_user),  # noqa: B008
) -> Organization:
    """
    Create a new organization.
    Only admin or superuser users can create organizations.
    """
    organization_service = OrganizationService(db)
    organization = await organization_service.create_organization(
        name=organization_in.name,
        description=organization_in.description,
    )
    return organization


@router.get("/{organization_id}", response_model=Organization)
async def read_organization(
    *,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    organization_id: int,
    current_user: User = Depends(get_current_active_user),  # noqa: B008
) -> Organization:
    """
    Get organization by ID.
    Users can only see organizations they belong to, unless they are admins or
    superusers.
    """
    organization_service = OrganizationService(db)

    # Check if user has access to the organization
    has_access = await organization_service.user_has_organization_access(
        current_user.id, organization_id
    )

    if not has_access and current_user.role != "superuser":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this organization",
        )

    organization = await organization_service.get_organization_by_id(organization_id)
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )
    return organization


@router.get("/", response_model=list[Organization])
async def read_organizations(
    *,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    current_user: User = Depends(get_current_active_user),  # noqa: B008
) -> list[Organization]:
    """
    Get all organizations.
    Regular users can only see their own organization.
    Admins can see all organizations.
    """
    organization_service = OrganizationService(db)

    # If superuser, return all organizations
    if current_user.role == "superuser":
        return await organization_service.get_all_organizations()

    # If user is in an organization, return just that one
    if current_user.organization_id is not None:
        org = await organization_service.get_organization_by_id(
            current_user.organization_id
        )
        return [cast(Organization, org)] if org else []

    # Otherwise, return empty list
    return []


@router.put("/{organization_id}", response_model=Organization)
async def update_organization(
    *,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    organization_id: int,
    organization_in: OrganizationUpdate,
    current_user: User = Depends(get_current_active_user),  # noqa: B008
) -> Organization:
    """
    Update an organization.
    Only admins or superusers can update organizations.
    Organization admins can only update their own organization.
    """
    organization_service = OrganizationService(db)

    # Check if user has admin access to the organization
    has_admin_access = await organization_service.user_has_organization_admin_access(
        current_user.id, organization_id
    )

    if not has_admin_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to update this organization",
        )

    organization = await organization_service.update_organization(
        org_id=organization_id,
        name=organization_in.name,
        description=organization_in.description,
    )
    return organization


@router.delete("/{organization_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organization(
    *,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    organization_id: int,
    current_user: User = Depends(get_current_active_superuser),  # noqa: B008
) -> None:
    """
    Delete an organization.
    Only superusers can delete organizations.
    Organizations with users cannot be deleted; users must be removed first.
    """
    organization_service = OrganizationService(db)
    result = await organization_service.delete_organization(organization_id)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete organization with users. Remove all users first.",
        )

    return None


@router.post("/{organization_id}/users/{user_id}", response_model=UserSchema, status_code=status.HTTP_200_OK)
async def add_user_to_organization(
    *,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    organization_id: int,
    user_id: int,
    current_user: User = Depends(get_current_active_user),  # noqa: B008
) -> UserSchema:
    """
    Add a user to an organization.
    Superusers can add any user to any organization.
    Organization admins can add users to their organization.
    """
    organization_service = OrganizationService(db)

    # Check if user can add users to this organization
    can_add = await organization_service.user_can_add_user_to_organization(
        current_user.id, organization_id, user_id
    )

    if not can_add:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to add users to this organization",
        )

    user = await organization_service.add_user_to_organization(
        user_id, organization_id, admin_user_id=current_user.id
    )
    return user


@router.delete("/{organization_id}/users/{user_id}", response_model=UserSchema)
async def remove_user_from_organization(
    *,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    organization_id: int,
    user_id: int,
    current_user: User = Depends(get_current_active_user),  # noqa: B008
) -> UserSchema:
    """
    Remove a user from their organization.
    Superusers can remove any user from any organization.
    Organization admins can remove users from their organization.
    """
    organization_service = OrganizationService(db)

    # Check if user has access to this organization
    has_access = await organization_service.user_has_organization_access(
        current_user.id, organization_id
    )

    if not has_access and current_user.role != "superuser":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this organization",
        )

    # Check if user can remove this user
    can_remove = await organization_service.user_can_remove_user_from_organization(
        current_user.id, user_id
    )

    if not can_remove:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to remove this user",
        )

    user = await organization_service.remove_user_from_organization(
        user_id, admin_user_id=current_user.id
    )
    return user


@router.get("/{organization_id}/users", response_model=list[UserSchema])
async def read_organization_users(
    *,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    organization_id: int,
    current_user: User = Depends(get_current_active_user),  # noqa: B008
) -> list[UserSchema]:
    """
    Get all users in an organization.
    Users can only see users in their own organization.
    Superusers can see users in any organization.
    """
    organization_service = OrganizationService(db)

    # Check if user has access to the organization
    has_access = await organization_service.user_has_organization_access(
        current_user.id, organization_id
    )

    if not has_access and current_user.role != "superuser":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this organization",
        )

    users = await organization_service.get_organization_users(organization_id)
    return users
