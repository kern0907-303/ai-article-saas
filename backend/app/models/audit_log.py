from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class AuditLog(BaseModel):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    action: Mapped[str] = mapped_column(String(120), index=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
