from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_ENV: str = "development"
    JWT_SECRET: str = "dev-secret-change-in-production"
    JWT_EXPIRE_HOURS: int = 24
    FERNET_KEY: str = ""

    DATABASE_URL: str = "postgresql+asyncpg://user:pass@localhost:5432/sparkguard"

    FRONTEND_URL: str = "http://localhost:5573"

    PLAYWRIGHT_HEADLESS: bool = False

    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = ""

    RATE_LIMIT_ENABLED: bool = True
    TIMEZONE: str = "Asia/Shanghai"

    DEV_BYPASS_AUTH: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
