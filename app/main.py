import asyncio
import contextlib
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response

from app.api import api_router
from app.api.auth import limiter
from app.api.pki import ca_router, crl_router
from app.core.config import logger, settings
from app.db.session import create_db_and_tables
from app.services.encryption import encrypt_existing_keys


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: StarletteRequest,
        call_next: Callable[[StarletteRequest], Awaitable[Response]],
    ) -> Response:
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Strict-Transport-Security"] = (
            "max-age=63072000; includeSubDomains"
        )
        return response


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
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Token GC: error during cleanup")


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


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]
app.add_middleware(SlowAPIMiddleware)

# Set all CORS enabled origins
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.add_middleware(SecurityHeadersMiddleware)

app.include_router(api_router, prefix=settings.API_V1_STR)
app.include_router(crl_router, prefix="/crl", tags=["pki"])
app.include_router(ca_router, prefix="/ca", tags=["pki"])


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Welcome to FastPKI - API-based PKI management system."}
