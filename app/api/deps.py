from collections.abc import AsyncGenerator

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from jose.exceptions import JWTError
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import User, UserRole
from app.db.session import get_session
from app.schemas.user import TokenPayload

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    # Note: we call 'get_session()' (don't await it) so FastAPI can use it as a
    # dependency. This is because get_session returns an async generator which will
    # be awaited by FastAPI
    async for session in get_session():
        yield session


async def get_current_user(
    db: AsyncSession = Depends(get_db),  # noqa: B008
    token: str = Depends(oauth2_scheme),  # noqa: B008
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
    except (JWTError, ValidationError):
        raise credentials_exception
    
    from app.services.user import UserService
    
    user_service = UserService(db)
    user = await user_service.get_user_by_id(token_data.id)
    
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> User:
    """
    Get current active user.
    """
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


async def get_current_active_superuser(
    current_user: User = Depends(get_current_active_user),  # noqa: B008
) -> User:
    """
    Get current active superuser.
    """
    if current_user.role != UserRole.SUPERUSER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have sufficient privileges",
        )
    return current_user


async def get_current_active_admin_user(
    current_user: User = Depends(get_current_active_user),  # noqa: B008
) -> User:
    """
    Get current active user with admin privileges (ADMIN or SUPERUSER).
    """
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPERUSER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have sufficient privileges",
        )
    return current_user
