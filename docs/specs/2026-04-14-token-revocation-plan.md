# Token Revocation & Refresh Tokens Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add token revocation (logout, invalidate-all) and refresh token rotation to the FastPKI auth system, reducing access token TTL from 24 hours to 15 minutes.

**Architecture:** Database-backed blocklist for individual token revocation, `tokens_invalidated_at` timestamp on User for mass invalidation, opaque refresh tokens with rotation. Background GC task cleans expired entries hourly.

**Tech Stack:** SQLModel, FastAPI, PyJWT, Alembic, asyncio

---

### File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `app/db/models.py` | Modify | Add `BlocklistedToken`, `RefreshToken` models; add `tokens_invalidated_at` to `User` |
| `app/schemas/user.py` | Modify | Add `refresh_token` to `Token`, `jti`/`iat` to `TokenPayload`, new `RefreshTokenRequest` schema |
| `app/core/config.py` | Modify | Change `ACCESS_TOKEN_EXPIRE_MINUTES` default to 15, add `REFRESH_TOKEN_EXPIRE_MINUTES` |
| `app/services/token.py` | Create | `TokenService` with blocklist/refresh token CRUD and GC logic |
| `app/services/user.py` | Modify | Add `jti`+`iat` to `create_access_token`, trigger revocation on password change/deactivation |
| `app/api/deps.py` | Modify | Add blocklist + `tokens_invalidated_at` checks in `get_current_user` |
| `app/api/auth.py` | Modify | Add `/refresh`, `/logout`, `/invalidate` endpoints; update login to return refresh token |
| `app/main.py` | Modify | Add GC background task to lifespan |
| `app/db/session.py` | Modify | Export `async_session_maker` for GC task |
| `alembic/versions/<new>_add_token_revocation.py` | Create | Migration for new tables + User column |
| `tests/test_services/test_token_service.py` | Create | Unit tests for `TokenService` |
| `tests/test_api/test_auth.py` | Modify | Integration tests for new endpoints |
| `tests/test_api/test_auth_dependencies.py` | Modify | Tests for blocklist/invalidation checks in `get_current_user` |

---

### Task 1: Database Models

**Files:**
- Modify: `app/db/models.py`
- Test: `tests/test_services/test_token_service.py` (created here, extended later)

- [ ] **Step 1: Write failing test for BlocklistedToken model**

Create `tests/test_services/test_token_service.py`:

```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import BlocklistedToken


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_services/test_token_service.py::test_create_blocklisted_token -v`
Expected: FAIL — `ImportError: cannot import name 'BlocklistedToken'`

- [ ] **Step 3: Write failing test for RefreshToken model**

Append to `tests/test_services/test_token_service.py`:

```python
from app.db.models import RefreshToken


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
```

- [ ] **Step 4: Write failing test for User.tokens_invalidated_at**

Append to `tests/test_services/test_token_service.py`:

```python
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
```

- [ ] **Step 5: Implement the three model changes**

In `app/db/models.py`, add `BlocklistedToken` and `RefreshToken` models, and add `tokens_invalidated_at` to `User`.

Add after the existing model imports at the top (the file already imports `Column`, `DateTime`, `Field`, `Relationship`, `SQLModel`, and `UTC`):

```python
class BlocklistedToken(SQLModel, table=True):
    __tablename__ = "blocklisted_token"

    id: int | None = Field(default=None, primary_key=True)
    jti: str = Field(index=True, unique=True)
    exp: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
```

```python
class RefreshToken(SQLModel, table=True):
    __tablename__ = "refresh_token"

    id: int | None = Field(default=None, primary_key=True)
    token: str = Field(index=True, unique=True)
    user_id: int = Field(foreign_key="users.id")
    expires_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    revoked: bool = Field(default=False)
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            default=lambda: datetime.now(UTC),
        )
    )
```

Add to the `User` model:

```python
    tokens_invalidated_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run pytest tests/test_services/test_token_service.py -v`
Expected: all 3 tests PASS

- [ ] **Step 7: Run linting**

Run: `uv run ruff check app/db/models.py tests/test_services/test_token_service.py && uv run ruff format app/db/models.py tests/test_services/test_token_service.py && uv run mypy app/db/models.py`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add app/db/models.py tests/test_services/test_token_service.py
git commit -m "feat: add BlocklistedToken, RefreshToken models and User.tokens_invalidated_at"
```

---

### Task 2: Schemas and Config

**Files:**
- Modify: `app/schemas/user.py`
- Modify: `app/core/config.py`

- [ ] **Step 1: Update Token schema**

In `app/schemas/user.py`, add `refresh_token` to `Token`:

```python
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
```

- [ ] **Step 2: Update TokenPayload schema**

In `app/schemas/user.py`, add `jti` and `iat` to `TokenPayload`:

```python
class TokenPayload(BaseModel):
    sub: str | None = None
    id: int | None = None
    role: str | None = None
    exp: int | None = None
    jti: str | None = None
    iat: int | None = None
