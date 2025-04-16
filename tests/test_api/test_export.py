import pytest
from fastapi import status
from httpx import AsyncClient

from app.core.config import settings
from app.db.models import CertificateType


@pytest.mark.asyncio
async def test_export_ca_certificate(client: AsyncClient):
    """Test exporting a CA certificate in PEM format."""
    # First create a CA
    ca_data = {
        "name": "Export Test CA",
        "subject_dn": "CN=Export Test CA,O=Test Organization,C=US",
    }

    response = await client.post(
        f"{settings.API_V1_STR}/cas/",
        json=ca_data,
    )
    assert response.status_code == status.HTTP_201_CREATED
    created_ca = response.json()
    ca_id = created_ca["id"]

    # Now test exporting the CA certificate
    response = await client.get(f"{settings.API_V1_STR}/export/ca/{ca_id}/certificate")

    assert response.status_code == status.HTTP_200_OK
    assert response.headers["Content-Type"] == "application/x-pem-file"
    assert (
        response.headers["Content-Disposition"]
        == f"attachment; filename=ca_{ca_id}_certificate.pem"
    )
    assert "-----BEGIN CERTIFICATE-----" in response.text
    assert "-----END CERTIFICATE-----" in response.text


@pytest.mark.asyncio
async def test_export_ca_private_key(client: AsyncClient):
    """Test exporting a CA private key in PEM format."""
    # First create a CA
    ca_data = {
        "name": "Export Key Test CA",
        "subject_dn": "CN=Export Key Test CA,O=Test Organization,C=US",
    }

    response = await client.post(
        f"{settings.API_V1_STR}/cas/",
        json=ca_data,
    )
    assert response.status_code == status.HTTP_201_CREATED
    created_ca = response.json()
    ca_id = created_ca["id"]

    # Now test exporting the CA private key
    response = await client.get(f"{settings.API_V1_STR}/export/ca/{ca_id}/private-key")

    assert response.status_code == status.HTTP_200_OK
    assert response.headers["Content-Type"] == "application/x-pem-file"
    assert (
        response.headers["Content-Disposition"]
        == f"attachment; filename=ca_{ca_id}_private_key.pem"
    )
    assert "-----BEGIN PRIVATE KEY-----" in response.text
    assert "-----END PRIVATE KEY-----" in response.text


@pytest.mark.asyncio
async def test_export_certificate(client: AsyncClient):
    """Test exporting a certificate in PEM format."""
    # First create a CA
    ca_data = {
        "name": "Cert Export Test CA",
        "subject_dn": "CN=Cert Export Test CA,O=Test Organization,C=US",
    }

    response = await client.post(
        f"{settings.API_V1_STR}/cas/",
        json=ca_data,
    )
    assert response.status_code == status.HTTP_201_CREATED
    created_ca = response.json()
    ca_id = created_ca["id"]

    # Then create a certificate
    cert_data = {
        "common_name": "test-export.example.com",
        "subject_dn": "CN=test-export.example.com,O=Test Organization,C=US",
        "certificate_type": "server",
    }

    response = await client.post(
        f"{settings.API_V1_STR}/certificates/?ca_id={ca_id}",
        json=cert_data,
    )
    assert response.status_code == status.HTTP_201_CREATED
    created_cert = response.json()
    cert_id = created_cert["id"]

    # Now test exporting the certificate
    response = await client.get(f"{settings.API_V1_STR}/export/certificate/{cert_id}")

    assert response.status_code == status.HTTP_200_OK
    assert response.headers["Content-Type"] == "application/x-pem-file"
    assert (
        response.headers["Content-Disposition"]
        == f"attachment; filename=certificate_{cert_id}.pem"
    )
    assert "-----BEGIN CERTIFICATE-----" in response.text
    assert "-----END CERTIFICATE-----" in response.text


@pytest.mark.asyncio
async def test_export_certificate_private_key(client: AsyncClient):
    """Test exporting a certificate's private key in PEM format."""
    # First create a CA
    ca_data = {
        "name": "Key Export Test CA",
        "subject_dn": "CN=Key Export Test CA,O=Test Organization,C=US",
    }

    response = await client.post(
        f"{settings.API_V1_STR}/cas/",
        json=ca_data,
    )
    assert response.status_code == status.HTTP_201_CREATED
    created_ca = response.json()
    ca_id = created_ca["id"]

    # Then create a certificate with private key
    cert_data = {
        "common_name": "key-export.example.com",
        "subject_dn": "CN=key-export.example.com,O=Test Organization,C=US",
        "certificate_type": "server",
        "include_private_key": True,
    }

    response = await client.post(
        f"{settings.API_V1_STR}/certificates/?ca_id={ca_id}",
        json=cert_data,
    )
    assert response.status_code == status.HTTP_201_CREATED
    created_cert = response.json()
    cert_id = created_cert["id"]

    # Now test exporting the certificate private key
    response = await client.get(
        f"{settings.API_V1_STR}/export/certificate/{cert_id}/private-key"
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.headers["Content-Type"] == "application/x-pem-file"
    assert (
        response.headers["Content-Disposition"]
        == f"attachment; filename=certificate_{cert_id}_private_key.pem"
    )
    assert "-----BEGIN PRIVATE KEY-----" in response.text
    assert "-----END PRIVATE KEY-----" in response.text


@pytest.mark.asyncio
async def test_export_certificate_chain(client: AsyncClient):
    """Test exporting a certificate with its complete certificate chain."""
    # First create a root CA
    root_ca_data = {
        "name": "Chain Root CA",
        "subject_dn": "CN=Chain Root CA,O=Test Organization,C=US",
    }

    response = await client.post(
        f"{settings.API_V1_STR}/cas/",
        json=root_ca_data,
    )
    assert response.status_code == status.HTTP_201_CREATED
    created_root_ca = response.json()
    root_ca_id = created_root_ca["id"]

    # Create an intermediate CA signed by the root CA
    intermediate_ca_data = {
        "common_name": "Chain Intermediate CA",
        "subject_dn": "CN=Chain Intermediate CA,O=Test Organization,C=US",
        "certificate_type": CertificateType.CA,
        "include_private_key": True,
    }

    response = await client.post(
        f"{settings.API_V1_STR}/certificates/?ca_id={root_ca_id}",
        json=intermediate_ca_data,
    )
    assert response.status_code == status.HTTP_201_CREATED
    created_intermediate = response.json()
    intermediate_id = created_intermediate["id"]

    # Create a server certificate signed by the intermediate CA
    cert_data = {
        "common_name": "chain-test.example.com",
        "subject_dn": "CN=chain-test.example.com,O=Test Organization,C=US",
        "certificate_type": "server",
        "include_private_key": True,
    }

    # Create the server certificate signed by the intermediate CA
    response = await client.post(
        f"{settings.API_V1_STR}/certificates/?ca_id={intermediate_id}",
        json=cert_data,
    )
    assert response.status_code == status.HTTP_201_CREATED
    created_cert = response.json()
    cert_id = created_cert["id"]

    # Now test exporting the certificate chain
    response = await client.get(
        f"{settings.API_V1_STR}/export/certificate/{cert_id}/chain"
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.headers["Content-Type"] == "application/x-pem-file"
    assert (
        response.headers["Content-Disposition"]
        == f"attachment; filename=certificate_{cert_id}_chain.pem"
    )

    # Chain should contain both the certificate and the CA certificates
    assert response.text.count("-----BEGIN CERTIFICATE-----") >= 2
    assert response.text.count("-----END CERTIFICATE-----") >= 2
