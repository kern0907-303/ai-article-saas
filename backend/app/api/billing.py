from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.payment import Payment
from app.models.plan import Plan
from app.models.subscription import Subscription
from app.models.user import User
from app.schemas.billing import (
    CreateCheckoutRequest,
    CreateCheckoutResponse,
    EntitlementsOut,
    PaymentWebhookRequest,
    PaymentWebhookResponse,
    PlanOut,
    SubscriptionOut,
    TrialStartResponse,
)
from app.services.audit_service import log_audit
from app.services.entitlement_service import get_entitlements
from app.services.subscription_service import (
    activate_subscription_one_year,
    get_subscription_with_plan,
    normalize_utc_naive,
    start_trial_subscription,
)
from app.utils.deps import get_current_user

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/plans", response_model=list[PlanOut])
def list_plans(db: Session = Depends(get_db)):
    return db.query(Plan).filter(Plan.is_active == 1).order_by(Plan.price_cents.asc()).all()


@router.get("/subscription", response_model=SubscriptionOut)
def get_my_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sub, plan = get_subscription_with_plan(db, current_user.id)
    if not sub:
        return SubscriptionOut(
            status="inactive",
            access_tier="inactive",
            plan_code=None,
            started_at=None,
            expires_at=None,
            is_active=False,
            trial_used=False,
        )

    expires_at = normalize_utc_naive(sub.expires_at)
    is_active = bool(
        sub.status == "active"
        and (sub.access_tier or "inactive") in {"paid", "trial"}
        and expires_at
        and expires_at > datetime.utcnow()
    )
    return SubscriptionOut(
        status=sub.status,
        access_tier=sub.access_tier or "inactive",
        plan_code=plan.code if plan else None,
        started_at=sub.started_at,
        expires_at=sub.expires_at,
        is_active=is_active,
        trial_used=bool(sub.trial_used),
    )


@router.get("/entitlements", response_model=EntitlementsOut)
def get_my_entitlements(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return EntitlementsOut(**get_entitlements(db, current_user.id))


@router.post("/trial/start", response_model=TrialStartResponse)
def start_trial(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sub, _ = get_subscription_with_plan(db, current_user.id)
    now = datetime.utcnow()
    if sub and bool(sub.trial_used):
        raise HTTPException(status_code=400, detail="此帳號已使用過試用資格")

    if sub and sub.status == "active" and (sub.access_tier or "inactive") == "paid":
        expires_at = normalize_utc_naive(sub.expires_at)
        if expires_at and expires_at > now:
            raise HTTPException(status_code=400, detail="目前已是付費方案，無需啟用試用")

    trial_plan = db.query(Plan).filter(Plan.code == "trial-7d", Plan.is_active == 1).first()
    if not trial_plan:
        raise HTTPException(status_code=500, detail="試用方案尚未設定，請聯絡管理員")

    trial_sub = start_trial_subscription(db, current_user.id, trial_plan)
    log_audit(
        db,
        action="billing.trial_started",
        user_id=str(current_user.id),
        metadata={"expires_at": str(trial_sub.expires_at)},
    )
    return TrialStartResponse(success=True, message="已啟用 7 天試用", expires_at=trial_sub.expires_at)


@router.post("/checkout", response_model=CreateCheckoutResponse)
def create_checkout(
    payload: CreateCheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plan = db.query(Plan).filter(Plan.code == payload.plan_code, Plan.is_active == 1).first()
    if not plan:
        raise HTTPException(status_code=404, detail="找不到方案")
    if plan.is_trial:
        raise HTTPException(status_code=400, detail="試用方案不可建立付款單")

    payment = Payment(
        user_id=current_user.id,
        plan_id=plan.id,
        provider=payload.provider,
        txn_id=f"txn_{uuid4().hex}",
        amount_cents=plan.price_cents,
        currency=plan.currency,
        status="pending",
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)

    log_audit(
        db,
        action="billing.checkout_created",
        user_id=str(current_user.id),
        metadata={"txn_id": payment.txn_id, "plan_code": plan.code, "provider": payload.provider},
    )

    return CreateCheckoutResponse(
        payment_id=payment.id,
        txn_id=payment.txn_id,
        amount_cents=payment.amount_cents,
        currency=payment.currency,
        provider=payment.provider,
        status=payment.status,
    )


@router.post("/webhook/payment", response_model=PaymentWebhookResponse)
def payment_webhook(payload: PaymentWebhookRequest, db: Session = Depends(get_db)):
    payment = db.query(Payment).filter(Payment.txn_id == payload.txn_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="交易不存在")

    payment.status = payload.status
    db.commit()
    db.refresh(payment)

    if payload.status == "paid":
        plan = db.query(Plan).filter(Plan.id == payment.plan_id).first()
        if not plan:
            raise HTTPException(status_code=400, detail="交易對應方案不存在")

        sub = activate_subscription_one_year(db, payment.user_id, plan)
        log_audit(
            db,
            action="billing.payment_paid",
            user_id=str(payment.user_id),
            metadata={"txn_id": payment.txn_id, "plan_code": plan.code, "expires_at": str(sub.expires_at)},
        )
        return PaymentWebhookResponse(success=True, message="付款成功，已開通一年權限")

    log_audit(
        db,
        action="billing.payment_update",
        user_id=str(payment.user_id),
        metadata={"txn_id": payment.txn_id, "status": payload.status},
    )
    return PaymentWebhookResponse(success=True, message=f"付款狀態已更新為 {payload.status}")