```

- [ ] **Step 3: Add RefreshTokenRequest schema**

In `app/schemas/user.py`, add:

```python
class RefreshTokenRequest(BaseModel):
    refresh_token: str
```

- [ ] **Step 4: Update config defaults**

In `app/core/config.py`, change and add:

```python
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15  # 15 minutes
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
```

- [ ] **Step 5: Run existing tests to ensure nothing breaks**

Run: `uv run pytest tests/ -v --timeout=60`
Expected: all existing tests PASS (Token schema change may break tests that don't provide `refresh_token` — if so, `refresh_token` should have a default: `refresh_token: str = ""`)

Note: if tests fail because existing login responses don't include `refresh_token`, make the field optional temporarily: `refresh_token: str | None = None`. This will be made required once the login endpoint is updated in Task 5.

- [ ] **Step 6: Run linting**

Run: `uv run ruff check app/schemas/user.py app/core/config.py && uv run ruff format app/schemas/user.py app/core/config.py && uv run mypy app/schemas/user.py app/core/config.py`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add app/schemas/user.py app/core/config.py
git commit -m "feat: add refresh token schema, jti/iat to token payload, update TTL defaults"
```

---

### Task 3: TokenService

**Files:**
- Create: `app/services/token.py`
- Test: `tests/test_services/test_token_service.py` (extend)

- [ ] **Step 1: Write failing test for blocklist_token**

Append to `tests/test_services/test_token_service.py`:

```python
from app.services.token import TokenService


async def test_blocklist_token(db: AsyncSession):
    from datetime import datetime
    from zoneinfo import ZoneInfo

    token_service = TokenService(db)
    await token_service.blocklist_token(
        jti="blocklist-jti-1",
        exp=datetime.now(ZoneInfo("UTC")),
    )

    assert await token_service.is_token_blocklisted("blocklist-jti-1") is True
    assert await token_service.is_token_blocklisted("nonexistent-jti") is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_services/test_token_service.py::test_blocklist_token -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.token'`

- [ ] **Step 3: Write failing test for create_refresh_token and validate_refresh_token**

Append to `tests/test_services/test_token_service.py`:

```python
async def test_create_and_validate_refresh_token(db: AsyncSession):
    token_service = TokenService(db)
    refresh_token = await token_service.create_refresh_token(user_id=1)

    assert isinstance(refresh_token, str)
    assert len(refresh_token) > 0

    valid_token = await token_service.validate_refresh_token(refresh_token)
    assert valid_token is not None
    assert valid_token.user_id == 1
    assert valid_token.revoked is False
```

- [ ] **Step 4: Write failing test for revoke_refresh_token**

Append to `tests/test_services/test_token_service.py`:

```python
async def test_revoke_refresh_token(db: AsyncSession):
    token_service = TokenService(db)
    refresh_token = await token_service.create_refresh_token(user_id=1)

    await token_service.revoke_refresh_token(refresh_token)

    result = await token_service.validate_refresh_token(refresh_token)
    assert result is None
```

- [ ] **Step 5: Write failing test for revoke_all_user_refresh_tokens**

Append to `tests/test_services/test_token_service.py`:

```python
async def test_revoke_all_user_refresh_tokens(db: AsyncSession):
    token_service = TokenService(db)
    token1 = await token_service.create_refresh_token(user_id=1)
    token2 = await token_service.create_refresh_token(user_id=1)
    token3 = await token_service.create_refresh_token(user_id=2)

    await token_service.revoke_all_user_refresh_tokens(user_id=1)

    assert await token_service.validate_refresh_token(token1) is None
    assert await token_service.validate_refresh_token(token2) is None
    # User 2's token should still be valid
    assert await token_service.validate_refresh_token(token3) is not None
```

- [ ] **Step 6: Write failing test for cleanup_expired_tokens**

Append to `tests/test_services/test_token_service.py`:

