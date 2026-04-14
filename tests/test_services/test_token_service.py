from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import BlocklistedToken, RefreshToken
from app.services.token import TokenService


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


async def test_blocklist_token(db: AsyncSession):
    from datetime import datetime
    from zoneinfo import ZoneInfo

    token_service = TokenService(db)
    await token_service.blocklist_token(
        jti="blocklist-jti-1", exp=datetime.now(ZoneInfo("UTC"))
    )
    assert await token_service.is_token_blocklisted("blocklist-jti-1") is True
    assert await token_service.is_token_blocklisted("nonexistent-jti") is False


async def test_create_and_validate_refresh_token(db: AsyncSession):
    token_service = TokenService(db)
    refresh_token = await token_service.create_refresh_token(user_id=1)
    assert isinstance(refresh_token, str)
    assert len(refresh_token) > 0
    valid_token = await token_service.validate_refresh_token(refresh_token)
    assert valid_token is not None
    assert valid_token.user_id == 1
    assert valid_token.revoked is False


async def test_revoke_refresh_token(db: AsyncSession):
    token_service = TokenService(db)
    refresh_token = await token_service.create_refresh_token(user_id=1)
    await token_service.revoke_refresh_token(refresh_token)
    result = await token_service.validate_refresh_token(refresh_token)
    assert result is None


async def test_revoke_all_user_refresh_tokens(db: AsyncSession):
    token_service = TokenService(db)
    token1 = await token_service.create_refresh_token(user_id=1)
    token2 = await token_service.create_refresh_token(user_id=1)
    token3 = await token_service.create_refresh_token(user_id=2)
    await token_service.revoke_all_user_refresh_tokens(user_id=1)
    assert await token_service.validate_refresh_token(token1) is None
    assert await token_service.validate_refresh_token(token2) is None
    assert await token_service.validate_refresh_token(token3) is not None


async def test_cleanup_expired_tokens(db: AsyncSession):
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo

    from sqlmodel import select

    from app.db.models import BlocklistedToken, RefreshToken

    utc = ZoneInfo("UTC")
    token_service = TokenService(db)
    now = datetime.now(utc)

    expired_bl = BlocklistedToken(jti="expired-jti", exp=now - timedelta(hours=1))
    db.add(expired_bl)
    valid_bl = BlocklistedToken(jti="valid-jti", exp=now + timedelta(hours=1))
    db.add(valid_bl)
    expired_rt = RefreshToken(
        token="expired-rt", user_id=1, expires_at=now - timedelta(hours=1)
    )
    db.add(expired_rt)
    valid_rt = RefreshToken(
        token="valid-rt", user_id=1, expires_at=now + timedelta(hours=1)
    )
    db.add(valid_rt)
    await db.commit()

    deleted_count = await token_service.cleanup_expired_tokens()
    assert deleted_count == 2

    result = await db.execute(
        select(BlocklistedToken).where(BlocklistedToken.jti == "expired-jti")
    )
    assert result.scalar_one_or_none() is None
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token == "expired-rt")
    )
    assert result.scalar_one_or_none() is None
    result = await db.execute(
        select(BlocklistedToken).where(BlocklistedToken.jti == "valid-jti")
    )
    assert result.scalar_one_or_none() is not None
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token == "valid-rt")
    )
    assert result.scalar_one_or_none() is not None


async def test_access_token_contains_jti_and_iat(db: AsyncSession):
    import jwt

    from app.core.config import settings
    from app.services.user import UserService

    user_service = UserService(db)
    token = user_service.create_access_token(
        data={"sub": "testuser", "id": 1, "role": "user"}
    )
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

    assert "jti" in payload
    assert isinstance(payload["jti"], str)
    assert len(payload["jti"]) > 0

    assert "iat" in payload
    assert isinstance(payload["iat"], int)
