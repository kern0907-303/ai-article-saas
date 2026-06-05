from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class ArticleImage(BaseModel):
    __tablename__ = "article_images"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    article_id: Mapped[int] = mapped_column(Integer, index=True)

    provider: Mapped[str] = mapped_column(String(32))
    model: Mapped[str] = mapped_column(String(100))
    style_preset: Mapped[str] = mapped_column(String(50), default="blog_cover")

    prompt: Mapped[str] = mapped_column(Text)
    image_url: Mapped[str] = mapped_column(Text)
    width: Mapped[int] = mapped_column(Integer, default=1536)
    height: Mapped[int] = mapped_column(Integer, default=1024)

    text_language: Mapped[str | None] = mapped_column(String(20), nullable=True)
    text_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    generation_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="generated")
