from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

# mypy: disable-error-code="arg-type"
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from app.db.models import Organization, User, UserRole

UTC = ZoneInfo("UTC")


class OrganizationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_organization(
        self, name: str, description: Optional[str] = None
    ) -> Organization:
        """Create a new organization."""
        # Check if organization with this name already exists
        exists = await self.get_organization_by_name(name)
        if exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Organization with this name already exists",
            )

        # Create new organization
        org = Organization(
            name=name,
            description=description,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        self.db.add(org)
        await self.db.commit()
        await self.db.refresh(org)
        return org

    async def get_organization_by_id(self, org_id: int) -> Optional[Organization]:
        """Get an organization by ID."""
        query = select(Organization).where(Organization.id == org_id)  # type: ignore
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_organization_by_name(self, name: str) -> Optional[Organization]:
        """Get an organization by name."""
        query = select(Organization).where(Organization.name == name)  # type: ignore
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_all_organizations(self) -> list[Organization]:
        """Get all organizations."""
        query = select(Organization).order_by(Organization.name)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_organization(
        self,
        org_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Organization:
        """Update an organization."""
        org = await self.get_organization_by_id(org_id)
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found",
            )

        # Check for name uniqueness if name is being updated
        if name and name != org.name:
            exists = await self.get_organization_by_name(name)
            if exists:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Organization with this name already exists",
                )
            org.name = name

        if description is not None:
            org.description = description

        org.updated_at = datetime.now(UTC)
        self.db.add(org)
        await self.db.commit()
        await self.db.refresh(org)
        return org

    async def delete_organization(self, org_id: int) -> bool:
        """Delete an organization."""
        org = await self.get_organization_by_id(org_id)
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found",
            )

        # Check if there are users in the organization
        users = await self.get_organization_users(org_id)
        if users:
            # We could either fail, automatically remove users,
            # or force the caller to handle it
            # For now, we'll fail to avoid unexpected behavior
            return False

        await self.db.delete(org)
        await self.db.commit()
        return True

    async def add_user_to_organization(
        self, user_id: int, org_id: int, admin_user_id: Optional[int] = None
    ) -> User:
        """Add a user to an organization."""
        # Check if organization exists
        org = await self.get_organization_by_id(org_id)
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found",
            )

        # Get the user
        query = select(User).where(User.id == user_id)
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        # If an admin_user_id is provided, ensure they have the right to add users
        if admin_user_id:
            can_add = await self.user_can_add_user_to_organization(
                admin_user_id, org_id, user_id
            )
            if not can_add:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have permission to add users to this org",
                )

        # Update the user's organization
        user.organization_id = org_id
        user.updated_at = datetime.now(UTC)

        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def remove_user_from_organization(
        self, user_id: int, admin_user_id: Optional[int] = None
    ) -> User:
        """Remove a user from their organization."""
        # Get the user
        query = select(User).where(User.id == user_id)
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        if user.organization_id is None:
            # User is not in any organization, nothing to do
            return user

        # If an admin_user_id is provided, ensure they have the right to remove users
        if admin_user_id:
            can_remove = await self.user_can_remove_user_from_organization(
                admin_user_id, user_id
            )
            if not can_remove:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have permission to remove this user",
                )

        # Update the user's organization
        user.organization_id = None
        user.updated_at = datetime.now(UTC)

        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def get_organization_users(self, org_id: int) -> list[User]:
        """Get all users in an organization."""
        query = select(User).where(User.organization_id == org_id)  # type: ignore
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_organization_user_count(self, org_id: int) -> int:
        """Get the count of users in an organization."""
        query = select(func.count(User.id)).where(User.organization_id == org_id)  # type: ignore
        result = await self.db.execute(query)
        return result.scalar_one()

    async def user_has_organization_access(self, user_id: int, org_id: int) -> bool:
        """Check if a user has access to an organization."""
        # Get the user
        query = select(User).where(User.id == user_id)
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            return False

        # Superusers have access to all organizations
        if user.role == UserRole.SUPERUSER:
            return True

        # Users with the organization ID have access
        return user.organization_id == org_id

    async def user_has_organization_admin_access(
        self, user_id: int, org_id: int
    ) -> bool:
        """
        Check if a user has admin access to an organization.

        A user has admin access if:
        1. They are a superuser
        2. They are an admin and belong to the organization
        """
        # Get the user
        query = select(User).where(User.id == user_id)
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            return False

        # Superusers have admin access to all organizations
        if user.role == UserRole.SUPERUSER:
            return True

        # Only admins have admin access, and they must be in the organization
        return user.role == UserRole.ADMIN and user.organization_id == org_id

    async def user_can_add_user_to_organization(
        self, admin_user_id: int, org_id: int, user_id: int
    ) -> bool:
        """Check if a user can add another user to an organization."""
        # Get the admin user
        query = select(User).where(User.id == admin_user_id)
        result = await self.db.execute(query)
        admin_user = result.scalar_one_or_none()

        if not admin_user:
            return False

        # Superusers can add users to any organization
        if admin_user.role == UserRole.SUPERUSER:
            return True

        # Organization admins can only add users to their organization
        return (
            admin_user.role == UserRole.ADMIN and admin_user.organization_id == org_id
        )

    async def user_can_remove_user_from_organization(
        self, admin_user_id: int, user_id: int
    ) -> bool:
        """Check if a user can remove another user from an organization."""
        # Get both users
        admin_query = select(User).where(User.id == admin_user_id)  # type: ignore
        user_query = select(User).where(User.id == user_id)  # type: ignore

        admin_result = await self.db.execute(admin_query)
        user_result = await self.db.execute(user_query)

        admin_user = admin_result.scalar_one_or_none()
        user = user_result.scalar_one_or_none()

        if not admin_user or not user or user.organization_id is None:
            return False

        # Superusers can remove any user from any organization
        if admin_user.role == UserRole.SUPERUSER:
            return True

        # Organization admins can only remove users from their organization
        return (
            admin_user.role == UserRole.ADMIN
            and admin_user.organization_id == user.organization_id
        )
