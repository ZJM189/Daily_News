from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str = "postgresql+psycopg://daily_news:change-me@localhost:5432/daily_news"
    redis_url: str = "redis://localhost:6379/0"
    session_secret: str = "change-me-session-secret"
    csrf_secret: str = "change-me-csrf-secret"
    encryption_key: str = "change-me-32-byte-key"
    default_timezone: str = "Asia/Shanghai"
    digest_cron: str = "0 8 * * *"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def debug(self) -> bool:
        return self.app_env == "development"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
