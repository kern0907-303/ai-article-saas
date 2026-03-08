from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    app_name: str = "AI 文章生成與自動發布 SaaS API"
    api_prefix: str = "/api"
    database_url: str = "sqlite:///./app.db"
    storage_dir: Path = Path("storage")
    cors_origins: str = "*"

    jwt_secret_key: str = "change-this-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24

    encryption_secret: str = "replace-with-32-byte-base64-key"

    expose_reset_token_in_response: bool = True
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)


settings = AppSettings()
