import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import CertificateAuthority, Certificate, CertificateType, CertificateStatus
from app.services.ca import CAService
from app.services.cert import CertificateService


@pytest_asyncio.fixture
async def test_ca(db: AsyncSession) -> CertificateAuthority:
    """Create a test CA for certificate tests."""
    ca = await CAService.create_ca(
        db=db,
        name="Test CA for Certs",
        subject_dn="CN=Test CA for Certs,O=Test Organization,C=US",
        key_size=2048,
        valid_days=3650,
    )
    return ca


@pytest.mark.asyncio
async def test_create_certificate(db: AsyncSession, test_ca: CertificateAuthority):
    """Test creating a new certificate."""
    # Create a server certificate
    cert = await CertificateService.create_certificate(
        db=db,
        ca_id=test_ca.id,
        common_name="test.example.com",
        subject_dn="CN=test.example.com,O=Test Organization,C=US",
        certificate_type=CertificateType.SERVER,
        key_size=2048,
        valid_days=365,
    )
    
    # Check that the certificate was created with expected values
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
async def test_create_certificate_without_private_key(db: AsyncSession, test_ca: CertificateAuthority):
    """Test creating a new certificate without including the private key."""
    cert = await CertificateService.create_certificate(
        db=db,
        ca_id=test_ca.id,
        common_name="no-key.example.com",
        subject_dn="CN=no-key.example.com,O=Test Organization,C=US",
        certificate_type=CertificateType.SERVER,
        include_private_key=False,
    )
    
    # Check that the certificate was created without a private key
    assert cert.id is not None
    assert cert.common_name == "no-key.example.com"
    assert cert.private_key is None
    assert cert.certificate is not None


@pytest.mark.asyncio
async def test_get_certificate(db: AsyncSession, test_ca: CertificateAuthority):
    """Test retrieving a certificate by ID."""
    # First create a certificate
    created_cert = await CertificateService.create_certificate(
        db=db,
        ca_id=test_ca.id,
        common_name="get.example.com",
        subject_dn="CN=get.example.com,O=Test Organization,C=US",
        certificate_type=CertificateType.SERVER,
    )
    
    # Now retrieve it
    cert = await CertificateService.get_certificate(db, created_cert.id)
    
    # Check that we got the right certificate
    assert cert is not None
    assert cert.id == created_cert.id
    assert cert.common_name == "get.example.com"


@pytest.mark.asyncio
async def test_list_certificates(db: AsyncSession, test_ca: CertificateAuthority):
    """Test listing certificates."""
    # Create a few certificates
    for i in range(3):
        await CertificateService.create_certificate(
            db=db,
            ca_id=test_ca.id,
            common_name=f"list{i}.example.com",
            subject_dn=f"CN=list{i}.example.com,O=Test Organization,C=US",
            certificate_type=CertificateType.SERVER,
        )
    
    # List all certificates
    certs = await CertificateService.list_certificates(db)
    
    # Check that we got at least 3 certificates (might be more if other tests ran)
    assert len(certs) >= 3
    
    # List certificates filtered by CA
    certs = await CertificateService.list_certificates(db, ca_id=test_ca.id)
    
    # Check that all certificates have the right CA
    assert all(cert.issuer_id == test_ca.id for cert in certs)


@pytest.mark.asyncio
async def test_revoke_certificate(db: AsyncSession, test_ca: CertificateAuthority):
    """Test revoking a certificate."""
    # First create a certificate
    cert = await CertificateService.create_certificate(
        db=db,
        ca_id=test_ca.id,
        common_name="revoke.example.com",
        subject_dn="CN=revoke.example.com,O=Test Organization,C=US",
        certificate_type=CertificateType.SERVER,
    )
    
    # Revoke the certificate
    revoked_cert = await CertificateService.revoke_certificate(
        db, cert.id, reason="Key compromise"
    )
    
    # Check that the certificate was revoked
    assert revoked_cert is not None
    assert revoked_cert.id == cert.id
    assert revoked_cert.status == CertificateStatus.REVOKED
    assert revoked_cert.revoked_at is not None


@pytest.mark.asyncio
async def test_different_cert_types(db: AsyncSession, test_ca: CertificateAuthority):
    """Test creating different types of certificates."""
    # Create a client certificate
    client_cert = await CertificateService.create_certificate(
        db=db,
        ca_id=test_ca.id,
        common_name="client.example.com",
        subject_dn="CN=client.example.com,O=Test Organization,C=US",
        certificate_type=CertificateType.CLIENT,
    )
    
    assert client_cert.certificate_type == CertificateType.CLIENT
    
    # Create a CA certificate
    ca_cert = await CertificateService.create_certificate(
        db=db,
        ca_id=test_ca.id,
        common_name="subca.example.com",
        subject_dn="CN=subca.example.com,O=Test Organization,C=US",
        certificate_type=CertificateType.CA,
    )
    
    assert ca_cert.certificate_type == CertificateType.CA