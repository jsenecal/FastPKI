from typing import AsyncGenerator, Awaitable

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    # Note: we call 'get_session()' (don't await it) so FastAPI can use it as a dependency
    # This is because get_session returns an async generator which will be awaited by FastAPI
    async for session in get_session():
        yield session