```python
async def test_cleanup_expired_tokens(db: AsyncSession):
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo

    from sqlmodel import select

    from app.db.models import BlocklistedToken, RefreshToken

    UTC = ZoneInfo("UTC")
    token_service = TokenService(db)
    now = datetime.now(UTC)

    # Create expired blocklisted token
    expired_bl = BlocklistedToken(jti="expired-jti", exp=now - timedelta(hours=1))
    db.add(expired_bl)

    # Create valid blocklisted token
    valid_bl = BlocklistedToken(jti="valid-jti", exp=now + timedelta(hours=1))
    db.add(valid_bl)

    # Create expired refresh token
    expired_rt = RefreshToken(
        token="expired-rt",
        user_id=1,
        expires_at=now - timedelta(hours=1),
    )
    db.add(expired_rt)

    # Create valid refresh token
    valid_rt = RefreshToken(
        token="valid-rt",
        user_id=1,
        expires_at=now + timedelta(hours=1),
    )
    db.add(valid_rt)

    await db.commit()

    deleted_count = await token_service.cleanup_expired_tokens()
    assert deleted_count == 2

    # Verify expired entries are gone
    result = await db.execute(
        select(BlocklistedToken).where(BlocklistedToken.jti == "expired-jti")
    )
    assert result.scalar_one_or_none() is None

    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token == "expired-rt")
    )
    assert result.scalar_one_or_none() is None

    # Verify valid entries remain
    result = await db.execute(
        select(BlocklistedToken).where(BlocklistedToken.jti == "valid-jti")
    )
    assert result.scalar_one_or_none() is not None

    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token == "valid-rt")
    )
    assert result.scalar_one_or_none() is not None
```

- [ ] **Step 7: Implement TokenService**

Create `app/services/token.py`:

```python
import secrets
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.config import settings
from app.db.models import BlocklistedToken, RefreshToken

UTC = ZoneInfo("UTC")


class TokenService:
    def __init__(self, db: AsyncSession):
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
        from datetime import timedelta

        token = secrets.token_urlsafe(48)
        expires_at = datetime.now(UTC) + timedelta(
            minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES
        )
        refresh_token = RefreshToken(
            token=token,
            user_id=user_id,
            expires_at=expires_at,
        )
        self.db.add(refresh_token)
        await self.db.commit()
        return token

    async def validate_refresh_token(self, token: str) -> RefreshToken | None:
        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.token == token,
                RefreshToken.revoked == False,  # noqa: E712
                RefreshToken.expires_at > datetime.now(UTC),
            )
        )
        return result.scalar_one_or_none()

    async def revoke_refresh_token(self, token: str) -> None:
        result = await self.db.execute(
            select(RefreshToken).where(RefreshToken.token == token)
        )
        refresh_token = result.scalar_one_or_none()
        if refresh_token:
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
        for t in tokens:
            t.revoked = True
            self.db.add(t)
        await self.db.commit()

    async def cleanup_expired_tokens(self) -> int:
        now = datetime.now(UTC)

        # Delete expired blocklisted tokens
        result = await self.db.execute(
            select(BlocklistedToken).where(BlocklistedToken.exp < now)
        )
        expired_bl = result.scalars().all()

        # Delete expired refresh tokens
        result = await self.db.execute(
            select(RefreshToken).where(RefreshToken.expires_at < now)
        )
        expired_rt = result.scalars().all()

        count = len(expired_bl) + len(expired_rt)

        for entry in expired_bl:
            await self.db.delete(entry)
        for entry in expired_rt:
            await self.db.delete(entry)

        await self.db.commit()
        return count
```

- [ ] **Step 8: Run tests to verify they pass**

Run: `uv run pytest tests/test_services/test_token_service.py -v`
Expected: all tests PASS

- [ ] **Step 9: Run linting**

Run: `uv run ruff check app/services/token.py tests/test_services/test_token_service.py && uv run ruff format app/services/token.py tests/test_services/test_token_service.py && uv run mypy app/services/token.py`
Expected: PASS

- [ ] **Step 10: Commit**

```bash
git add app/services/token.py tests/test_services/test_token_service.py
git commit -m "feat: add TokenService with blocklist, refresh token CRUD, and GC"
```

---

### Task 4: Update create_access_token with jti and iat

**Files:**
- Modify: `app/services/user.py`
- Test: `tests/test_services/test_token_service.py` (extend)

- [ ] **Step 1: Write failing test**

Append to `tests/test_services/test_token_service.py`:

```python
import jwt

from app.core.config import settings
from app.services.user import UserService


async def test_access_token_contains_jti_and_iat(db: AsyncSession):
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_services/test_token_service.py::test_access_token_contains_jti_and_iat -v`
Expected: FAIL — `AssertionError: assert 'jti' in payload`

- [ ] **Step 3: Implement jti and iat in create_access_token**

In `app/services/user.py`, update `create_access_token`:

```python
    def create_access_token(
        self, data: dict[str, Any], expires_delta: timedelta | None = None
    ) -> str:
        import uuid

        to_encode = data.copy()

        now = datetime.now(UTC)
        if expires_delta:
            expire = now + expires_delta
        else:
            expire = now + timedelta(
                minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
            )

        to_encode.update({
            "exp": int(expire.timestamp()),
            "iat": int(now.timestamp()),
            "jti": str(uuid.uuid4()),
        })

        encoded_jwt: str = jwt.encode(
            to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
        )

        return encoded_jwt
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_services/test_token_service.py::test_access_token_contains_jti_and_iat -v`
Expected: PASS

