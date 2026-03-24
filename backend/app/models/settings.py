from sqlalchemy import String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class Setting(BaseModel):
    __tablename__ = "settings"
    __table_args__ = (UniqueConstraint("user_id", name="uq_settings_user_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)

    ai_provider: Mapped[str] = mapped_column(String(50), default="openai")

    openai_api_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    anthropic_api_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    gemini_api_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    website_api_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    social_api_key: Mapped[str | None] = mapped_column(String(255), nullable=True)

    openai_api_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    anthropic_api_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    gemini_api_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    website_api_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    social_api_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)

    article_model: Mapped[str] = mapped_column(String(100), default="gpt-4.1-mini")
    prompt_model: Mapped[str] = mapped_column(String(100), default="gpt-4.1-mini")
    image_model: Mapped[str] = mapped_column(String(100), default="gpt-image-1")

    website_endpoint: Mapped[str | None] = mapped_column(String(500), nullable=True)
    social_endpoint: Mapped[str | None] = mapped_column(String(500), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
