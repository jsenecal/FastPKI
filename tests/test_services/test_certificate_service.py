import pytest
import pytest_asyncio
from cryptography import x509
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    CertificateAuthority,
    CertificateStatus,
    CertificateType,
)
from app.services.ca import CAService
from app.services.cert import CertificateService


@pytest_asyncio.fixture
async def test_ca(db: AsyncSession) -> CertificateAuthority:
    """Create a test CA for certificate tests."""
    ca_service = CAService(db)
    ca = await ca_service.create_ca(
        name="Test CA for Certs",
        subject_dn="CN=Test CA for Certs,O=Test Organization,C=US",
        key_size=2048,
        valid_days=3650,
    )
    return ca


@pytest.mark.asyncio
async def test_create_certificate(db: AsyncSession, test_ca: CertificateAuthority):
    """Test creating a new certificate."""
    cert_service = CertificateService(db)
    cert = await cert_service.create_certificate(
        ca_id=test_ca.id,
        common_name="test.example.com",
        subject_dn="CN=test.example.com,O=Test Organization,C=US",
        certificate_type=CertificateType.SERVER,
        key_size=2048,
        valid_days=365,
    )

    assert cert.id is not None
    assert cert.common_name == "test.example.com"
    assert cert.subject_dn == "CN=test.example.com,O=Test Organization,C=US"
    assert cert.certificate_type == CertificateType.SERVER
    assert cert.key_size == 2048
    assert cert.valid_days == 365
    assert cert.status == CertificateStatus.VALID
    assert cert.private_key is not None
    assert cert.certificate is not None
    assert cert.serial_number is not None
    assert cert.not_before is not None
    assert cert.not_after is not None
    assert cert.issuer_id == test_ca.id


@pytest.mark.asyncio
async def test_create_certificate_without_private_key(
    db: AsyncSession, test_ca: CertificateAuthority
):
    """Test creating a new certificate without including the private key."""
    cert_service = CertificateService(db)
    cert = await cert_service.create_certificate(
        ca_id=test_ca.id,
        common_name="no-key.example.com",
        subject_dn="CN=no-key.example.com,O=Test Organization,C=US",
        certificate_type=CertificateType.SERVER,
        include_private_key=False,
    )

    assert cert.id is not None
    assert cert.common_name == "no-key.example.com"
    assert cert.private_key is None
    assert cert.certificate is not None


@pytest.mark.asyncio
async def test_get_certificate(db: AsyncSession, test_ca: CertificateAuthority):
    """Test retrieving a certificate by ID."""
    cert_service = CertificateService(db)
    created_cert = await cert_service.create_certificate(
        ca_id=test_ca.id,
        common_name="get.example.com",
        subject_dn="CN=get.example.com,O=Test Organization,C=US",
        certificate_type=CertificateType.SERVER,
    )

    cert = await cert_service.get_certificate(created_cert.id)

    assert cert is not None
    assert cert.id == created_cert.id
    assert cert.common_name == "get.example.com"


@pytest.mark.asyncio
async def test_list_certificates(db: AsyncSession, test_ca: CertificateAuthority):
    """Test listing certificates."""
    cert_service = CertificateService(db)
    for i in range(3):
        await cert_service.create_certificate(
            ca_id=test_ca.id,
            common_name=f"list{i}.example.com",
            subject_dn=f"CN=list{i}.example.com,O=Test Organization,C=US",
            certificate_type=CertificateType.SERVER,
        )

    certs = await cert_service.list_certificates()

    assert len(certs) >= 3

    certs = await cert_service.list_certificates(ca_id=test_ca.id)

    assert all(cert.issuer_id == test_ca.id for cert in certs)


@pytest.mark.asyncio
async def test_revoke_certificate(db: AsyncSession, test_ca: CertificateAuthority):
    """Test revoking a certificate."""
    cert_service = CertificateService(db)
    cert = await cert_service.create_certificate(
        ca_id=test_ca.id,
        common_name="revoke.example.com",
        subject_dn="CN=revoke.example.com,O=Test Organization,C=US",
        certificate_type=CertificateType.SERVER,
    )

    revoked_cert = await cert_service.revoke_certificate(
        cert.id, reason="Key compromise"
    )

    assert revoked_cert is not None
    assert revoked_cert.id == cert.id
    assert revoked_cert.status == CertificateStatus.REVOKED
    assert revoked_cert.revoked_at is not None


@pytest.mark.asyncio
async def test_double_revocation(db: AsyncSession, test_ca: CertificateAuthority):
    """Test that revoking an already-revoked certificate raises ValueError."""
    cert_service = CertificateService(db)
    cert = await cert_service.create_certificate(
        ca_id=test_ca.id,
        common_name="double-revoke.example.com",
        subject_dn="CN=double-revoke.example.com,O=Test Organization,C=US",
        certificate_type=CertificateType.SERVER,
    )

    await cert_service.revoke_certificate(cert.id, reason="Key compromise")

    with pytest.raises(ValueError, match="already revoked"):
        await cert_service.revoke_certificate(cert.id, reason="Duplicate")


@pytest.mark.asyncio
async def test_different_cert_types(db: AsyncSession, test_ca: CertificateAuthority):
    """Test creating different types of certificates."""
    cert_service = CertificateService(db)

    client_cert = await cert_service.create_certificate(
        ca_id=test_ca.id,
        common_name="client.example.com",
        subject_dn="CN=client.example.com,O=Test Organization,C=US",
        certificate_type=CertificateType.CLIENT,
    )

    assert client_cert.certificate_type == CertificateType.CLIENT

    ca_cert = await cert_service.create_certificate(
        ca_id=test_ca.id,
        common_name="subca.example.com",
        subject_dn="CN=subca.example.com,O=Test Organization,C=US",
        certificate_type=CertificateType.CA,
    )

    assert ca_cert.certificate_type == CertificateType.CA


@pytest.mark.asyncio
async def test_dual_purpose_cert_has_both_ekus(
    db: AsyncSession, test_ca: CertificateAuthority
):
    """Test that dual_purpose certs have both SERVER_AUTH and CLIENT_AUTH EKUs."""
    cert_service = CertificateService(db)
    cert = await cert_service.create_certificate(
        ca_id=test_ca.id,
        common_name="peer.example.com",
        subject_dn="CN=peer.example.com,O=Test Organization,C=US",
        certificate_type=CertificateType.DUAL_PURPOSE,
    )

    assert cert.certificate_type == CertificateType.DUAL_PURPOSE

    # Parse the X.509 certificate and check EKUs
    x509_cert = x509.load_pem_x509_certificate(cert.certificate.encode("utf-8"))
    eku_ext = x509_cert.extensions.get_extension_for_class(x509.ExtendedKeyUsage)
    ekus = list(eku_ext.value)

    assert ExtendedKeyUsageOID.SERVER_AUTH in ekus
    assert ExtendedKeyUsageOID.CLIENT_AUTH in ekus


def test_parse_subject_dn_escaped_comma():
    """Test that escaped commas in DN values are handled correctly."""
    name = CAService.parse_subject_dn("CN=Doe\\, John,O=Test Org,C=US")
    cn = name.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
    assert cn == "Doe, John"
    org = name.get_attributes_for_oid(NameOID.ORGANIZATION_NAME)[0].value
    assert org == "Test Org"
