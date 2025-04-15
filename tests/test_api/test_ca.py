import pytest
from fastapi import status
from httpx import AsyncClient

from app.core.config import settings


@pytest.mark.asyncio
async def test_create_ca(client: AsyncClient):
    # Test creating a CA
    ca_data = {
        "name": "Test CA",
        "description": "Test Certificate Authority",
        "subject_dn": "CN=Test CA,O=Test Organization,C=US",
        "key_size": 2048,
        "valid_days": 3650
    }
    
    response = await client.post(
        f"{settings.API_V1_STR}/cas/",
        json=ca_data,
    )
    
    assert response.status_code == status.HTTP_201_CREATED
    created_ca = response.json()
    
    assert created_ca["name"] == ca_data["name"]
    assert created_ca["description"] == ca_data["description"]
    assert created_ca["subject_dn"] == ca_data["subject_dn"]
    assert created_ca["key_size"] == ca_data["key_size"]
    assert created_ca["valid_days"] == ca_data["valid_days"]
    assert "certificate" in created_ca
    assert "private_key" in created_ca
    assert "id" in created_ca


@pytest.mark.asyncio
async def test_get_cas(client: AsyncClient):
    # First create a CA
    ca_data = {
        "name": "Another CA",
        "subject_dn": "CN=Another CA,O=Test Organization,C=US",
    }
    
    response = await client.post(
        f"{settings.API_V1_STR}/cas/",
        json=ca_data,
    )
    assert response.status_code == status.HTTP_201_CREATED
    
    # Now test getting the list of CAs
    response = await client.get(f"{settings.API_V1_STR}/cas/")
    
    assert response.status_code == status.HTTP_200_OK
    cas = response.json()
    
    assert len(cas) >= 1
    assert cas[0]["name"] is not None
    assert cas[0]["subject_dn"] is not None
    assert "certificate" in cas[0]
    assert "private_key" not in cas[0]  # Private key not included in list


@pytest.mark.asyncio
async def test_get_ca(client: AsyncClient):
    # First create a CA
    ca_data = {
        "name": "CA to Get",
        "subject_dn": "CN=CA to Get,O=Test Organization,C=US",
    }
    
    response = await client.post(
        f"{settings.API_V1_STR}/cas/",
        json=ca_data,
    )
    assert response.status_code == status.HTTP_201_CREATED
    created_ca = response.json()
    ca_id = created_ca["id"]
    
    # Now test getting a specific CA
    response = await client.get(f"{settings.API_V1_STR}/cas/{ca_id}")
    
    assert response.status_code == status.HTTP_200_OK
    retrieved_ca = response.json()
    
    assert retrieved_ca["id"] == ca_id
    assert retrieved_ca["name"] == ca_data["name"]
    assert retrieved_ca["subject_dn"] == ca_data["subject_dn"]
    assert "certificate" in retrieved_ca
    assert "private_key" not in retrieved_ca  # Private key not included


@pytest.mark.asyncio
async def test_get_ca_private_key(client: AsyncClient):
    # First create a CA
    ca_data = {
        "name": "CA with Private Key",
        "subject_dn": "CN=CA with Private Key,O=Test Organization,C=US",
    }
    
    response = await client.post(
        f"{settings.API_V1_STR}/cas/",
        json=ca_data,
    )
    assert response.status_code == status.HTTP_201_CREATED
    created_ca = response.json()
    ca_id = created_ca["id"]
    
    # Now test getting a specific CA with private key
    response = await client.get(f"{settings.API_V1_STR}/cas/{ca_id}/private-key")
    
    assert response.status_code == status.HTTP_200_OK
    retrieved_ca = response.json()
    
    assert retrieved_ca["id"] == ca_id
    assert retrieved_ca["name"] == ca_data["name"]
    assert retrieved_ca["subject_dn"] == ca_data["subject_dn"]
    assert "certificate" in retrieved_ca
    assert "private_key" in retrieved_ca  # Private key is included


@pytest.mark.asyncio
async def test_delete_ca(client: AsyncClient):
    # First create a CA
    ca_data = {
        "name": "CA to Delete",
        "subject_dn": "CN=CA to Delete,O=Test Organization,C=US",
    }
    
    response = await client.post(
        f"{settings.API_V1_STR}/cas/",
        json=ca_data,
    )
    assert response.status_code == status.HTTP_201_CREATED
    created_ca = response.json()
    ca_id = created_ca["id"]
    
    # Now test deleting the CA
    response = await client.delete(f"{settings.API_V1_STR}/cas/{ca_id}")
    
    assert response.status_code == status.HTTP_204_NO_CONTENT
    
    # Verify it's deleted
    response = await client.get(f"{settings.API_V1_STR}/cas/{ca_id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND