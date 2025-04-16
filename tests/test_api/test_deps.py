import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_active_admin_user,
    get_current_active_superuser,
    get_current_active_user,
    get_current_user,
    get_db,
)
from app.db.models import User, UserRole
from app.services.user import UserService


# Remove unused fixtures


@pytest.mark.asyncio
async def test_get_db():
    """Test the get_db dependency."""
    db_generator = get_db()
    db = await anext(db_generator)
    assert db is not None
    # Clean up by closing the session
    try:
        await db_generator.aclose()
    except Exception:
        pass  # This is expected in a test environment


@pytest.mark.asyncio
async def test_get_current_active_user_success(db: AsyncSession):
    """Test get_current_active_user with an active user."""
    # Create a test user directly
    user_service = UserService(db)
    user = await user_service.create_user(
        username="active_test_user",
        email="active_test_user@example.com",
        password="password123",
        role=UserRole.USER,
    )
    
    active_user = await get_current_active_user(current_user=user)
    assert active_user is not None
    assert active_user.id == user.id
    assert active_user.is_active is True


@pytest.mark.asyncio
async def test_get_current_active_user_inactive(db: AsyncSession):
    """Test get_current_active_user with an inactive user."""
    # Create a test user directly
    user_service = UserService(db)
    user = await user_service.create_user(
        username="inactive_test_user",
        email="inactive_test_user@example.com",
        password="password123",
        role=UserRole.USER,
    )
    
    # Set inactive status directly
    user.is_active = False
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    with pytest.raises(HTTPException) as exc_info:
        await get_current_active_user(current_user=user)
    
    assert exc_info.value.status_code == 400
    assert "Inactive user" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_current_active_superuser_success(db: AsyncSession):
    """Test get_current_active_superuser with a superuser."""
    # Create a test superuser directly
    user_service = UserService(db)
    user = await user_service.create_user(
        username="super_test_user",
        email="super_test_user@example.com",
        password="password123",
        role=UserRole.SUPERUSER,
    )
    
    superuser = await get_current_active_superuser(current_user=user)
    assert superuser is not None
    assert superuser.id == user.id
    assert superuser.role == UserRole.SUPERUSER


@pytest.mark.asyncio
async def test_get_current_active_superuser_not_superuser(db: AsyncSession):
    """Test get_current_active_superuser with a non-superuser."""
    # Create a regular user
    user_service = UserService(db)
    user = await user_service.create_user(
        username="regular_test_user",
        email="regular_test_user@example.com",
        password="password123",
        role=UserRole.USER,
    )
    
    with pytest.raises(HTTPException) as exc_info:
        await get_current_active_superuser(current_user=user)
    
    assert exc_info.value.status_code == 403
    assert "sufficient privileges" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_current_active_admin_user_admin(db: AsyncSession):
    """Test get_current_active_admin_user with an admin."""
    # Create an admin user
    user_service = UserService(db)
    user = await user_service.create_user(
        username="admin_test_user",
        email="admin_test_user@example.com",
        password="password123",
        role=UserRole.ADMIN,
    )
    
    admin_user = await get_current_active_admin_user(current_user=user)
    assert admin_user is not None
    assert admin_user.id == user.id
    assert admin_user.role == UserRole.ADMIN


@pytest.mark.asyncio
async def test_get_current_active_admin_user_superuser(db: AsyncSession):
    """Test get_current_active_admin_user with a superuser."""
    # Create a superuser
    user_service = UserService(db)
    user = await user_service.create_user(
        username="super_admin_test_user",
        email="super_admin_test_user@example.com",
        password="password123",
        role=UserRole.SUPERUSER,
    )
    
    super_admin_user = await get_current_active_admin_user(current_user=user)
    assert super_admin_user is not None
    assert super_admin_user.id == user.id
    assert super_admin_user.role == UserRole.SUPERUSER


@pytest.mark.asyncio
async def test_get_current_active_admin_user_not_admin(db: AsyncSession):
    """Test get_current_active_admin_user with a regular user."""
    # Create a regular user
    user_service = UserService(db)
    user = await user_service.create_user(
        username="regular_admin_test_user",
        email="regular_admin_test_user@example.com",
        password="password123",
        role=UserRole.USER,
    )
    
    with pytest.raises(HTTPException) as exc_info:
        await get_current_active_admin_user(current_user=user)
    
    assert exc_info.value.status_code == 403
    assert "sufficient privileges" in exc_info.value.detail