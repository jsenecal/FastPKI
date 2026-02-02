import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import CertificateType, UserRole
from app.services.ca import CAService
from app.services.cert import CertificateService
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
        username="certowner",
        email="certowner@example.com",
        password="password123",
        role=UserRole.USER,
        organization_id=org.id,
    )


@pytest_asyncio.fixture
async def ca(db: AsyncSession, org):
    ca_service = CAService(db)
    return await ca_service.create_ca(
        name="Test CA",
        subject_dn="CN=Test CA",
        organization_id=org.id,
    )


@pytest.mark.asyncio
async def test_create_certificate_with_ownership(db: AsyncSession, ca, org, user):
    cert_service = CertificateService(db)
    cert = await cert_service.create_certificate(
        ca_id=ca.id,
        common_name="test.example.com",
        subject_dn="CN=test.example.com",
        certificate_type=CertificateType.SERVER,
        organization_id=org.id,
        created_by_user_id=user.id,
    )
    assert cert.organization_id == org.id
    assert cert.created_by_user_id == user.id


@pytest.mark.asyncio
async def test_create_certificate_without_ownership(db: AsyncSession, ca):
    cert_service = CertificateService(db)
    cert = await cert_service.create_certificate(
        ca_id=ca.id,
        common_name="test.example.com",
        subject_dn="CN=test.example.com",
        certificate_type=CertificateType.SERVER,
    )
    assert cert.organization_id is None
    assert cert.created_by_user_id is None


@pytest.mark.asyncio
async def test_list_certificates_filtered_by_org(db: AsyncSession, ca, org):
    cert_service = CertificateService(db)
    await cert_service.create_certificate(
        ca_id=ca.id,
        common_name="org-cert.example.com",
        subject_dn="CN=org-cert.example.com",
        certificate_type=CertificateType.SERVER,
        organization_id=org.id,
    )
    await cert_service.create_certificate(
        ca_id=ca.id,
        common_name="other-cert.example.com",
        subject_dn="CN=other-cert.example.com",
        certificate_type=CertificateType.CLIENT,
    )
    filtered = await cert_service.list_certificates(organization_id=org.id)
    assert len(filtered) == 1
    assert filtered[0].common_name == "org-cert.example.com"


@pytest.mark.asyncio
async def test_list_certificates_unfiltered(db: AsyncSession, ca, org):
    cert_service = CertificateService(db)
    await cert_service.create_certificate(
        ca_id=ca.id,
        common_name="cert-a.example.com",
        subject_dn="CN=cert-a.example.com",
        certificate_type=CertificateType.SERVER,
        organization_id=org.id,
    )
    await cert_service.create_certificate(
        ca_id=ca.id,
        common_name="cert-b.example.com",
        subject_dn="CN=cert-b.example.com",
        certificate_type=CertificateType.CLIENT,
    )
    all_certs = await cert_service.list_certificates()
    assert len(all_certs) == 2
