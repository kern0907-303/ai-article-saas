from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class Payment(BaseModel):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id"), index=True)

    provider: Mapped[str] = mapped_column(String(30), default="mockpay")
    txn_id: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    amount_cents: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(10), default="TWD")
    status: Mapped[str] = mapped_column(String(30), default="pending")
