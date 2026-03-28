"""Aurora backend configuration (Pydantic BaseSettings)."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    AURORA_ENV: str = "development"
    DATABASE_URL: str = "postgresql+asyncpg://aurora_app:aurora_dev@localhost:5432/aurora"
    REDIS_URL: str = "redis://localhost:6379/0"

    S3_ENDPOINT_URL: str | None = None
    S3_BUCKET: str = "aurora-audio"
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_REGION: str = "us-east-1"

    JWT_PUBLIC_KEY_PATH: str | None = None
    JWT_PRIVATE_KEY_PATH: str | None = None
    JWT_ALGORITHM: str = "RS256"

    ANTHROPIC_API_KEY: str | None = None
    STRIPE_SECRET_KEY: str | None = None
    STRIPE_WEBHOOK_SECRET: str | None = None
    STRIPE_PRICE_ARTIST_ID: str | None = None
    STRIPE_PRICE_PRO_ID: str | None = None

    NORMALIZATION_VALIDATED: bool = False
    COLLAB_MAX_USERS_PER_SESSION: int = 8
    AURORA_CERT_SIGNING_KEY_PATH: str | None = None
    AURORA_ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:80"

    # Domain and environment
    DOMAIN: str = "localhost"
    ENVIRONMENT: str = "development"

    # Optional JWT private key inline (alternative to file path)
    JWT_PRIVATE_KEY: str | None = None


settings = Settings()
