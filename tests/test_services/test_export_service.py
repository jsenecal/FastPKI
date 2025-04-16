import pytest
import pytest_asyncio
from fastapi import Response
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import CertificateAuthority, Certificate, CertificateType
from app.services.ca import CAService
from app.services.cert import CertificateService


@pytest_asyncio.fixture
async def export_test_ca(db: AsyncSession) -> CertificateAuthority:
    """Create a test CA for export tests."""
    ca = await CAService.create_ca(
        db=db,
        name="Export Test CA",
        subject_dn="CN=Export Test CA,O=Test Organization,C=US",
        key_size=2048,
        valid_days=3650,
    )
    return ca


@pytest_asyncio.fixture
async def export_test_cert(db: AsyncSession, export_test_ca: CertificateAuthority) -> Certificate:
    """Create a test certificate for export tests."""
    cert = await CertificateService.create_certificate(
        db=db,
        ca_id=export_test_ca.id,
        common_name="export.example.com",
        subject_dn="CN=export.example.com,O=Test Organization,C=US",
        certificate_type=CertificateType.SERVER,
        key_size=2048,
        valid_days=365,
    )
    return cert


@pytest_asyncio.fixture
async def export_test_cert_without_key(db: AsyncSession, export_test_ca: CertificateAuthority) -> Certificate:
    """Create a test certificate without private key for export tests."""
    cert = await CertificateService.create_certificate(
        db=db,
        ca_id=export_test_ca.id,
        common_name="export-no-key.example.com",
        subject_dn="CN=export-no-key.example.com,O=Test Organization,C=US",
        certificate_type=CertificateType.SERVER,
        include_private_key=False,
    )
    return cert


@pytest.mark.asyncio
async def test_export_ca_certificate(client: AsyncClient, export_test_ca: CertificateAuthority):
    """Test exporting a CA certificate."""
    response = await client.get(
        f"{settings.API_V1_STR}/export/ca/{export_test_ca.id}/certificate"
    )
    
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/x-pem-file"
    assert f"ca_{export_test_ca.id}_certificate.pem" in response.headers["Content-Disposition"]
    assert "BEGIN CERTIFICATE" in response.text
    assert "END CERTIFICATE" in response.text


@pytest.mark.asyncio
async def test_export_ca_private_key(client: AsyncClient, export_test_ca: CertificateAuthority):
    """Test exporting a CA private key."""
    response = await client.get(
        f"{settings.API_V1_STR}/export/ca/{export_test_ca.id}/private-key"
    )
    
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/x-pem-file"
    assert f"ca_{export_test_ca.id}_private_key.pem" in response.headers["Content-Disposition"]
    assert "BEGIN PRIVATE KEY" in response.text
    assert "END PRIVATE KEY" in response.text


@pytest.mark.asyncio
async def test_export_certificate(client: AsyncClient, export_test_cert: Certificate):
    """Test exporting a certificate."""
    response = await client.get(
        f"{settings.API_V1_STR}/export/certificate/{export_test_cert.id}"
    )
    
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/x-pem-file"
    assert f"certificate_{export_test_cert.id}.pem" in response.headers["Content-Disposition"]
    assert "BEGIN CERTIFICATE" in response.text
    assert "END CERTIFICATE" in response.text


@pytest.mark.asyncio
async def test_export_certificate_private_key(client: AsyncClient, export_test_cert: Certificate):
    """Test exporting a certificate private key."""
    response = await client.get(
        f"{settings.API_V1_STR}/export/certificate/{export_test_cert.id}/private-key"
    )
    
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/x-pem-file"
    assert f"certificate_{export_test_cert.id}_private_key.pem" in response.headers["Content-Disposition"]
    assert "BEGIN PRIVATE KEY" in response.text
    assert "END PRIVATE KEY" in response.text


@pytest.mark.asyncio
async def test_export_certificate_without_private_key(client: AsyncClient, export_test_cert_without_key: Certificate):
    """Test exporting a certificate that doesn't have a private key."""
    response = await client.get(
        f"{settings.API_V1_STR}/export/certificate/{export_test_cert_without_key.id}/private-key"
    )
    
    assert response.status_code == 404
    assert "does not have a private key" in response.json()["detail"]


@pytest.mark.asyncio
async def test_export_certificate_chain(client: AsyncClient, export_test_cert: Certificate):
    """Test exporting a certificate chain."""
    response = await client.get(
        f"{settings.API_V1_STR}/export/certificate/{export_test_cert.id}/chain"
    )
    
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/x-pem-file"
    assert f"certificate_{export_test_cert.id}_chain.pem" in response.headers["Content-Disposition"]
    assert "BEGIN CERTIFICATE" in response.text
    assert "END CERTIFICATE" in response.text
    # Chain should contain at least 2 certificates (the cert itself and the CA)
    assert response.text.count("BEGIN CERTIFICATE") >= 2


@pytest.mark.asyncio
async def test_export_nonexistent_ca(client: AsyncClient):
    """Test exporting a nonexistent CA."""
    response = await client.get(
        f"{settings.API_V1_STR}/export/ca/9999/certificate"
    )
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_export_nonexistent_certificate(client: AsyncClient):
    """Test exporting a nonexistent certificate."""
    response = await client.get(
        f"{settings.API_V1_STR}/export/certificate/9999"
    )
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]