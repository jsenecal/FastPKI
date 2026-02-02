from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import logger, settings
from app.db.models import AuditAction
from app.db.session import get_session
from app.schemas.user import Token
from app.services.audit import AuditService
from app.services.user import UserService

router = APIRouter()


@router.post("/token", response_model=Token)
async def login_for_access_token(
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

    await audit_service.log_action(
        action=AuditAction.LOGIN_SUCCESS,
        user_id=user.id,
        username=user.username,
        organization_id=user.organization_id,
    )

    logger.info("Successful login for user: %s", user.username)
    return {"access_token": access_token, "token_type": "bearer"}
