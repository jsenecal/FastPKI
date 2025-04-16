import pytest

from app.db.models import UserRole


@pytest.mark.asyncio
async def test_create_user(client):
    # Test creating a new user
    user_data = {
        "username": "newuser",
        "email": "new@example.com",
        "password": "password123",
    }

    response = await client.post("/api/v1/users/", json=user_data)

    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "newuser"
    assert data["email"] == "new@example.com"
    assert data["role"] == UserRole.USER.value
    assert data["is_active"] is True
    assert "hashed_password" not in data  # Password should not be returned


@pytest.mark.asyncio
async def test_create_user_duplicate_username(client):
    # Create a user
    user_data = {
        "username": "duplicate",
        "email": "dup1@example.com",
        "password": "password123",
    }

    await client.post("/api/v1/users/", json=user_data)

    # Try to create another user with the same username
    duplicate_data = {
        "username": "duplicate",
        "email": "dup2@example.com",
        "password": "password456",
    }

    response = await client.post("/api/v1/users/", json=duplicate_data)

    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert data["detail"] == "Username already registered"


@pytest.mark.asyncio
async def test_create_user_duplicate_email(client):
    # Create a user
    user_data = {
        "username": "emailuser1",
        "email": "same@example.com",
        "password": "password123",
    }

    await client.post("/api/v1/users/", json=user_data)

    # Try to create another user with the same email
    duplicate_data = {
        "username": "emailuser2",
        "email": "same@example.com",
        "password": "password456",
    }

    response = await client.post("/api/v1/users/", json=duplicate_data)

    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert data["detail"] == "Email already registered"


@pytest.mark.asyncio
async def test_get_users(client, db):
    # First create a superuser (will be the first user so has permission)
    superuser_data = {
        "username": "superadmin",
        "email": "super@example.com",
        "password": "superpass",
        "role": UserRole.SUPERUSER.value,
    }

    await client.post("/api/v1/users/", json=superuser_data)

    # Login as superuser
    login_response = await client.post(
        "/api/v1/auth/token", data={"username": "superadmin", "password": "superpass"}
    )
    token = login_response.json()["access_token"]

    # Create multiple users using the superuser token
    users_data = [
        {"username": "user1", "email": "user1@example.com", "password": "password1"},
        {"username": "user2", "email": "user2@example.com", "password": "password2"},
        {"username": "user3", "email": "user3@example.com", "password": "password3"},
    ]

    headers = {"Authorization": f"Bearer {token}"}
    for user_data in users_data:
        await client.post("/api/v1/users/", json=user_data, headers=headers)

    # Get list of users
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.get("/api/v1/users/", headers=headers)

    assert response.status_code == 200
    data = response.json()

    # Should have at least 4 users (3 regular + 1 superuser)
    assert len(data) >= 4

    # Check if our created users are in the list
    usernames = [user["username"] for user in data]
    assert "user1" in usernames
    assert "user2" in usernames
    assert "user3" in usernames


