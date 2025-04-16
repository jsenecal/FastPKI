import asyncio
import logging
import os
from collections.abc import AsyncGenerator
from datetime import timedelta
from typing import Optional

import pytest_asyncio
from fastapi import Depends, FastAPI
from fastapi.security import OAuth2PasswordBearer
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from sqlmodel import SQLModel

from app.api import api_router
from app.api.deps import get_current_active_user, get_current_user
from app.core.config import logger, settings
from app.db.models import User, UserRole
from app.db.session import get_session
from app.services.user import UserService

# Set logger to DEBUG for tests
logger.setLevel(logging.DEBUG)


# Test database
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

# Create async engine for tests
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    poolclass=NullPool,
    connect_args={"check_same_thread": False},
)

# Create test session
test_session_maker = sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)


async def get_test_session() -> AsyncGenerator[AsyncSession, None]:
    async with test_session_maker() as session:
        yield session


# App for testing
def create_test_app() -> FastAPI:
    app = FastAPI()
    app.include_router(api_router, prefix=settings.API_V1_STR)
    return app


@pytest_asyncio.fixture(scope="session")
async def event_loop():
    """Create an event loop for testing."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def setup_db():
    # Create the test database and tables
    # Log the setup
    logger.debug("Setting up test database")

    # Remove existing test database file first
    if os.path.exists("./test.db"):
        os.remove("./test.db")

    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
        await conn.run_sync(SQLModel.metadata.create_all)
    yield
    # Clean up after tests
    logger.debug("Tearing down test database")
    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)

    # Remove test database file
    if os.path.exists("./test.db"):
        os.remove("./test.db")


@pytest_asyncio.fixture
async def db(setup_db) -> AsyncGenerator[AsyncSession, None]:
    async with test_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


@pytest_asyncio.fixture
async def client(setup_db) -> AsyncGenerator[AsyncClient, None]:
    app = create_test_app()

    # Override the dependency
    app.dependency_overrides[get_session] = get_test_session

    # Create test client using ASGITransport
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


# User fixtures for testing
@pytest_asyncio.fixture
async def superuser(db) -> User:
    """Create and return a superuser for testing."""
    user_service = UserService(db)
    user = await user_service.get_user_by_username("testsuper")
    if not user:
        user = await user_service.create_user(
            username="testsuper",
            email="super@example.com",
            password="password123",
            role=UserRole.SUPERUSER,
        )
    return user


@pytest_asyncio.fixture
async def admin_user(db) -> User:
    """Create and return an admin user for testing."""
    user_service = UserService(db)
    user = await user_service.get_user_by_username("testadmin")
    if not user:
        user = await user_service.create_user(
            username="testadmin",
            email="admin@example.com",
            password="password123",
            role=UserRole.ADMIN,
        )
    return user


@pytest_asyncio.fixture
async def normal_user(db) -> User:
    """Create and return a normal user for testing."""
    user_service = UserService(db)
    user = await user_service.get_user_by_username("testuser")
    if not user:
        user = await user_service.create_user(
            username="testuser",
            email="user@example.com",
            password="password123",
            role=UserRole.USER,
        )
    return user


# Token fixtures
@pytest_asyncio.fixture
async def superuser_token(superuser, db) -> str:
    """Create and return a token for the superuser."""
    user_service = UserService(db)
    token = user_service.create_access_token(
        data={"sub": superuser.username, "id": superuser.id, "role": superuser.role},
        expires_delta=timedelta(minutes=30),
    )
    return token


@pytest_asyncio.fixture
async def admin_token(admin_user, db) -> str:
    """Create and return a token for the admin user."""
    user_service = UserService(db)
    token = user_service.create_access_token(
        data={"sub": admin_user.username, "id": admin_user.id, "role": admin_user.role},
        expires_delta=timedelta(minutes=30),
    )
    return token


@pytest_asyncio.fixture
async def normal_user_token(normal_user, db) -> str:
    """Create and return a token for the normal user."""
    user_service = UserService(db)
    token = user_service.create_access_token(
        data={"sub": normal_user.username, "id": normal_user.id, "role": normal_user.role},
        expires_delta=timedelta(minutes=30),
    )
    return token


# Token header fixtures
@pytest_asyncio.fixture
async def superuser_token_headers(superuser_token) -> dict:
    """Return Authorization headers for superuser."""
    return {"Authorization": f"Bearer {superuser_token}"}


@pytest_asyncio.fixture
async def admin_token_headers(admin_token) -> dict:
    """Return Authorization headers for admin user."""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest_asyncio.fixture
async def normal_user_token_headers(normal_user_token) -> dict:
    """Return Authorization headers for normal user."""
    return {"Authorization": f"Bearer {normal_user_token}"}


# Override authentication for tests
class TestAuth:
    def __init__(self, user: Optional[User] = None):
        self.user = user

    async def __call__(self, *args, **kwargs):
        return self.user


@pytest_asyncio.fixture
def auth_override_app():
    """Return a function that creates an app with auth override."""

    def _auth_override_app(user: Optional[User] = None):
        app = create_test_app()
        
        # Override the dependency
        app.dependency_overrides[get_session] = get_test_session
        app.dependency_overrides[get_current_user] = TestAuth(user)
        app.dependency_overrides[get_current_active_user] = TestAuth(user)
        
        return app

    return _auth_override_app
