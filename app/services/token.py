import secrets
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import delete, update
from sqlalchemy.exc import IntegrityError
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
        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()

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
                RefreshToken.revoked.is_(False),  # type: ignore[attr-defined]
                RefreshToken.expires_at > now,
            )
        )
        return result.scalar_one_or_none()

    async def validate_and_revoke_refresh_token(
        self, token: str
    ) -> RefreshToken | None:
        """Atomically validate and revoke a refresh token."""
        now = datetime.now(UTC)
        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.token == token,
                RefreshToken.revoked.is_(False),  # type: ignore[attr-defined]
                RefreshToken.expires_at > now,
            )
        )
        refresh_token = result.scalar_one_or_none()
        if refresh_token is not None:
            refresh_token.revoked = True
            self.db.add(refresh_token)
            await self.db.commit()
        return refresh_token

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
        await self.db.execute(
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,  # type: ignore[arg-type]
                RefreshToken.revoked.is_(False),  # type: ignore[attr-defined]
            )
            .values(revoked=True)
        )
        await self.db.commit()

    async def cleanup_expired_tokens(self) -> int:
        now = datetime.now(UTC)

        bl_result = await self.db.execute(
            delete(BlocklistedToken).where(
                BlocklistedToken.exp < now  # type: ignore[arg-type]
            )
        )
        bl_count: int = bl_result.rowcount  # type: ignore[attr-defined]

        rt_result = await self.db.execute(
            delete(RefreshToken).where(
                RefreshToken.expires_at < now  # type: ignore[arg-type]
            )
        )
        rt_count: int = rt_result.rowcount  # type: ignore[attr-defined]

        await self.db.commit()
        return bl_count + rt_count