- [ ] **Step 5: Run full test suite to check for regressions**

Run: `uv run pytest tests/ -v --timeout=60`
Expected: all tests PASS

- [ ] **Step 6: Run linting**

Run: `uv run ruff check app/services/user.py && uv run ruff format app/services/user.py && uv run mypy app/services/user.py`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add app/services/user.py tests/test_services/test_token_service.py
git commit -m "feat: add jti and iat claims to access tokens"
```

---

### Task 5: Update get_current_user with Blocklist and Invalidation Checks

**Files:**
- Modify: `app/api/deps.py`
- Test: `tests/test_api/test_auth_dependencies.py` (extend)

- [ ] **Step 1: Write failing test for blocklisted token rejection**

Append to `tests/test_api/test_auth_dependencies.py`:

```python
from app.services.token import TokenService


@pytest.mark.asyncio
async def test_get_current_user_blocklisted_token(
    db: AsyncSession, auth_test_user: User
):
    """Test that a blocklisted token is rejected."""
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo

    user_service = UserService(db)
    token = user_service.create_access_token(
        data={
            "sub": auth_test_user.username,
            "id": auth_test_user.id,
            "role": auth_test_user.role,
        }
    )

    # Decode to get jti and exp
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

    # Blocklist the token
    token_service = TokenService(db)
    await token_service.blocklist_token(
        jti=payload["jti"],
        exp=datetime.fromtimestamp(payload["exp"], tz=ZoneInfo("UTC")),
    )

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(token=token, db=db)

    assert exc_info.value.status_code == 401
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_api/test_auth_dependencies.py::test_get_current_user_blocklisted_token -v`
Expected: FAIL — blocklisted token is not rejected (no check exists yet)

- [ ] **Step 3: Write failing test for tokens_invalidated_at rejection**

Append to `tests/test_api/test_auth_dependencies.py`:

```python
@pytest.mark.asyncio
async def test_get_current_user_invalidated_tokens(
    db: AsyncSession, auth_test_user: User
):
    """Test that tokens issued before tokens_invalidated_at are rejected."""
    from datetime import datetime
    from zoneinfo import ZoneInfo

    user_service = UserService(db)
    token = user_service.create_access_token(
        data={
            "sub": auth_test_user.username,
            "id": auth_test_user.id,
            "role": auth_test_user.role,
        }
    )

    # Invalidate all tokens for this user
    auth_test_user.tokens_invalidated_at = datetime.now(ZoneInfo("UTC"))
    db.add(auth_test_user)
    await db.commit()
    await db.refresh(auth_test_user)

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(token=token, db=db)

    assert exc_info.value.status_code == 401
