import pytest
import pytest_asyncio
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import Organization, User, UserRole
from app.services.organization import OrganizationService
from app.services.user import UserService


@pytest_asyncio.fixture
async def direct_test_org(db: AsyncSession) -> Organization:
    """Create a test organization directly."""
    org_service = OrganizationService(db)
    org = await org_service.create_organization(
        name="Direct Test Org",
        description="A test organization created directly",
    )
    return org


@pytest_asyncio.fixture
async def direct_admin_user(db: AsyncSession) -> User:
    """Create a test admin user directly."""
    user_service = UserService(db)
    user = await user_service.create_user(
        username="directadmin",
        email="directadmin@example.com",
        password="password123",
        role=UserRole.ADMIN,
    )
    return user


@pytest_asyncio.fixture
async def direct_superuser(db: AsyncSession) -> User:
    """Create a test superuser directly."""
    user_service = UserService(db)
    user = await user_service.create_user(
        username="directsuper",
        email="directsuper@example.com",
        password="password123",
        role=UserRole.SUPERUSER,
    )
    return user


@pytest_asyncio.fixture
async def direct_normal_user(db: AsyncSession) -> User:
    """Create a test normal user directly."""
    user_service = UserService(db)
    user = await user_service.create_user(
        username="directuser",
        email="directuser@example.com",
        password="password123",
        role=UserRole.USER,
    )
    return user


@pytest_asyncio.fixture
async def direct_user_in_org(db: AsyncSession, direct_test_org: Organization) -> User:
    """Create a test user who belongs to an organization."""
    user_service = UserService(db)
    user = await user_service.create_user(
        username="directorguser",
        email="directorguser@example.com",
        password="password123",
        role=UserRole.USER,
        organization_id=direct_test_org.id,
    )
    return user


@pytest.mark.asyncio
async def test_organization_service_create(db: AsyncSession):
    """Test creating an organization using the service directly."""
    org_service = OrganizationService(db)
    org = await org_service.create_organization(
        name="Service Test Org",
        description="A test organization created with the service",
    )
    
    assert org.id is not None
    assert org.name == "Service Test Org"
    assert org.description == "A test organization created with the service"
    assert org.created_at is not None
    assert org.updated_at is not None


@pytest.mark.asyncio
async def test_organization_service_get_by_id(db: AsyncSession, direct_test_org: Organization):
    """Test getting an organization by ID using the service directly."""
    org_service = OrganizationService(db)
    org = await org_service.get_organization_by_id(direct_test_org.id)
    
    assert org is not None
    assert org.id == direct_test_org.id
    assert org.name == direct_test_org.name


@pytest.mark.asyncio
async def test_organization_service_get_by_name(db: AsyncSession, direct_test_org: Organization):
    """Test getting an organization by name using the service directly."""
    org_service = OrganizationService(db)
    org = await org_service.get_organization_by_name(direct_test_org.name)
    
    assert org is not None
    assert org.id == direct_test_org.id
    assert org.name == direct_test_org.name


@pytest.mark.asyncio
async def test_organization_service_get_all(db: AsyncSession, direct_test_org: Organization):
    """Test getting all organizations using the service directly."""
    org_service = OrganizationService(db)
    orgs = await org_service.get_all_organizations()
    
    assert len(orgs) >= 1
    assert any(org.id == direct_test_org.id for org in orgs)


@pytest.mark.asyncio
async def test_organization_service_update(db: AsyncSession, direct_test_org: Organization):
    """Test updating an organization using the service directly."""
    org_service = OrganizationService(db)
    updated_org = await org_service.update_organization(
        org_id=direct_test_org.id,
        name="Updated Direct Test Org",
        description="Updated description",
    )
    
    assert updated_org.id == direct_test_org.id
    assert updated_org.name == "Updated Direct Test Org"
    assert updated_org.description == "Updated description"
    assert updated_org.updated_at > direct_test_org.updated_at


@pytest.mark.asyncio
async def test_organization_service_add_user(db: AsyncSession, direct_test_org: Organization, direct_normal_user: User):
    """Test adding a user to an organization using the service directly."""
    org_service = OrganizationService(db)
    user = await org_service.add_user_to_organization(
        user_id=direct_normal_user.id,
        org_id=direct_test_org.id,
    )
    
    assert user.id == direct_normal_user.id
    assert user.organization_id == direct_test_org.id


@pytest.mark.asyncio
async def test_organization_service_remove_user(db: AsyncSession, direct_test_org: Organization, direct_user_in_org: User):
    """Test removing a user from an organization using the service directly."""
    org_service = OrganizationService(db)
    user = await org_service.remove_user_from_organization(
        user_id=direct_user_in_org.id,
    )
    
    assert user.id == direct_user_in_org.id
    assert user.organization_id is None


@pytest.mark.asyncio
async def test_organization_service_get_users(db: AsyncSession, direct_test_org: Organization, direct_user_in_org: User):
    """Test getting all users in an organization using the service directly."""
    org_service = OrganizationService(db)
    users = await org_service.get_organization_users(direct_test_org.id)
    
    assert len(users) >= 1
    assert any(user.id == direct_user_in_org.id for user in users)


@pytest.mark.asyncio
async def test_organization_service_user_count(db: AsyncSession, direct_test_org: Organization, direct_user_in_org: User):
    """Test getting the count of users in an organization using the service directly."""
    org_service = OrganizationService(db)
    count = await org_service.get_organization_user_count(direct_test_org.id)
    
    assert count >= 1


@pytest.mark.asyncio
async def test_organization_service_has_access(db: AsyncSession, direct_test_org: Organization, direct_user_in_org: User):
    """Test checking if a user has access to an organization using the service directly."""
    org_service = OrganizationService(db)
    has_access = await org_service.user_has_organization_access(
        user_id=direct_user_in_org.id,
        org_id=direct_test_org.id,
    )
    
    assert has_access is True


@pytest.mark.asyncio
async def test_organization_service_superuser_has_access(db: AsyncSession, direct_test_org: Organization, direct_superuser: User):
    """Test that a superuser has access to any organization."""
    org_service = OrganizationService(db)
    has_access = await org_service.user_has_organization_access(
        user_id=direct_superuser.id,
        org_id=direct_test_org.id,
    )
    
    assert has_access is True


@pytest.mark.asyncio
async def test_organization_service_has_admin_access(db: AsyncSession, direct_test_org: Organization, direct_admin_user: User):
    """Test checking if a user has admin access to an organization."""
    org_service = OrganizationService(db)
    
    # First add the admin user to the organization
    await org_service.add_user_to_organization(
        user_id=direct_admin_user.id,
        org_id=direct_test_org.id,
    )
    
    has_admin_access = await org_service.user_has_organization_admin_access(
        user_id=direct_admin_user.id,
        org_id=direct_test_org.id,
    )
    
    assert has_admin_access is True