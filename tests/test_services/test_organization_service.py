from datetime import UTC, datetime

import pytest

from app.db.models import UserRole
from app.services.organization import OrganizationService
from app.services.user import UserService


@pytest.mark.asyncio
async def test_create_organization(db):
    # Test creating a new organization
    org_service = OrganizationService(db)
    new_org = await org_service.create_organization(
        name="Test Organization",
        description="This is a test organization"
    )

    assert new_org.id is not None
    assert new_org.name == "Test Organization"
    assert new_org.description == "This is a test organization"
    assert new_org.created_at is not None
    assert isinstance(new_org.created_at, datetime)


@pytest.mark.asyncio
async def test_get_organization_by_id(db):
    # Create an organization first
    org_service = OrganizationService(db)
    created_org = await org_service.create_organization(
        name="Get By ID Org",
        description="This is an organization to retrieve by ID"
    )

    # Get the organization by ID
    org = await org_service.get_organization_by_id(created_org.id)

    assert org is not None
    assert org.id == created_org.id
    assert org.name == "Get By ID Org"
    assert org.description == "This is an organization to retrieve by ID"


@pytest.mark.asyncio
async def test_get_organization_by_name(db):
    # Create an organization first
    org_service = OrganizationService(db)
    await org_service.create_organization(
        name="Get By Name Org",
        description="This is an organization to retrieve by name"
    )

    # Get the organization by name
    org = await org_service.get_organization_by_name("Get By Name Org")

    assert org is not None
    assert org.name == "Get By Name Org"
    assert org.description == "This is an organization to retrieve by name"


@pytest.mark.asyncio
async def test_get_all_organizations(db):
    # Create multiple organizations
    org_service = OrganizationService(db)
    await org_service.create_organization(name="Org 1", description="First org")
    await org_service.create_organization(name="Org 2", description="Second org")
    await org_service.create_organization(name="Org 3", description="Third org")

    # Get all organizations
    organizations = await org_service.get_all_organizations()

    assert len(organizations) >= 3
    # Check if our organizations are in the list
    org_names = [org.name for org in organizations]
    assert "Org 1" in org_names
    assert "Org 2" in org_names
    assert "Org 3" in org_names


@pytest.mark.asyncio
async def test_update_organization(db):
    # Create an organization first
    org_service = OrganizationService(db)
    created_org = await org_service.create_organization(
        name="Update Org",
        description="This organization will be updated"
    )

    # Update the organization
    updated_org = await org_service.update_organization(
        created_org.id,
        name="Updated Org Name",
        description="This organization has been updated"
    )

    assert updated_org.id == created_org.id
    assert updated_org.name == "Updated Org Name"
    assert updated_org.description == "This organization has been updated"
    # Check that updated_at has been modified
    assert updated_org.updated_at > created_org.created_at


@pytest.mark.asyncio
async def test_delete_organization(db):
    # Create an organization first
    org_service = OrganizationService(db)
    created_org = await org_service.create_organization(
        name="Delete Org",
        description="This organization will be deleted"
    )

    # Delete the organization
    result = await org_service.delete_organization(created_org.id)
    assert result is True

    # Verify organization is deleted
    org = await org_service.get_organization_by_id(created_org.id)
    assert org is None


@pytest.mark.asyncio
async def test_add_user_to_organization(db):
    # Create a user and an organization first
    user_service = UserService(db)
    org_service = OrganizationService(db)
    
    user = await user_service.create_user(
        username="orguser",
        email="orguser@example.com",
        password="password123",
        role=UserRole.USER
    )
    
    org = await org_service.create_organization(
        name="User's Org",
        description="Organization for testing user membership"
    )
    
    # Add user to organization
    updated_user = await org_service.add_user_to_organization(user.id, org.id)
    
    assert updated_user is not None
    assert updated_user.organization_id == org.id
    
    # Verify through the user service as well
    retrieved_user = await user_service.get_user_by_id(user.id)
    assert retrieved_user.organization_id == org.id


@pytest.mark.asyncio
async def test_remove_user_from_organization(db):
    # Create a user and an organization first
    user_service = UserService(db)
    org_service = OrganizationService(db)
    
    user = await user_service.create_user(
        username="removeuser",
        email="removeuser@example.com",
        password="password123"
    )
    
    org = await org_service.create_organization(
        name="Remove Org",
        description="Organization for testing user removal"
    )
    
    # Add user to organization first
    await org_service.add_user_to_organization(user.id, org.id)
    
    # Now remove user from organization
    updated_user = await org_service.remove_user_from_organization(user.id)
    
    assert updated_user is not None
    assert updated_user.organization_id is None
    
    # Verify through the user service as well
    retrieved_user = await user_service.get_user_by_id(user.id)
    assert retrieved_user.organization_id is None


@pytest.mark.asyncio
async def test_get_organization_users(db):
    # Create an organization and multiple users
    user_service = UserService(db)
    org_service = OrganizationService(db)
    
    org = await org_service.create_organization(
        name="Multi-User Org",
        description="Organization with multiple users"
    )
    
    # Create users and add them to the organization
    user1 = await user_service.create_user(
        username="orguser1",
        email="orguser1@example.com",
        password="password123"
    )
    user2 = await user_service.create_user(
        username="orguser2",
        email="orguser2@example.com",
        password="password123"
    )
    user3 = await user_service.create_user(
        username="orguser3",
        email="orguser3@example.com",
        password="password123"
    )
    
    await org_service.add_user_to_organization(user1.id, org.id)
    await org_service.add_user_to_organization(user2.id, org.id)
    await org_service.add_user_to_organization(user3.id, org.id)
    
    # Get all users for the organization
    org_users = await org_service.get_organization_users(org.id)
    
    assert len(org_users) == 3
    
    # Verify correct users are in the list
    usernames = [user.username for user in org_users]
    assert "orguser1" in usernames
    assert "orguser2" in usernames
    assert "orguser3" in usernames