import os
from pydantic_settings import BaseSettings, SettingsConfigDict

_env_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+psycopg://pulse_user:pulse_password@localhost:5432/engagement_pulse_fastapi"
    JWT_SECRET_KEY: str | None = None
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    REDIS_URL: str = "redis://127.0.0.1:6379/0"
    DRAMATIQ_QUEUE_NAME: str = "fastapi"
    CSV_UPLOAD_DIR: str = "media/csv_imports"

    # Development-only seed credentials (read from environment/.env, never hardcoded)
    SEED_CONSULTANT_PASSWORD: str | None = None
    SEED_CLIENT_VIEWER_PASSWORD: str | None = None
    SEED_PASSWORD: str | None = None

    model_config = SettingsConfigDict(
        env_file=(_env_file_path, ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
