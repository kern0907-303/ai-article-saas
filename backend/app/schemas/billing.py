from datetime import datetime

from pydantic import BaseModel


class PlanOut(BaseModel):
    id: int
    code: str
    name: str
    description: str | None
    duration_days: int
    price_cents: int
    currency: str
    is_trial: int

    model_config = {"from_attributes": True}


class SubscriptionOut(BaseModel):
    status: str
    access_tier: str = "inactive"
    plan_code: str | None
    started_at: datetime | None
    expires_at: datetime | None
    is_active: bool
    trial_used: bool = False


class CreateCheckoutRequest(BaseModel):
    plan_code: str
    provider: str = "mockpay"


class CreateCheckoutResponse(BaseModel):
    payment_id: int
    txn_id: str
    amount_cents: int
    currency: str
    provider: str
    status: str


class PaymentWebhookRequest(BaseModel):
    txn_id: str
    status: str


class PaymentWebhookResponse(BaseModel):
    success: bool
    message: str


class TrialStartResponse(BaseModel):
    success: bool
    message: str
    expires_at: datetime


class EntitlementsOut(BaseModel):
    status: str
    access_tier: str
    plan_code: str | None
    started_at: datetime | None
    expires_at: datetime | None
    is_active: bool
    trial_used: bool
    limits: dict
    usage: dict
    remaining: dict
