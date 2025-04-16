import pytest
import pytest_asyncio
from fastapi import HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import (
    get_current_active_user,
    get_current_admin_or_superuser,
    get_current_superuser,
    get_current_user,
    login_for_access_token,
)
from app.core.config import settings
from app.db.models import User, UserRole
from app.schemas.user import Token
from app.services.user import UserService


@pytest_asyncio.fixture
async def auth_test_user(db: AsyncSession) -> User:
    """Create a test user for auth tests."""
    user_service = UserService(db)
    user = await user_service.create_user(
        username="authuser",
        email="authuser@example.com",
        password="password123",
        role=UserRole.USER,
    )
    return user


@pytest_asyncio.fixture
async def auth_test_admin(db: AsyncSession) -> User:
    """Create a test admin for auth tests."""
    user_service = UserService(db)
    user = await user_service.create_user(
        username="authadmin",
        email="authadmin@example.com",
        password="password123",
        role=UserRole.ADMIN,
    )
    return user


@pytest_asyncio.fixture
async def auth_test_superuser(db: AsyncSession) -> User:
    """Create a test superuser for auth tests."""
    user_service = UserService(db)
    user = await user_service.create_user(
        username="authsuper",
        email="authsuper@example.com",
        password="password123",
        role=UserRole.SUPERUSER,
    )
    return user


@pytest_asyncio.fixture
async def auth_test_inactive_user(db: AsyncSession) -> User:
    """Create an inactive test user for auth tests."""
    user_service = UserService(db)
    # Create a user then deactivate it
    user = await user_service.create_user(
        username="authinactive",
        email="authinactive@example.com",
        password="password123",
        role=UserRole.USER,
    )
    # Set inactive status directly
    user.is_active = False
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest.mark.asyncio
async def test_login_for_access_token_success(db: AsyncSession, auth_test_user: User):
    """Test successful login and token generation."""
    form_data = OAuth2PasswordRequestForm(
        username=auth_test_user.username, 
        password="password123",
        scope=""
    )
    
    token_response = await login_for_access_token(form_data=form_data, db=db)
    
    assert isinstance(token_response, dict)
    assert "access_token" in token_response
    assert "token_type" in token_response
    assert token_response["token_type"] == "bearer"
    
    # Verify token can be decoded
    token = token_response["access_token"]
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    
    assert payload["sub"] == auth_test_user.username
    assert payload["id"] == auth_test_user.id
    assert payload["role"] == auth_test_user.role


@pytest.mark.asyncio
async def test_login_for_access_token_invalid_credentials(db: AsyncSession, auth_test_user: User):
    """Test login with invalid credentials."""
    form_data = OAuth2PasswordRequestForm(
        username=auth_test_user.username, 
        password="wrongpassword",
        scope=""
    )
    
    with pytest.raises(HTTPException) as exc_info:
        await login_for_access_token(form_data=form_data, db=db)
    
    assert exc_info.value.status_code == 401
    assert "Incorrect username or password" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_current_user_success(db: AsyncSession, auth_test_user: User):
    """Test getting the current user from a valid token."""
    # Create a token
    user_service = UserService(db)
    token = user_service.create_access_token(
        data={"sub": auth_test_user.username, "id": auth_test_user.id, "role": auth_test_user.role}
    )
    
    # Get current user
    user = await get_current_user(token=token, db=db)
    
    assert user is not None
    assert user.id == auth_test_user.id
    assert user.username == auth_test_user.username


@pytest.mark.asyncio
async def test_get_current_active_user_success(db: AsyncSession, auth_test_user: User):
    """Test getting current active user."""
    # This is a simple passthrough function, so just verify it returns the user
    user = await get_current_active_user(current_user=auth_test_user)
    
    assert user is not None
    assert user.id == auth_test_user.id


@pytest.mark.asyncio
async def test_get_current_active_user_inactive(db: AsyncSession, auth_test_inactive_user: User):
    """Test getting current active user with an inactive user."""
    with pytest.raises(HTTPException) as exc_info:
        await get_current_active_user(current_user=auth_test_inactive_user)
    
    assert exc_info.value.status_code == 400
    assert "Inactive user" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_current_superuser_success(db: AsyncSession, auth_test_superuser: User):
    """Test getting current superuser with a superuser."""
    user = await get_current_superuser(current_user=auth_test_superuser)
    
    assert user is not None
    assert user.id == auth_test_superuser.id
    assert user.role == UserRole.SUPERUSER


@pytest.mark.asyncio
async def test_get_current_superuser_not_superuser(db: AsyncSession, auth_test_user: User):
    """Test getting current superuser with a non-superuser."""
    with pytest.raises(HTTPException) as exc_info:
        await get_current_superuser(current_user=auth_test_user)
    
    assert exc_info.value.status_code == 403
    assert "Not enough permissions" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_current_admin_or_superuser_admin(db: AsyncSession, auth_test_admin: User):
    """Test getting current admin or superuser with an admin."""
    user = await get_current_admin_or_superuser(current_user=auth_test_admin)
    
    assert user is not None
    assert user.id == auth_test_admin.id
    assert user.role == UserRole.ADMIN


@pytest.mark.asyncio
async def test_get_current_admin_or_superuser_superuser(db: AsyncSession, auth_test_superuser: User):
    """Test getting current admin or superuser with a superuser."""
    user = await get_current_admin_or_superuser(current_user=auth_test_superuser)
    
    assert user is not None
    assert user.id == auth_test_superuser.id
    assert user.role == UserRole.SUPERUSER


@pytest.mark.asyncio
async def test_get_current_admin_or_superuser_not_admin(db: AsyncSession, auth_test_user: User):
    """Test getting current admin or superuser with a regular user."""
    with pytest.raises(HTTPException) as exc_info:
        await get_current_admin_or_superuser(current_user=auth_test_user)
    
    assert exc_info.value.status_code == 403
    assert "Not enough permissions" in exc_info.value.detail