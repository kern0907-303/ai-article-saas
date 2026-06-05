import os
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_runtime_root() -> Path:
    render_disk_path = os.getenv("RENDER_DISK_PATH", "").strip()
    if render_disk_path:
        return Path(render_disk_path) / "ai-article-saas"

    return Path(".")


def _default_database_url() -> str:
    configured = os.getenv("DATABASE_URL", "").strip()
    if configured:
        if configured.startswith("postgres://"):
            return configured.replace("postgres://", "postgresql://", 1)
        return configured

    runtime_root = _default_runtime_root()
    return f"sqlite:///{(runtime_root / 'app.db').resolve()}"


def _default_storage_dir() -> Path:
    configured = os.getenv("STORAGE_DIR", "").strip()
    if configured:
        return Path(configured)
    return _default_runtime_root() / "storage"


class AppSettings(BaseSettings):
    app_name: str = "AI 文章生成與自動發布 SaaS API"
    api_prefix: str = "/api"
    database_url: str = _default_database_url()
    storage_dir: Path = _default_storage_dir()
    cors_origins: str = "*"

    jwt_secret_key: str = "change-this-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24

    encryption_secret: str = "replace-with-32-byte-base64-key"

    expose_reset_token_in_response: bool = True
    auth_enabled: bool = False
    admin_api_key: str = "change-admin-key-in-production"
    require_persistent_database: bool = False

    pcloud_auth_token: str | None = None
    pcloud_api_host: str = "api.pcloud.com"
    pcloud_folder_id: int | None = None
    pcloud_folder_path: str | None = None
    pcloud_create_public_link: bool = True
    pcloud_use_direct_download_link: bool = True
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            return _default_database_url()
        if isinstance(value, str) and value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql://", 1)
        return value

    @property
    def persistent_storage_enabled(self) -> bool:
        if not self.database_url.startswith("sqlite"):
            return True
        return bool(os.getenv("RENDER_DISK_PATH", "").strip())

    @property
    def database_backend_label(self) -> str:
        return "sqlite" if self.database_url.startswith("sqlite") else "server"


settings = AppSettings()
