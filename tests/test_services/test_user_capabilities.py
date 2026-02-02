import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import UserRole
from app.services.user import UserService


@pytest.mark.asyncio
async def test_create_user_default_capabilities(db: AsyncSession):
    user_service = UserService(db)
    user = await user_service.create_user(
        username="defaultcaps",
        email="defaultcaps@example.com",
        password="password123",
        role=UserRole.USER,
    )
    assert user.can_create_ca is False
    assert user.can_create_cert is False
    assert user.can_revoke_cert is False
    assert user.can_export_private_key is False
    assert user.can_delete_ca is False


@pytest.mark.asyncio
async def test_create_user_with_capabilities(db: AsyncSession):
    user_service = UserService(db)
    user = await user_service.create_user(
        username="capuser",
        email="capuser@example.com",
        password="password123",
        role=UserRole.USER,
        can_create_ca=True,
        can_create_cert=True,
        can_export_private_key=True,
    )
    assert user.can_create_ca is True
    assert user.can_create_cert is True
    assert user.can_revoke_cert is False
    assert user.can_export_private_key is True
    assert user.can_delete_ca is False


@pytest.mark.asyncio
async def test_update_user_capabilities(db: AsyncSession):
    user_service = UserService(db)
    user = await user_service.create_user(
        username="updatecaps",
        email="updatecaps@example.com",
        password="password123",
        role=UserRole.USER,
    )
    assert user.can_revoke_cert is False
    assert user.can_delete_ca is False

    updated = await user_service.update_user(
        user_id=user.id,
        can_revoke_cert=True,
        can_delete_ca=True,
    )
    assert updated is not None
    assert updated.can_revoke_cert is True
    assert updated.can_delete_ca is True
    # Other capabilities remain unchanged
    assert updated.can_create_ca is False
    assert updated.can_create_cert is False
    assert updated.can_export_private_key is False
