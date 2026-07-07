from app.core.config import AppSettings


def test_postgresql_url_uses_installed_psycopg_driver():
    settings = AppSettings(database_url="postgresql://user:pass@example.com:5432/app")

    assert settings.database_url == "postgresql+psycopg://user:pass@example.com:5432/app"


def test_legacy_postgres_url_uses_installed_psycopg_driver():
    settings = AppSettings(database_url="postgres://user:pass@example.com:5432/app")

    assert settings.database_url == "postgresql+psycopg://user:pass@example.com:5432/app"


def test_explicit_postgresql_driver_is_preserved():
    settings = AppSettings(database_url="postgresql+psycopg://user:pass@example.com:5432/app")

    assert settings.database_url == "postgresql+psycopg://user:pass@example.com:5432/app"
