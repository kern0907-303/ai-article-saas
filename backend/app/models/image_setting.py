from sqlalchemy import Boolean, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class ImageSetting(BaseModel):
    __tablename__ = "image_settings"
    __table_args__ = (UniqueConstraint("user_id", name="uq_image_settings_user_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)

    image_provider_mode: Mapped[str] = mapped_column(String(32), default="auto")
    default_provider: Mapped[str] = mapped_column(String(32), default="openai")
    force_nano_banana_for_zh_text: Mapped[bool] = mapped_column(Boolean, default=True)

    nano_banana_model: Mapped[str] = mapped_column(String(100), default="nano-banana-v1")
    openai_image_model: Mapped[str] = mapped_column(String(100), default="gpt-image-1")

    default_size: Mapped[str] = mapped_column(String(32), default="1536x1024")
    default_quality: Mapped[str] = mapped_column(String(32), default="high")
    output_format: Mapped[str] = mapped_column(String(16), default="png")
    images_per_article: Mapped[int] = mapped_column(Integer, default=1)

    zh_text_detection_keywords: Mapped[str] = mapped_column(
        Text,
        default="中文,繁體,標語,文案,海報,banner,封面文字,字卡",
    )
