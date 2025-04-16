from datetime import UTC, datetime, timedelta

import pytest
from jose import jwt

from app.core.config import settings
from app.db.models import UserRole
from app.services.user import UserService, get_password_hash, verify_password


@pytest.mark.asyncio
async def test_create_user(db):
    # Test creating a new user
    user_service = UserService(db)
    new_user = await user_service.create_user(
        username="testuser",
        email="test@example.com",
        password="securepassword",
        role=UserRole.USER,
    )

    assert new_user.id is not None
    assert new_user.username == "testuser"
    assert new_user.email == "test@example.com"
    assert new_user.role == UserRole.USER
    assert new_user.is_active is True
    # Password should be hashed
    assert new_user.hashed_password != "securepassword"
    # Verify the password hash works
    assert verify_password("securepassword", new_user.hashed_password)


@pytest.mark.asyncio
async def test_get_user_by_id(db):
    # Create a user first
    user_service = UserService(db)
    created_user = await user_service.create_user(
        username="getbyid",
        email="getbyid@example.com",
        password="password123",
    )

    # Get the user by ID
    user = await user_service.get_user_by_id(created_user.id)

    assert user is not None
    assert user.id == created_user.id
    assert user.username == "getbyid"
    assert user.email == "getbyid@example.com"


@pytest.mark.asyncio
async def test_get_user_by_username(db):
    # Create a user first
    user_service = UserService(db)
    await user_service.create_user(
        username="getbyusername",
        email="getbyusername@example.com",
        password="password123",
    )

    # Get the user by username
    user = await user_service.get_user_by_username("getbyusername")

    assert user is not None
    assert user.username == "getbyusername"
    assert user.email == "getbyusername@example.com"


@pytest.mark.asyncio
async def test_get_user_by_email(db):
    # Create a user first
    user_service = UserService(db)
    await user_service.create_user(
        username="getbyemail",
        email="getbyemail@example.com",
        password="password123",
    )

    # Get the user by email
    user = await user_service.get_user_by_email("getbyemail@example.com")

    assert user is not None
    assert user.username == "getbyemail"
    assert user.email == "getbyemail@example.com"


@pytest.mark.asyncio
async def test_password_hashing():
    # Test password hashing functions
    password = "testpassword"
    hashed = get_password_hash(password)

    # Hashed password should be different from original
    assert hashed != password

    # Verify should return True for correct password
    assert verify_password(password, hashed) is True

    # Verify should return False for incorrect password
    assert verify_password("wrongpassword", hashed) is False


@pytest.mark.asyncio
async def test_create_access_token():
    # Test JWT token generation
    user_service = UserService(None)  # No DB needed for token generation

    username = "tokenuser"
    user_id = 123
    role = UserRole.ADMIN

    # Create token with 30-minute expiry
    token = user_service.create_access_token(
        data={"sub": username, "id": user_id, "role": role},
        expires_delta=timedelta(minutes=30),
    )

    # Verify the token contains the right data
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

    assert payload["sub"] == username
    assert payload["id"] == user_id
    assert payload["role"] == role

    # Verify expiration time is set correctly (approximately)
    expiry_time = datetime.fromtimestamp(payload["exp"], UTC)
    time_diff = expiry_time - datetime.now(UTC)

    # Should be close to 30 minutes (allow 5 seconds tolerance)
    assert (
        timedelta(minutes=29, seconds=55) < time_diff < timedelta(minutes=30, seconds=5)
    )


@pytest.mark.asyncio
async def test_authenticate_user(db):
    # Create a test user
    user_service = UserService(db)
    await user_service.create_user(
        username="authuser",
        email="authuser@example.com",
        password="correctpassword",
    )

    # Test successful authentication
    user = await user_service.authenticate_user("authuser", "correctpassword")
    assert user is not None
    assert user.username == "authuser"

    # Test failed authentication with wrong password
    user = await user_service.authenticate_user("authuser", "wrongpassword")
    assert user is None

    # Test failed authentication with non-existent username
    user = await user_service.authenticate_user("nonexistentuser", "anypassword")
    assert user is None


@pytest.mark.asyncio
async def test_inactive_user_authentication(db):
    # Create a test user that is inactive
    user_service = UserService(db)
    created_user = await user_service.create_user(
        username="inactiveuser",
        email="inactive@example.com",
        password="password123",
    )

    # Set user to inactive
    created_user.is_active = False
    db.add(created_user)
    await db.commit()
    await db.refresh(created_user)

    # Authentication should fail for inactive users
    user = await user_service.authenticate_user("inactiveuser", "password123")
    assert user is None


@pytest.mark.asyncio
async def test_update_user(db):
    # Create a test user
    user_service = UserService(db)
    created_user = await user_service.create_user(
        username="updateuser",
        email="update@example.com",
        password="password123",
    )

    # Update the user
    updated_user = await user_service.update_user(
        created_user.id,
        email="updated@example.com",
        role=UserRole.ADMIN,
        is_active=False,
    )

    assert updated_user.id == created_user.id
    assert updated_user.username == "updateuser"  # Username remains unchanged
    assert updated_user.email == "updated@example.com"
    assert updated_user.role == UserRole.ADMIN
    assert updated_user.is_active is False


@pytest.mark.asyncio
async def test_delete_user(db):
    # Create a test user
    user_service = UserService(db)
    created_user = await user_service.create_user(
        username="deleteuser",
        email="delete@example.com",
        password="password123",
    )

    # Delete the user
    result = await user_service.delete_user(created_user.id)
    assert result is True

    # Verify user is deleted
    user = await user_service.get_user_by_id(created_user.id)
    assert user is None
