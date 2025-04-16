import pytest
from fastapi import status
from httpx import AsyncClient

from app.core.config import settings


@pytest.mark.asyncio
async def test_create_certificate(client: AsyncClient):
    # First create a CA
    ca_data = {
        "name": "Test CA for Certs",
        "subject_dn": "CN=Test CA for Certs,O=Test Organization,C=US",
    }

    response = await client.post(
        f"{settings.API_V1_STR}/cas/",
        json=ca_data,
    )
    assert response.status_code == status.HTTP_201_CREATED
    created_ca = response.json()
    ca_id = created_ca["id"]

    # Now create a certificate
    cert_data = {
        "common_name": "test.example.com",
        "subject_dn": "CN=test.example.com,O=Test Organization,C=US",
        "certificate_type": "server",
        "key_size": 2048,
        "valid_days": 365,
        "include_private_key": True,
    }

    response = await client.post(
        f"{settings.API_V1_STR}/certificates/?ca_id={ca_id}",
        json=cert_data,
    )

    assert response.status_code == status.HTTP_201_CREATED
    created_cert = response.json()

    assert created_cert["common_name"] == cert_data["common_name"]
    assert created_cert["subject_dn"] == cert_data["subject_dn"]
    assert created_cert["certificate_type"] == cert_data["certificate_type"]
    assert created_cert["key_size"] == cert_data["key_size"]
    assert created_cert["valid_days"] == cert_data["valid_days"]
    assert created_cert["status"] == "valid"
    assert "certificate" in created_cert
    assert "private_key" in created_cert
    assert "id" in created_cert
    assert created_cert["issuer_id"] == ca_id


@pytest.mark.asyncio
async def test_get_certificates(client: AsyncClient):
    # First create a CA
    ca_data = {
        "name": "Another CA for Certs",
        "subject_dn": "CN=Another CA for Certs,O=Test Organization,C=US",
    }

    response = await client.post(
        f"{settings.API_V1_STR}/cas/",
        json=ca_data,
    )
    assert response.status_code == status.HTTP_201_CREATED
    created_ca = response.json()
    ca_id = created_ca["id"]

    # Create a certificate
    cert_data = {
        "common_name": "another.example.com",
        "subject_dn": "CN=another.example.com,O=Test Organization,C=US",
        "certificate_type": "server",
    }

    response = await client.post(
        f"{settings.API_V1_STR}/certificates/?ca_id={ca_id}",
        json=cert_data,
    )
    assert response.status_code == status.HTTP_201_CREATED

    # Now test getting the list of certificates
    response = await client.get(f"{settings.API_V1_STR}/certificates/")

    assert response.status_code == status.HTTP_200_OK
    certs = response.json()

    assert len(certs) >= 1
    assert certs[0]["common_name"] is not None
    assert certs[0]["subject_dn"] is not None
    assert "certificate" in certs[0]
    assert "private_key" not in certs[0]  # Private key not included in list

    # Test filtering by CA ID
    response = await client.get(f"{settings.API_V1_STR}/certificates/?ca_id={ca_id}")

    assert response.status_code == status.HTTP_200_OK
    filtered_certs = response.json()

    assert len(filtered_certs) >= 1
    for cert in filtered_certs:
        assert cert["issuer_id"] == ca_id


@pytest.mark.asyncio
async def test_get_certificate(client: AsyncClient):
    # First create a CA
    ca_data = {
        "name": "CA for Cert Detail",
        "subject_dn": "CN=CA for Cert Detail,O=Test Organization,C=US",
    }

    response = await client.post(
        f"{settings.API_V1_STR}/cas/",
        json=ca_data,
    )
    assert response.status_code == status.HTTP_201_CREATED
    created_ca = response.json()
    ca_id = created_ca["id"]

    # Create a certificate
    cert_data = {
        "common_name": "detail.example.com",
        "subject_dn": "CN=detail.example.com,O=Test Organization,C=US",
        "certificate_type": "server",
    }

    response = await client.post(
        f"{settings.API_V1_STR}/certificates/?ca_id={ca_id}",
        json=cert_data,
    )
    assert response.status_code == status.HTTP_201_CREATED
    created_cert = response.json()
    cert_id = created_cert["id"]

    # Now test getting a specific certificate
    response = await client.get(f"{settings.API_V1_STR}/certificates/{cert_id}")

    assert response.status_code == status.HTTP_200_OK
    retrieved_cert = response.json()

    assert retrieved_cert["id"] == cert_id
    assert retrieved_cert["common_name"] == cert_data["common_name"]
    assert retrieved_cert["subject_dn"] == cert_data["subject_dn"]
    assert "certificate" in retrieved_cert
    assert "private_key" not in retrieved_cert  # Private key not included


@pytest.mark.asyncio
async def test_get_certificate_with_private_key(client: AsyncClient):
    # First create a CA
    ca_data = {
        "name": "CA for Cert with Key",
        "subject_dn": "CN=CA for Cert with Key,O=Test Organization,C=US",
    }

    response = await client.post(
        f"{settings.API_V1_STR}/cas/",
        json=ca_data,
    )
    assert response.status_code == status.HTTP_201_CREATED
    created_ca = response.json()
    ca_id = created_ca["id"]

    # Create a certificate
    cert_data = {
        "common_name": "withkey.example.com",
        "subject_dn": "CN=withkey.example.com,O=Test Organization,C=US",
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

    # Now test getting a specific certificate with private key
    response = await client.get(
        f"{settings.API_V1_STR}/certificates/{cert_id}/private-key"
    )

    assert response.status_code == status.HTTP_200_OK
    retrieved_cert = response.json()

    assert retrieved_cert["id"] == cert_id
    assert retrieved_cert["common_name"] == cert_data["common_name"]
    assert retrieved_cert["subject_dn"] == cert_data["subject_dn"]
    assert "certificate" in retrieved_cert
    assert "private_key" in retrieved_cert  # Private key is included


@pytest.mark.asyncio
async def test_revoke_certificate(client: AsyncClient):
    # First create a CA
    ca_data = {
        "name": "CA for Revoke Test",
        "subject_dn": "CN=CA for Revoke Test,O=Test Organization,C=US",
    }

    response = await client.post(
        f"{settings.API_V1_STR}/cas/",
        json=ca_data,
    )
    assert response.status_code == status.HTTP_201_CREATED
    created_ca = response.json()
    ca_id = created_ca["id"]

    # Create a certificate
    cert_data = {
        "common_name": "revoke.example.com",
        "subject_dn": "CN=revoke.example.com,O=Test Organization,C=US",
        "certificate_type": "server",
    }

    response = await client.post(
        f"{settings.API_V1_STR}/certificates/?ca_id={ca_id}",
        json=cert_data,
    )
    assert response.status_code == status.HTTP_201_CREATED
    created_cert = response.json()
    cert_id = created_cert["id"]

    # Now test revoking the certificate
    revoke_data = {"reason": "Key compromise"}

    response = await client.post(
        f"{settings.API_V1_STR}/certificates/{cert_id}/revoke",
        json=revoke_data,
    )

    assert response.status_code == status.HTTP_200_OK
    revoked_cert = response.json()

    assert revoked_cert["id"] == cert_id
    assert revoked_cert["status"] == "revoked"
    assert revoked_cert["revoked_at"] is not None
