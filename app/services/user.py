from datetime import datetime, timedelta
from typing import Any, Optional
from zoneinfo import ZoneInfo

from jose import jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.config import logger, settings
from app.db.models import User, UserRole

UTC = ZoneInfo("UTC")

# Setup password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_user_by_username(self, username: str) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def create_user(
        self,
        username: str,
        email: str,
        password: str,
        role: UserRole = UserRole.USER,
        organization_id: Optional[int] = None,
    ) -> User:
        logger.debug(f"Creating user: {username}, role: {role}")
        hashed_password = get_password_hash(password)

        user = User(
            username=username,
            email=email,
            hashed_password=hashed_password,
            role=role,
            organization_id=organization_id,
        )

        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)

        logger.debug(f"User created successfully: {username} with ID {user.id}")
        return user

    async def update_user(
        self,
        user_id: int,
        email: Optional[str] = None,
        password: Optional[str] = None,
        role: Optional[UserRole] = None,
        is_active: Optional[bool] = None,
        organization_id: Optional[int] = None,
    ) -> Optional[User]:
        user = await self.get_user_by_id(user_id)

        if not user:
            return None

        if email is not None:
            user.email = email

        if password is not None:
            user.hashed_password = get_password_hash(password)

        if role is not None:
            user.role = role

        if is_active is not None:
            user.is_active = is_active

        if organization_id is not None:
            user.organization_id = organization_id

        user.updated_at = datetime.now(UTC)

        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)

        return user

    async def delete_user(self, user_id: int) -> bool:
        user = await self.get_user_by_id(user_id)

        if not user:
            return False

        await self.db.delete(user)
        await self.db.commit()

        return True

    async def authenticate_user(self, username: str, password: str) -> Optional[User]:
        logger.debug(f"Authenticating user: {username}")
        user = await self.get_user_by_username(username)

        if not user:
            logger.debug(f"User not found: {username}")
            return None

        if not user.is_active:
            logger.debug(f"User is inactive: {username}")
            return None

        if not verify_password(password, user.hashed_password):
            logger.debug(f"Invalid password for user: {username}")
            return None

        logger.debug(f"Authentication successful: {username}")
        return user

    def create_access_token(
        self, data: dict[str, Any], expires_delta: Optional[timedelta] = None
    ) -> str:
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.now(UTC) + expires_delta
        else:
            expire = datetime.now(UTC) + timedelta(
                minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
            )

        to_encode.update({"exp": expire.timestamp()})

        encoded_jwt = jwt.encode(
            to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
        )

        return encoded_jwt
