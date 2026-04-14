import secrets
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.config import settings
from app.db.models import BlocklistedToken, RefreshToken

UTC = ZoneInfo("UTC")


class TokenService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def blocklist_token(self, jti: str, exp: datetime) -> None:
        entry = BlocklistedToken(jti=jti, exp=exp)
        self.db.add(entry)
        await self.db.commit()

    async def is_token_blocklisted(self, jti: str) -> bool:
        result = await self.db.execute(
            select(BlocklistedToken).where(BlocklistedToken.jti == jti)
        )
        return result.scalar_one_or_none() is not None

    async def create_refresh_token(self, user_id: int) -> str:
        token_str = secrets.token_urlsafe(48)
        expires_at = datetime.now(UTC) + timedelta(
            minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES
        )
        token = RefreshToken(token=token_str, user_id=user_id, expires_at=expires_at)
        self.db.add(token)
        await self.db.commit()
        return token_str

    async def validate_refresh_token(self, token: str) -> RefreshToken | None:
        now = datetime.now(UTC)
        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.token == token,
                RefreshToken.revoked == False,  # noqa: E712
                RefreshToken.expires_at > now,
            )
        )
        return result.scalar_one_or_none()

    async def revoke_refresh_token(self, token: str) -> None:
        result = await self.db.execute(
            select(RefreshToken).where(RefreshToken.token == token)
        )
        refresh_token = result.scalar_one_or_none()
        if refresh_token is not None:
            refresh_token.revoked = True
            self.db.add(refresh_token)
            await self.db.commit()

    async def revoke_all_user_refresh_tokens(self, user_id: int) -> None:
        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked == False,  # noqa: E712
            )
        )
        tokens = result.scalars().all()
        for token in tokens:
            token.revoked = True
            self.db.add(token)
        await self.db.commit()

    async def cleanup_expired_tokens(self) -> int:
        now = datetime.now(UTC)
        count = 0

        bl_result = await self.db.execute(
            select(BlocklistedToken).where(BlocklistedToken.exp < now)
        )
        expired_bl = bl_result.scalars().all()
        for bl_entry in expired_bl:
            await self.db.delete(bl_entry)
            count += 1

        rt_result = await self.db.execute(
            select(RefreshToken).where(RefreshToken.expires_at < now)
        )
        expired_rt = rt_result.scalars().all()
        for rt_entry in expired_rt:
            await self.db.delete(rt_entry)
            count += 1

        await self.db.commit()
        return count
