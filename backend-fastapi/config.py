from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+psycopg://pulse_user:pulse_password@localhost:5432/engagement_pulse_fastapi"
    JWT_SECRET_KEY: str | None = None
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Development-only seed credentials (read from environment/.env, never hardcoded)
    SEED_CONSULTANT_PASSWORD: str | None = None
    SEED_CLIENT_VIEWER_PASSWORD: str | None = None
    SEED_PASSWORD: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
