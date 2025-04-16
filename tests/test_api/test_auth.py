import logging

import pytest
from jose import jwt

from app.core.config import logger, settings
from app.db.models import UserRole

# Set logging to debug for tests
logger.setLevel(logging.DEBUG)


@pytest.mark.asyncio
async def test_login_success(client, db):
    # Create a test user first (directly, not via API)
    user_data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "password123",
    }

    await client.post("/api/v1/users/", json=user_data)

    # Try to login
    # Using form data directly in the request below

    # For OAuth2PasswordRequestForm, use proper formData format
    response = await client.post(
        "/api/v1/auth/token", data={"username": "testuser", "password": "password123"}
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

    # Verify token contains expected data
    token = data["access_token"]
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

    assert payload["sub"] == "testuser"
    assert "id" in payload
    assert payload["role"] == UserRole.USER.value


@pytest.mark.asyncio
async def test_login_invalid_credentials(client, db):
    # Create a test user first
    user_data = {
        "username": "invalidtest",
        "email": "invalid@example.com",
        "password": "password123",
    }

    await client.post("/api/v1/users/", json=user_data)

    # Try to login with wrong password
    # Using form data directly in the request below

    response = await client.post(
        "/api/v1/auth/token",
        data={"username": "invalidtest", "password": "wrongpassword"},
    )

    assert response.status_code == 401
    data = response.json()
    assert "detail" in data
    assert data["detail"] == "Incorrect username or password"


@pytest.mark.asyncio
async def test_login_nonexistent_user(client):
    # Try to login with non-existent user (with timestamp to ensure it doesn't exist)
    import time

    unique_id = int(time.time() * 1000)

    login_data = {"username": f"nonexistentuser_{unique_id}", "password": "anypassword"}

    response = await client.post(
        "/api/v1/auth/token",
        data={"username": login_data["username"], "password": "anypassword"},
    )

    assert response.status_code == 401
    data = response.json()
    assert "detail" in data
    assert data["detail"] == "Incorrect username or password"


@pytest.mark.asyncio
async def test_access_protected_endpoint(client, db):
    # Create a test user
    user_data = {
        "username": "protecteduser",
        "email": "protected@example.com",
        "password": "password123",
    }

    await client.post("/api/v1/users/", json=user_data)

    # Login to get a token
    # Using form data directly in the request below

    login_response = await client.post(
        "/api/v1/auth/token",
        data={"username": "protecteduser", "password": "password123"},
    )
    token = login_response.json()["access_token"]

    # Access a protected endpoint with token
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.get("/api/v1/users/me", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "protecteduser"
    assert data["email"] == "protected@example.com"


@pytest.mark.asyncio
async def test_access_protected_endpoint_without_token(client):
    # Try to access protected endpoint without a token
    response = await client.get("/api/v1/users/me")

    assert response.status_code == 401
    data = response.json()
    assert "detail" in data
    assert data["detail"] == "Not authenticated"


@pytest.mark.asyncio
async def test_access_protected_endpoint_invalid_token(client):
    # Try to access protected endpoint with invalid token
    headers = {"Authorization": "Bearer invalidtoken"}
    response = await client.get("/api/v1/users/me", headers=headers)

    assert response.status_code == 401
    data = response.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_user_can_create_regular_user(client, db):
    # Test to verify a user can create another regular user
    # First create a regular user
    import time

    unique_id = int(time.time() * 1000)

    user_data = {
        "username": f"user_{unique_id}",
        "email": f"user_{unique_id}@example.com",
        "password": "password123",
    }

    # Create user
    create_response = await client.post("/api/v1/users/", json=user_data)
    assert create_response.status_code == 201

    # Login as user
    login_response = await client.post(
        "/api/v1/auth/token",
        data={"username": user_data["username"], "password": "password123"},
    )

    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    # Create another regular user
    unique_id_2 = int(time.time() * 1000) + 1
    new_user_data = {
        "username": f"new_user_{unique_id_2}",
        "email": f"new_{unique_id_2}@example.com",
        "password": "userpass",
        "role": UserRole.USER.value,  # Regular user role
    }

    headers = {"Authorization": f"Bearer {token}"}
    response = await client.post("/api/v1/users/", json=new_user_data, headers=headers)

    assert response.status_code == 201
    data = response.json()
    assert data["username"] == new_user_data["username"]
    assert data["role"] == UserRole.USER.value


@pytest.mark.asyncio
async def test_regular_user_cannot_create_admin(client, db):
    # Create a unique regular user - use timestamp to ensure uniqueness
    import time

    unique_id = int(time.time() * 1000)

    user_data = {
        "username": f"regularuser_{unique_id}",
        "email": f"regular_{unique_id}@example.com",
        "password": "userpass",
    }

    await client.post("/api/v1/users/", json=user_data)

    # Login as regular user
    # Using form data directly in the request below

    login_response = await client.post(
        "/api/v1/auth/token",
        data={"username": user_data["username"], "password": "userpass"},
    )
    token = login_response.json()["access_token"]

    # Try to create an admin user
    new_user_data = {
        "username": "attempted_admin",
        "email": "attempted@example.com",
        "password": "adminpass",
        "role": UserRole.ADMIN.value,
    }

    headers = {"Authorization": f"Bearer {token}"}
    response = await client.post("/api/v1/users/", json=new_user_data, headers=headers)

    # Should be forbidden
    assert response.status_code == 403
