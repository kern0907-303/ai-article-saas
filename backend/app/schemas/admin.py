from datetime import datetime

from pydantic import BaseModel


class AdminStatsOut(BaseModel):
    total_users: int
    new_users_7d: int
    total_paid_users: int
    active_paid_users: int
    active_trial_users: int
    total_articles: int
    articles_7d: int
    total_knowledge_files: int
    total_payments: int
    paid_payments: int
    paid_revenue_cents: int
    paid_revenue_twd: float


class AdminRecentUserOut(BaseModel):
    id: int
    email: str
    created_at: datetime


class AdminRecentPaymentOut(BaseModel):
    payment_id: int
    user_id: int
    user_email: str | None = None
    plan_code: str | None = None
    amount_cents: int
    currency: str
    provider: str
    status: str
    created_at: datetime