@pytest.mark.asyncio
async def test_get_user_by_id(client, db):
    # First create a superuser (will be the first user so has permission)
    superuser_data = {
        "username": "superget",
        "email": "superget@example.com",
        "password": "superpass",
        "role": UserRole.SUPERUSER.value,
    }

    await client.post("/api/v1/users/", json=superuser_data)

    # Login as superuser
    login_response = await client.post(
        "/api/v1/auth/token", data={"username": "superget", "password": "superpass"}
    )
    token = login_response.json()["access_token"]

    # Create a test user with superuser token
    user_data = {
        "username": "getbyid",
        "email": "getbyid@example.com",
        "password": "password123",
    }

    headers = {"Authorization": f"Bearer {token}"}
    create_response = await client.post(
        "/api/v1/users/", json=user_data, headers=headers
    )
    user_id = create_response.json()["id"]

    # Get user by ID
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.get(f"/api/v1/users/{user_id}", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == user_id
    assert data["username"] == "getbyid"
    assert data["email"] == "getbyid@example.com"


@pytest.mark.asyncio
async def test_update_user(client, db):
    # First create a superuser (will be the first user so has permission)
    superuser_data = {
        "username": "superupdate",
        "email": "superupdate@example.com",
        "password": "superpass",
        "role": UserRole.SUPERUSER.value,
    }

    await client.post("/api/v1/users/", json=superuser_data)

    # Login as superuser
    login_response = await client.post(
        "/api/v1/auth/token", data={"username": "superupdate", "password": "superpass"}
    )
    token = login_response.json()["access_token"]

    # Create a test user with superuser token
    user_data = {
        "username": "updateme",
        "email": "update@example.com",
        "password": "password123",
    }

    headers = {"Authorization": f"Bearer {token}"}
    create_response = await client.post(
        "/api/v1/users/", json=user_data, headers=headers
    )
    user_id = create_response.json()["id"]

    # Update user
    update_data = {
        "email": "updated@example.com",
        "role": UserRole.ADMIN.value,
        "is_active": False,
    }

    headers = {"Authorization": f"Bearer {token}"}
    response = await client.patch(
        f"/api/v1/users/{user_id}", json=update_data, headers=headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == user_id
    assert data["username"] == "updateme"  # Username should not change
    assert data["email"] == "updated@example.com"
    assert data["role"] == UserRole.ADMIN.value
    assert data["is_active"] is False


@pytest.mark.asyncio
async def test_delete_user(client, db):
    # First create a superuser (will be the first user so has permission)
    superuser_data = {
        "username": "superdelete",
        "email": "superdelete@example.com",
        "password": "superpass",
        "role": UserRole.SUPERUSER.value,
    }

    await client.post("/api/v1/users/", json=superuser_data)

    # Login as superuser
    login_response = await client.post(
        "/api/v1/auth/token", data={"username": "superdelete", "password": "superpass"}
    )
    token = login_response.json()["access_token"]

    # Create a test user with superuser token
    user_data = {
        "username": "deleteme",
        "email": "delete@example.com",
        "password": "password123",
    }

    headers = {"Authorization": f"Bearer {token}"}
    create_response = await client.post(
        "/api/v1/users/", json=user_data, headers=headers
    )
    user_id = create_response.json()["id"]

    # Delete user
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.delete(f"/api/v1/users/{user_id}", headers=headers)

    assert response.status_code == 204

    # Verify user is deleted
    get_response = await client.get(f"/api/v1/users/{user_id}", headers=headers)
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_regular_user_cannot_access_other_users(client, db):
    # First create a superuser (will be the first user so has permission)
    superuser_data = {
        "username": "superaccess",
        "email": "superaccess@example.com",
        "password": "superpass",
        "role": UserRole.SUPERUSER.value,
    }

    await client.post("/api/v1/users/", json=superuser_data)

    # Login as superuser
    login_response = await client.post(
        "/api/v1/auth/token", data={"username": "superaccess", "password": "superpass"}
    )
    super_token = login_response.json()["access_token"]

    # Create two regular users with superuser token
    user1_data = {
        "username": "user1access",
        "email": "user1@example.com",
        "password": "password1",
    }

    user2_data = {
        "username": "user2access",
        "email": "user2@example.com",
        "password": "password2",
    }

    # We'll use _ for unused response variable
    headers = {"Authorization": f"Bearer {super_token}"}
    _ = await client.post("/api/v1/users/", json=user1_data, headers=headers)
    user2_response = await client.post(
        "/api/v1/users/", json=user2_data, headers=headers
    )

    user2_id = user2_response.json()["id"]

    # Login as user1
    login_response = await client.post(
        "/api/v1/auth/token", data={"username": "user1access", "password": "password1"}
    )
    token = login_response.json()["access_token"]

    # Try to get user2's details
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.get(f"/api/v1/users/{user2_id}", headers=headers)

    # Should be forbidden
    assert response.status_code == 403
