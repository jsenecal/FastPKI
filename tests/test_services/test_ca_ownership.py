import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import UserRole
from app.services.ca import CAService
from app.services.organization import OrganizationService
from app.services.user import UserService


@pytest_asyncio.fixture
async def org(db: AsyncSession):
    org_service = OrganizationService(db)
    return await org_service.create_organization(name="TestOrg", description="Test")


@pytest_asyncio.fixture
async def user(db: AsyncSession, org):
    user_service = UserService(db)
    return await user_service.create_user(
        username="caowner",
        email="caowner@example.com",
        password="password123",
        role=UserRole.USER,
        organization_id=org.id,
    )


@pytest.mark.asyncio
async def test_create_ca_with_ownership(db: AsyncSession, org, user):
    ca_service = CAService(db)
    ca = await ca_service.create_ca(
        name="Owned CA",
        subject_dn="CN=Owned CA",
        organization_id=org.id,
        created_by_user_id=user.id,
    )
    assert ca.organization_id == org.id
    assert ca.created_by_user_id == user.id


@pytest.mark.asyncio
async def test_create_ca_without_ownership(db: AsyncSession):
    ca_service = CAService(db)
    ca = await ca_service.create_ca(
        name="Unowned CA",
        subject_dn="CN=Unowned CA",
    )
    assert ca.organization_id is None
    assert ca.created_by_user_id is None


@pytest.mark.asyncio
async def test_list_cas_filtered_by_org(db: AsyncSession, org):
    ca_service = CAService(db)
    await ca_service.create_ca(
        name="Org CA",
        subject_dn="CN=Org CA",
        organization_id=org.id,
    )
    await ca_service.create_ca(
        name="Other CA",
        subject_dn="CN=Other CA",
    )
    filtered = await ca_service.list_cas(organization_id=org.id)
    assert len(filtered) == 1
    assert filtered[0].name == "Org CA"


@pytest.mark.asyncio
async def test_list_cas_unfiltered(db: AsyncSession, org):
    ca_service = CAService(db)
    await ca_service.create_ca(
        name="CA A",
        subject_dn="CN=CA A",
        organization_id=org.id,
    )
    await ca_service.create_ca(
        name="CA B",
        subject_dn="CN=CA B",
    )
    all_cas = await ca_service.list_cas()
    assert len(all_cas) == 2