```

- [ ] **Step 4: Implement blocklist and invalidation checks in get_current_user**

In `app/api/deps.py`, update `get_current_user`:

```python
async def get_current_user(
    db: AsyncSession = Depends(get_session),  # noqa: B008
    token: str = Depends(oauth2_scheme),
) -> User:
    """
    Validate access token and return current user.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    except (InvalidTokenError, ValidationError) as err:
        raise credentials_exception from err

    # Check if token is blocklisted
    if token_data.jti:
        from app.services.token import TokenService

        token_service = TokenService(db)
        if await token_service.is_token_blocklisted(token_data.jti):
            raise credentials_exception

    from app.services.user import UserService

    user_service = UserService(db)
    user = await user_service.get_user_by_id(token_data.id)

    if user is None:
        raise credentials_exception

    # Check if user's tokens have been invalidated
    if user.tokens_invalidated_at and token_data.iat:
        if token_data.iat < int(user.tokens_invalidated_at.timestamp()):
            raise credentials_exception

    return user
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_api/test_auth_dependencies.py -v`
Expected: all tests PASS

- [ ] **Step 6: Run linting**

Run: `uv run ruff check app/api/deps.py tests/test_api/test_auth_dependencies.py && uv run ruff format app/api/deps.py tests/test_api/test_auth_dependencies.py && uv run mypy app/api/deps.py`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add app/api/deps.py tests/test_api/test_auth_dependencies.py
git commit -m "feat: add blocklist and token invalidation checks to get_current_user"
```

---

### Task 6: Auth Endpoints (login update, refresh, logout, invalidate)

**Files:**
- Modify: `app/api/auth.py`
- Test: `tests/test_api/test_auth.py` (extend)

- [ ] **Step 1: Write failing test for login returning refresh_token**

Append to `tests/test_api/test_auth.py`:

```python
@pytest.mark.asyncio
async def test_login_returns_refresh_token(client, db):
    user_data = {
        "username": "refreshloginuser",
        "email": "refreshlogin@example.com",
        "password": "password123",
    }
    await client.post("/api/v1/users/", json=user_data)

    response = await client.post(
        "/api/v1/auth/token",
        data={"username": "refreshloginuser", "password": "password123"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
```

- [ ] **Step 2: Write failing test for refresh endpoint**

Append to `tests/test_api/test_auth.py`:

```python
@pytest.mark.asyncio
async def test_refresh_token_endpoint(client, db):
    user_data = {
        "username": "refreshuser",
        "email": "refresh@example.com",
        "password": "password123",
    }
    await client.post("/api/v1/users/", json=user_data)

    login_response = await client.post(
        "/api/v1/auth/token",
        data={"username": "refreshuser", "password": "password123"},
    )
    refresh_token = login_response.json()["refresh_token"]

    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    # New refresh token should be different (rotation)
    assert data["refresh_token"] != refresh_token


@pytest.mark.asyncio
async def test_refresh_token_invalid(client, db):
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "invalid-token"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token_reuse_rejected(client, db):
    """Old refresh token should be rejected after rotation."""
    user_data = {
        "username": "reuseuser",
        "email": "reuse@example.com",
        "password": "password123",
    }
    await client.post("/api/v1/users/", json=user_data)

    login_response = await client.post(
        "/api/v1/auth/token",
        data={"username": "reuseuser", "password": "password123"},
    )
    old_refresh = login_response.json()["refresh_token"]

    # Use the refresh token once
    await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh},
    )

    # Try to use the old refresh token again
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh},
    )
    assert response.status_code == 401
```

- [ ] **Step 3: Write failing test for logout endpoint**

Append to `tests/test_api/test_auth.py`:

```python
@pytest.mark.asyncio
async def test_logout_endpoint(client, db):
    user_data = {
        "username": "logoutuser",
        "email": "logout@example.com",
        "password": "password123",
    }
    await client.post("/api/v1/users/", json=user_data)

    login_response = await client.post(
        "/api/v1/auth/token",
        data={"username": "logoutuser", "password": "password123"},
    )
    tokens = login_response.json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    response = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": tokens["refresh_token"]},
        headers=headers,
    )

    assert response.status_code == 204

    # Access token should now be rejected
    response = await client.get("/api/v1/users/me", headers=headers)
    assert response.status_code == 401
```

- [ ] **Step 4: Write failing test for invalidate endpoint**

Append to `tests/test_api/test_auth.py`:

```python
@pytest.mark.asyncio
async def test_invalidate_endpoint(client, db):
    user_data = {
        "username": "invalidateuser",
        "email": "invalidate@example.com",
        "password": "password123",
    }
    await client.post("/api/v1/users/", json=user_data)

    # Login twice to get two sessions
    login1 = await client.post(
        "/api/v1/auth/token",
        data={"username": "invalidateuser", "password": "password123"},
    )
    login2 = await client.post(
        "/api/v1/auth/token",
        data={"username": "invalidateuser", "password": "password123"},
    )

    tokens1 = login1.json()
    tokens2 = login2.json()
    headers1 = {"Authorization": f"Bearer {tokens1['access_token']}"}
    headers2 = {"Authorization": f"Bearer {tokens2['access_token']}"}

    # Invalidate all tokens using session 1
    response = await client.post("/api/v1/auth/invalidate", headers=headers1)
    assert response.status_code == 204

    # Both sessions should now be rejected
    response = await client.get("/api/v1/users/me", headers=headers1)
    assert response.status_code == 401

    response = await client.get("/api/v1/users/me", headers=headers2)
    assert response.status_code == 401

    # But user can still log in again
    login3 = await client.post(
        "/api/v1/auth/token",
        data={"username": "invalidateuser", "password": "password123"},
    )
    assert login3.status_code == 200
    headers3 = {"Authorization": f"Bearer {login3.json()['access_token']}"}
    response = await client.get("/api/v1/users/me", headers=headers3)
    assert response.status_code == 200
```

- [ ] **Step 5: Implement updated login and new endpoints**

In `app/api/auth.py`, update the login endpoint and add the three new endpoints:

```python
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.core.config import logger, settings
from app.db.models import AuditAction, User
from app.db.session import get_session
from app.schemas.user import RefreshTokenRequest, Token
from app.services.audit import AuditService
from app.services.token import TokenService
from app.services.user import UserService

UTC = ZoneInfo("UTC")

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.post("/token", response_model=Token)
@limiter.limit(settings.AUTH_RATE_LIMIT)
async def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),  # noqa: B008
    db: AsyncSession = Depends(get_session),  # noqa: B008
) -> Any:
    logger.debug("Login attempt for username: %s", form_data.username)
    user_service = UserService(db)
    user = await user_service.authenticate_user(form_data.username, form_data.password)

    audit_service = AuditService(db)

    if not user:
        logger.info("Failed login attempt for username: %s", form_data.username)
        await audit_service.log_action(
            action=AuditAction.LOGIN_FAILURE,
            username=form_data.username,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = user_service.create_access_token(
        data={"sub": user.username, "id": user.id, "role": user.role},
        expires_delta=access_token_expires,
    )

    token_service = TokenService(db)
    refresh_token = await token_service.create_refresh_token(user_id=user.id)

    await audit_service.log_action(
        action=AuditAction.LOGIN_SUCCESS,
        user_id=user.id,
        username=user.username,
        organization_id=user.organization_id,
    )

    logger.info("Successful login for user: %s", user.username)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post("/refresh", response_model=Token)
async def refresh_access_token(
    body: RefreshTokenRequest,
    db: AsyncSession = Depends(get_session),  # noqa: B008
) -> Any:
    token_service = TokenService(db)
    refresh_token = await token_service.validate_refresh_token(body.refresh_token)

    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    # Revoke old refresh token (rotation)
    await token_service.revoke_refresh_token(body.refresh_token)

    # Issue new tokens
    user_service = UserService(db)
    user = await user_service.get_user_by_id(refresh_token.user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    new_access_token = user_service.create_access_token(
        data={"sub": user.username, "id": user.id, "role": user.role},
        expires_delta=access_token_expires,
    )
    new_refresh_token = await token_service.create_refresh_token(user_id=user.id)

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
    }


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    body: RefreshTokenRequest,
    current_user: User = Depends(get_current_active_user),  # noqa: B008
    db: AsyncSession = Depends(get_session),  # noqa: B008
) -> None:
    # Extract jti and exp from the current access token
    # Re-decode from the authorization header
    from fastapi.security import OAuth2PasswordBearer

    oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/token")
    # We need the raw token — get it from the request
    # Since current_user is already validated, we can trust the token
    # But we need jti/exp — re-extract from deps
    # Alternative: pass token through dependency
    pass


@router.post("/invalidate", status_code=status.HTTP_204_NO_CONTENT)
async def invalidate_all_tokens(
    current_user: User = Depends(get_current_active_user),  # noqa: B008
    db: AsyncSession = Depends(get_session),  # noqa: B008
) -> None:
    # Set tokens_invalidated_at on user
    current_user.tokens_invalidated_at = datetime.now(UTC)
    db.add(current_user)

    # Revoke all refresh tokens
    token_service = TokenService(db)
    await token_service.revoke_all_user_refresh_tokens(user_id=current_user.id)

    await db.commit()
```

**Note:** The `/logout` endpoint needs the raw JWT token to extract `jti`. Update `app/api/deps.py` to also provide the raw token. Add a new dependency:

```python
async def get_current_user_with_token(
    db: AsyncSession = Depends(get_session),  # noqa: B008
    token: str = Depends(oauth2_scheme),
) -> tuple[User, str]:
    """Validate access token and return current user with the raw token."""
    user = await get_current_user(db=db, token=token)
    return user, token
```

Then update the `/logout` endpoint to use it:

```python
@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    body: RefreshTokenRequest,
    user_and_token: tuple[User, str] = Depends(get_current_user_with_token),  # noqa: B008
    db: AsyncSession = Depends(get_session),  # noqa: B008
) -> None:
    current_user, raw_token = user_and_token

    # Decode token to get jti and exp
    payload = jwt.decode(
        raw_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
    )

    token_service = TokenService(db)

    # Blocklist the access token
    if payload.get("jti"):
        exp = datetime.fromtimestamp(payload["exp"], tz=UTC)
        await token_service.blocklist_token(jti=payload["jti"], exp=exp)

    # Revoke the refresh token
    await token_service.revoke_refresh_token(body.refresh_token)
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run pytest tests/test_api/test_auth.py -v`
Expected: all tests PASS

- [ ] **Step 7: Run full test suite**

Run: `uv run pytest tests/ -v --timeout=60`
Expected: all tests PASS

- [ ] **Step 8: Run linting**

Run: `uv run ruff check app/api/auth.py app/api/deps.py tests/test_api/test_auth.py && uv run ruff format app/api/auth.py app/api/deps.py tests/test_api/test_auth.py && uv run mypy app/api/auth.py app/api/deps.py`
Expected: PASS

- [ ] **Step 9: Commit**

```bash
git add app/api/auth.py app/api/deps.py tests/test_api/test_auth.py
git commit -m "feat: add refresh, logout, and invalidate auth endpoints"
```

---

### Task 7: Automatic Revocation on Password Change and Deactivation

**Files:**
- Modify: `app/services/user.py`
- Test: `tests/test_services/test_token_service.py` (extend)

- [ ] **Step 1: Write failing test for password change triggering revocation**

Append to `tests/test_services/test_token_service.py`:

```python
from app.db.models import UserRole


async def test_password_change_invalidates_tokens(db: AsyncSession):
    user_service = UserService(db)
    user = await user_service.create_user(
        username="pwchangeuser",
        email="pwchange@example.com",
        password="password123",
        role=UserRole.USER,
    )

    token_service = TokenService(db)
    refresh = await token_service.create_refresh_token(user_id=user.id)

    assert user.tokens_invalidated_at is None

    # Change password
    updated_user = await user_service.update_user(user.id, password="newpassword456")

    assert updated_user is not None
    assert updated_user.tokens_invalidated_at is not None

    # Refresh token should be revoked
    result = await token_service.validate_refresh_token(refresh)
    assert result is None
```

- [ ] **Step 2: Write failing test for deactivation triggering revocation**

Append to `tests/test_services/test_token_service.py`:

```python
async def test_deactivation_invalidates_tokens(db: AsyncSession):
    user_service = UserService(db)
    user = await user_service.create_user(
        username="deactuser",
        email="deact@example.com",
        password="password123",
        role=UserRole.USER,
    )

    token_service = TokenService(db)
    refresh = await token_service.create_refresh_token(user_id=user.id)

    # Deactivate user
    updated_user = await user_service.update_user(user.id, is_active=False)

    assert updated_user is not None
    assert updated_user.tokens_invalidated_at is not None

    # Refresh token should be revoked
    result = await token_service.validate_refresh_token(refresh)
    assert result is None
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/test_services/test_token_service.py::test_password_change_invalidates_tokens tests/test_services/test_token_service.py::test_deactivation_invalidates_tokens -v`
Expected: FAIL — `tokens_invalidated_at` is still None after update

- [ ] **Step 4: Implement automatic revocation in update_user**

In `app/services/user.py`, update the `update_user` method. After the existing password and is_active update blocks, add revocation logic:

```python
    async def update_user(
        self,
        user_id: int,
        email: str | None = None,
        password: str | None = None,
        role: UserRole | None = None,
        is_active: bool | None = None,
        organization_id: int | None = None,
        can_create_ca: bool | None = None,
        can_create_cert: bool | None = None,
        can_revoke_cert: bool | None = None,
        can_export_private_key: bool | None = None,
        can_delete_ca: bool | None = None,
    ) -> User | None:
        user = await self.get_user_by_id(user_id)

        if not user:
            return None

        should_invalidate_tokens = False

        if email is not None:
            user.email = email

        if password is not None:
            user.hashed_password = get_password_hash(password)
            should_invalidate_tokens = True

        if role is not None:
            user.role = role

        if is_active is not None:
            user.is_active = is_active
            if not is_active:
                should_invalidate_tokens = True

        if organization_id is not None:
            user.organization_id = organization_id

        if can_create_ca is not None:
            user.can_create_ca = can_create_ca

        if can_create_cert is not None:
            user.can_create_cert = can_create_cert

        if can_revoke_cert is not None:
            user.can_revoke_cert = can_revoke_cert

        if can_export_private_key is not None:
            user.can_export_private_key = can_export_private_key

        if can_delete_ca is not None:
            user.can_delete_ca = can_delete_ca

        if should_invalidate_tokens:
            user.tokens_invalidated_at = datetime.now(UTC)
            from app.services.token import TokenService

            token_service = TokenService(self.db)
            await token_service.revoke_all_user_refresh_tokens(user_id=user_id)

        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)

        return user
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_services/test_token_service.py -v`
Expected: all tests PASS

- [ ] **Step 6: Run full test suite**

Run: `uv run pytest tests/ -v --timeout=60`
Expected: all tests PASS

- [ ] **Step 7: Run linting**

Run: `uv run ruff check app/services/user.py && uv run ruff format app/services/user.py && uv run mypy app/services/user.py`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add app/services/user.py tests/test_services/test_token_service.py
git commit -m "feat: auto-revoke tokens on password change and user deactivation"
```

---

### Task 8: Background GC Task

**Files:**
- Modify: `app/main.py`
- Modify: `app/db/session.py`

- [ ] **Step 1: Export async_session_maker from session.py**

In `app/db/session.py`, create a module-level session factory:

```python
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel

from app.core.config import settings

connect_args = settings.DATABASE_CONNECT_ARGS
if settings.DATABASE_URL and settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False, **connect_args}

engine = create_async_engine(
    str(settings.DATABASE_URL),
    echo=False,
    future=True,
    connect_args=connect_args,
)

async_session_factory = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def create_db_and_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session
```

- [ ] **Step 2: Add GC loop to lifespan**

In `app/main.py`, add the GC background task:

```python
import asyncio
import contextlib

# Add to the existing imports

async def token_gc_loop() -> None:
    """Periodically clean up expired blocklisted and refresh tokens."""
    from app.db.session import async_session_factory
    from app.services.token import TokenService

    while True:
        await asyncio.sleep(3600)  # Run every hour
        try:
            async with async_session_factory() as session:
                token_service = TokenService(session)
                deleted = await token_service.cleanup_expired_tokens()
                if deleted > 0:
                    logger.info("Token GC: cleaned up %d expired entries", deleted)
        except Exception:
            logger.exception("Token GC: error during cleanup")
```

Update the lifespan:

```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await create_db_and_tables()
    await encrypt_existing_keys()
    gc_task = asyncio.create_task(token_gc_loop())
    try:
        yield
    finally:
        gc_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await gc_task
```

- [ ] **Step 3: Run full test suite**

Run: `uv run pytest tests/ -v --timeout=60`
Expected: all tests PASS

- [ ] **Step 4: Run linting**

Run: `uv run ruff check app/main.py app/db/session.py && uv run ruff format app/main.py app/db/session.py && uv run mypy app/main.py app/db/session.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/main.py app/db/session.py
git commit -m "feat: add background GC task for expired tokens"
```

---

### Task 9: Alembic Migration

**Files:**
- Create: `alembic/versions/<hash>_add_token_revocation.py`

- [ ] **Step 1: Generate migration**

Run: `uv run alembic revision --autogenerate -m "add token revocation tables and user invalidation column"`

- [ ] **Step 2: Review generated migration**

Verify it contains:
- `op.create_table("blocklisted_token", ...)` with `jti` (String, unique), `exp` (DateTime(timezone=True))
- `op.create_table("refresh_token", ...)` with `token` (String, unique), `user_id` (Integer, FK), `expires_at` (DateTime(timezone=True)), `revoked` (Boolean), `created_at` (DateTime(timezone=True))
- Index on `blocklisted_token.jti` and `refresh_token.token`
- `batch_alter_table("users")` adding `tokens_invalidated_at` (DateTime(timezone=True), nullable=True)
- Proper `downgrade()` dropping the tables and column

- [ ] **Step 3: Test migration**

Run: `uv run alembic upgrade head`
Expected: migration applies without errors

Run: `uv run alembic downgrade -1`
Expected: rollback succeeds

Run: `uv run alembic upgrade head`
Expected: re-apply succeeds

- [ ] **Step 4: Run full test suite**

Run: `uv run pytest tests/ -v --timeout=60`
Expected: all tests PASS

- [ ] **Step 5: Commit**

```bash
git add alembic/versions/
git commit -m "feat: add migration for token revocation tables"
```

---

### Task 10: Update Documentation

**Files:**
- Modify: `docs/security/authentication.md`
- Modify: `docs/reference/configuration.md`
- Modify: `docs/reference/api.md`
- Modify: `.env.example`

- [ ] **Step 1: Update authentication docs**

Add a "Token Lifecycle" section to `docs/security/authentication.md` covering:
- Access token TTL (15 min default)
- Refresh token TTL (24 hours)
- Token rotation on refresh
- Logout (single session)
- Invalidate (all sessions)
- Automatic revocation on password change / deactivation

- [ ] **Step 2: Update configuration reference**

Add `REFRESH_TOKEN_EXPIRE_MINUTES` to `docs/reference/configuration.md` and update `ACCESS_TOKEN_EXPIRE_MINUTES` default from 1440 to 15.

- [ ] **Step 3: Update API reference**

Add the three new endpoints to `docs/reference/api.md`:
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `POST /api/v1/auth/invalidate`

- [ ] **Step 4: Update .env.example**

Update `ACCESS_TOKEN_EXPIRE_MINUTES=15` and add `REFRESH_TOKEN_EXPIRE_MINUTES=1440`.

- [ ] **Step 5: Commit**

```bash
git add docs/security/authentication.md docs/reference/configuration.md docs/reference/api.md .env.example
git commit -m "docs: update authentication docs for token revocation and refresh tokens"
```

---

### Task 11: Final Verification

- [ ] **Step 1: Run full test suite**

Run: `uv run pytest tests/ -v --timeout=60`
Expected: all tests PASS

- [ ] **Step 2: Run linting and type checking**

Run: `uv run ruff check app tests && uv run ruff format app tests && uv run mypy app`
Expected: PASS

- [ ] **Step 3: Close issue #10**

Run: `gh issue close 10 --comment "Implemented in this branch: reduced access token TTL to 15 minutes, added refresh tokens with rotation, logout endpoint, invalidate-all endpoint, automatic revocation on password change/deactivation, and background GC for expired tokens."`
