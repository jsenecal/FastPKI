import logging
from typing import Any, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("fastpki")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore"
    )

    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "FastPKI"

    # Database settings
    DATABASE_URL: Optional[str] = "sqlite+aiosqlite:///./fastpki.db"
    DATABASE_CONNECT_ARGS: dict[str, Any] = {}

    @field_validator("DATABASE_URL")
    def validate_database_url(cls, v: Optional[str]) -> Any:  # noqa: N805
        if v and v.startswith("sqlite"):
            if not v.startswith("sqlite+aiosqlite"):
                return v.replace("sqlite", "sqlite+aiosqlite")
            return v
        if v and v.startswith("postgresql"):
            return v.replace("postgresql", "postgresql+asyncpg")
        return v

    # CA settings
    CA_KEY_SIZE: int = 4096
    CA_CERT_DAYS: int = 3650  # 10 years
    CERT_KEY_SIZE: int = 2048
    CERT_DAYS: int = 365  # 1 year

    # Security settings
    SECRET_KEY: str = "supersecretkey"  # Change in production
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day
    ALGORITHM: str = "HS256"

    # Logging
    LOG_LEVEL: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL

    # CORS settings
    BACKEND_CORS_ORIGINS: list[str] = ["*"]


settings = Settings()

# Update logging level based on settings
log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
logger.setLevel(log_level)
