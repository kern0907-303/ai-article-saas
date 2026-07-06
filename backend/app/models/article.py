from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class Article(BaseModel):
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    workspace_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    topic: Mapped[str] = mapped_column(String(255), index=True)
    outline: Mapped[str] = mapped_column(Text)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    generation_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    selected_file_ids: Mapped[str | None] = mapped_column(String(255), nullable=True)
    knowledge_categories: Mapped[str | None] = mapped_column(String(500), nullable=True)
    generation_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    generation_status: Mapped[str] = mapped_column(String(50), default="draft")
    published_to_website: Mapped[bool] = mapped_column(Boolean, default=False)
    published_to_social: Mapped[bool] = mapped_column(Boolean, default=False)
    publish_website_result: Mapped[str | None] = mapped_column(Text, nullable=True)
    publish_social_result: Mapped[str | None] = mapped_column(Text, nullable=True)
