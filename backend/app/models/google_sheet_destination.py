from sqlalchemy import Boolean, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class GoogleSheetDestination(BaseModel):
    __tablename__ = "google_sheet_destinations"
    __table_args__ = (
        UniqueConstraint("user_id", "label", name="uq_google_sheet_destinations_user_label"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    label: Mapped[str] = mapped_column(String(120))
    spreadsheet_id: Mapped[str] = mapped_column(String(255), index=True)
    sheet_name: Mapped[str] = mapped_column(String(120), default="文章準備")
    service_account_email: Mapped[str] = mapped_column(String(255))
    service_account_json_encrypted: Mapped[str] = mapped_column(Text)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
