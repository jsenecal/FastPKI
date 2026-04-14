from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import BlocklistedToken, RefreshToken


async def test_create_blocklisted_token(db: AsyncSession):
    from datetime import datetime
    from zoneinfo import ZoneInfo

    token = BlocklistedToken(
        jti="test-jti-123",
        exp=datetime.now(ZoneInfo("UTC")),
    )
    db.add(token)
    await db.commit()
    await db.refresh(token)

    assert token.id is not None
    assert token.jti == "test-jti-123"


async def test_create_refresh_token(db: AsyncSession):
    from datetime import datetime
    from zoneinfo import ZoneInfo

    token = RefreshToken(
        token="opaque-refresh-token-abc",
        user_id=1,
        expires_at=datetime.now(ZoneInfo("UTC")),
    )
    db.add(token)
    await db.commit()
    await db.refresh(token)

    assert token.id is not None
    assert token.token == "opaque-refresh-token-abc"
    assert token.revoked is False
    assert token.created_at is not None


async def test_user_tokens_invalidated_at_default_none(db: AsyncSession):
    from app.db.models import UserRole
    from app.services.user import UserService

    user_service = UserService(db)
    user = await user_service.create_user(
        username="tokentest",
        email="tokentest@example.com",
        password="password123",
        role=UserRole.USER,
    )

    assert user.tokens_invalidated_at is None
