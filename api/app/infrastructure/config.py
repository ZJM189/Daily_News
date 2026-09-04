from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    app_domain: str = "localhost"
    cors_allowed_origins: str = ""
    database_url: str = "postgresql+psycopg://daily_news:change-me@localhost:5432/daily_news"
    redis_url: str = "redis://localhost:6379/0"
    session_secret: str = "change-me-session-secret"
    session_cookie_name: str = "daily_news_session"
    session_cookie_secure: bool | None = None
    session_cookie_samesite: str = "lax"
    session_ttl_hours: int = 168
    csrf_secret: str = "change-me-csrf-secret"
    encryption_key: str = "change-me-32-byte-key"
    default_timezone: str = "Asia/Shanghai"
    digest_cron: str = "0 8 * * *"
    worker_poll_interval_seconds: int = 5

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def debug(self) -> bool:
        return self.app_env == "development"

    @property
    def cookie_secure(self) -> bool:
        if self.session_cookie_secure is not None:
            return self.session_cookie_secure
        return not self.debug

    @property
    def cors_origins(self) -> list[str]:
        configured_origins = [
            origin.strip()
            for origin in self.cors_allowed_origins.split(",")
            if origin.strip()
        ]
        if configured_origins:
            return configured_origins
        if self.debug or self.app_domain in {"localhost", "127.0.0.1"}:
            return []
        return [f"https://{self.app_domain}"]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
