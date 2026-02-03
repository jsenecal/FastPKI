import pytest
from fastapi import status
from httpx import AsyncClient

from app.core.config import settings


@pytest.mark.asyncio
async def test_create_intermediate_ca_via_api(superuser_client: AsyncClient):
    """Create an intermediate CA through the API."""
    # Create root CA first
    root_data = {
        "name": "API Root CA",
        "subject_dn": "CN=API Root CA,O=Test,C=US",
        "key_size": 2048,
        "valid_days": 3650,
    }
    response = await superuser_client.post(
        f"{settings.API_V1_STR}/cas/", json=root_data
    )
    assert response.status_code == status.HTTP_201_CREATED
    root_id = response.json()["id"]

    # Create intermediate CA
    intermediate_data = {
        "name": "API Intermediate CA",
        "subject_dn": "CN=API Intermediate CA,O=Test,C=US",
        "key_size": 2048,
        "valid_days": 1825,
        "parent_ca_id": root_id,
    }
    response = await superuser_client.post(
        f"{settings.API_V1_STR}/cas/", json=intermediate_data
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["parent_ca_id"] == root_id
    assert data["is_root"] is False


@pytest.mark.asyncio
async def test_root_ca_shows_is_root(superuser_client: AsyncClient):
    """Root CA response includes is_root=True."""
    root_data = {
        "name": "Root is_root Test",
        "subject_dn": "CN=Root is_root Test,O=Test,C=US",
        "key_size": 2048,
        "valid_days": 3650,
    }
    response = await superuser_client.post(
        f"{settings.API_V1_STR}/cas/", json=root_data
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["is_root"] is True
    assert data["parent_ca_id"] is None


@pytest.mark.asyncio
async def test_get_ca_chain_endpoint(superuser_client: AsyncClient):
    """GET /{ca_id}/chain returns the full chain."""
    root_resp = await superuser_client.post(
        f"{settings.API_V1_STR}/cas/",
        json={
            "name": "Chain Root",
            "subject_dn": "CN=Chain Root,O=Test,C=US",
            "key_size": 2048,
            "valid_days": 3650,
        },
    )
    root_id = root_resp.json()["id"]

    inter_resp = await superuser_client.post(
        f"{settings.API_V1_STR}/cas/",
        json={
            "name": "Chain Intermediate",
            "subject_dn": "CN=Chain Intermediate,O=Test,C=US",
            "key_size": 2048,
            "valid_days": 1825,
            "parent_ca_id": root_id,
        },
    )
    inter_id = inter_resp.json()["id"]

    response = await superuser_client.get(f"{settings.API_V1_STR}/cas/{inter_id}/chain")
    assert response.status_code == status.HTTP_200_OK
    chain = response.json()
    assert len(chain) == 2
    assert chain[0]["id"] == inter_id
    assert chain[1]["id"] == root_id


@pytest.mark.asyncio
async def test_get_ca_children_endpoint(superuser_client: AsyncClient):
    """GET /{ca_id}/children returns direct children."""
    root_resp = await superuser_client.post(
        f"{settings.API_V1_STR}/cas/",
        json={
            "name": "Children Root",
            "subject_dn": "CN=Children Root,O=Test,C=US",
            "key_size": 2048,
            "valid_days": 3650,
        },
    )
    root_id = root_resp.json()["id"]

    child_resp = await superuser_client.post(
        f"{settings.API_V1_STR}/cas/",
        json={
            "name": "Child CA",
            "subject_dn": "CN=Child CA,O=Test,C=US",
            "key_size": 2048,
            "valid_days": 1825,
            "parent_ca_id": root_id,
        },
    )
    child_id = child_resp.json()["id"]

    response = await superuser_client.get(
        f"{settings.API_V1_STR}/cas/{root_id}/children"
    )
    assert response.status_code == status.HTTP_200_OK
    children = response.json()
    assert len(children) == 1
    assert children[0]["id"] == child_id


@pytest.mark.asyncio
async def test_delete_ca_with_children_returns_409(superuser_client: AsyncClient):
    """DELETE on a CA with children returns 409 Conflict."""
    root_resp = await superuser_client.post(
        f"{settings.API_V1_STR}/cas/",
        json={
            "name": "Delete Root",
            "subject_dn": "CN=Delete Root,O=Test,C=US",
            "key_size": 2048,
            "valid_days": 3650,
        },
    )
    root_id = root_resp.json()["id"]

    await superuser_client.post(
        f"{settings.API_V1_STR}/cas/",
        json={
            "name": "Delete Child",
            "subject_dn": "CN=Delete Child,O=Test,C=US",
            "key_size": 2048,
            "valid_days": 1825,
            "parent_ca_id": root_id,
        },
    )

    response = await superuser_client.delete(f"{settings.API_V1_STR}/cas/{root_id}")
    assert response.status_code == status.HTTP_409_CONFLICT


@pytest.mark.asyncio
async def test_path_length_violation_returns_400(superuser_client: AsyncClient):
    """Creating a sub-CA that violates path_length returns 400."""
    root_resp = await superuser_client.post(
        f"{settings.API_V1_STR}/cas/",
        json={
            "name": "PL Root",
            "subject_dn": "CN=PL Root,O=Test,C=US",
            "key_size": 2048,
            "valid_days": 3650,
            "path_length": 0,
        },
    )
    assert root_resp.status_code == status.HTTP_201_CREATED
    root_id = root_resp.json()["id"]

    response = await superuser_client.post(
        f"{settings.API_V1_STR}/cas/",
        json={
            "name": "Should Fail Child",
            "subject_dn": "CN=Should Fail Child,O=Test,C=US",
            "key_size": 2048,
            "valid_days": 365,
            "parent_ca_id": root_id,
        },
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_leaf_cert_blocked_returns_400(superuser_client: AsyncClient):
    """Issuing a leaf cert from a CA with allow_leaf_certs=False returns 400."""
    # Create root CA
    root_resp = await superuser_client.post(
        f"{settings.API_V1_STR}/cas/",
        json={
            "name": "Leaf Block Root",
            "subject_dn": "CN=Leaf Block Root,O=Test,C=US",
            "key_size": 2048,
            "valid_days": 3650,
        },
    )
    assert root_resp.status_code == status.HTTP_201_CREATED
    root_id = root_resp.json()["id"]

    # Create intermediate CA (this auto-sets parent's allow_leaf_certs=False)
    inter_resp = await superuser_client.post(
        f"{settings.API_V1_STR}/cas/",
        json={
            "name": "Leaf Block Intermediate",
            "subject_dn": "CN=Leaf Block Intermediate,O=Test,C=US",
            "key_size": 2048,
            "valid_days": 1825,
            "parent_ca_id": root_id,
        },
    )
    assert inter_resp.status_code == status.HTTP_201_CREATED

    # Try to issue a leaf cert from the root CA (should fail)
    cert_resp = await superuser_client.post(
        f"{settings.API_V1_STR}/certificates/?ca_id={root_id}",
        json={
            "common_name": "blocked.example.com",
            "subject_dn": "CN=blocked.example.com,O=Test,C=US",
            "certificate_type": "server",
            "key_size": 2048,
            "valid_days": 365,
        },
    )
    assert cert_resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "does not allow leaf certificate" in cert_resp.json()["detail"]


@pytest.mark.asyncio
async def test_allow_leaf_certs_in_ca_response(superuser_client: AsyncClient):
    """CA response includes allow_leaf_certs field."""
    root_resp = await superuser_client.post(
        f"{settings.API_V1_STR}/cas/",
        json={
            "name": "Response Check Root",
            "subject_dn": "CN=Response Check Root,O=Test,C=US",
            "key_size": 2048,
            "valid_days": 3650,
        },
    )
    assert root_resp.status_code == status.HTTP_201_CREATED
    data = root_resp.json()
    assert data["allow_leaf_certs"] is True

    root_id = data["id"]

    # Create intermediate to auto-flip parent
    await superuser_client.post(
        f"{settings.API_V1_STR}/cas/",
        json={
            "name": "Response Check Intermediate",
            "subject_dn": "CN=Response Check Intermediate,O=Test,C=US",
            "key_size": 2048,
            "valid_days": 1825,
            "parent_ca_id": root_id,
        },
    )

    # Check that root's allow_leaf_certs is now False
    get_resp = await superuser_client.get(f"{settings.API_V1_STR}/cas/{root_id}")
    assert get_resp.status_code == status.HTTP_200_OK
    assert get_resp.json()["allow_leaf_certs"] is False
