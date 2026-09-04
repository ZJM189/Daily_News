from app.infrastructure.config import Settings


def test_development_has_no_default_cors_origin() -> None:
    settings = Settings(_env_file=None, app_env="development", app_domain="localhost")

    assert settings.debug is True
    assert settings.cookie_secure is False
    assert settings.cors_origins == []


def test_production_domain_is_used_as_default_cors_origin() -> None:
    settings = Settings(_env_file=None, app_env="production", app_domain="news.example.com")

    assert settings.debug is False
    assert settings.cookie_secure is True
    assert settings.cors_origins == ["https://news.example.com"]


def test_explicit_cors_origins_take_precedence() -> None:
    settings = Settings(
        _env_file=None,
        app_env="production",
        app_domain="news.example.com",
        cors_allowed_origins="https://web.example.com, https://admin.example.com",
    )

    assert settings.cors_origins == ["https://web.example.com", "https://admin.example.com"]
