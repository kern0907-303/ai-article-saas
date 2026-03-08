from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class UsageCounter(BaseModel):
    __tablename__ = "usage_counters"
    __table_args__ = (UniqueConstraint("user_id", "usage_date", name="uq_usage_user_date"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    usage_date: Mapped[str] = mapped_column(String(10), index=True)  # YYYY-MM-DD

    article_generate_count: Mapped[int] = mapped_column(Integer, default=0)
    prompt_expand_count: Mapped[int] = mapped_column(Integer, default=0)
    image_generate_count: Mapped[int] = mapped_column(Integer, default=0)
