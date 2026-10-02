from app.infrastructure.config import Settings, get_settings
from app.infrastructure.typesafe_jev.client import JevClientConfig, TypeSafeJevClient


def create_jev_client(settings: Settings | None = None) -> TypeSafeJevClient | None:
    configured = settings or get_settings()
    if not configured.jev_enabled or not configured.jev_api_key:
        return None
    return TypeSafeJevClient(
        JevClientConfig(
            base_url=configured.jev_base_url,
            api_key=configured.jev_api_key,
            model=configured.jev_model,
            timeout_seconds=configured.jev_timeout_seconds,
            retry_count=configured.jev_retry_count,
        )
    )
