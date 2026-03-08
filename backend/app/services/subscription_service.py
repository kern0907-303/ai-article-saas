from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.plan import Plan
from app.models.subscription import Subscription


def normalize_utc_naive(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def get_active_subscription(db: Session, user_id: int) -> Subscription | None:
    now = datetime.utcnow()
    sub = (
        db.query(Subscription)
        .filter(Subscription.user_id == user_id)
        .order_by(Subscription.updated_at.desc())
        .first()
    )
    if not sub:
        return None
    expires_at = normalize_utc_naive(sub.expires_at)
    if sub.status != "active" or not expires_at or expires_at <= now:
        return None
    if (sub.access_tier or "inactive") not in {"paid", "trial"}:
        return None
    return sub


def get_subscription_with_plan(db: Session, user_id: int) -> tuple[Subscription | None, Plan | None]:
    sub = (
        db.query(Subscription)
        .filter(Subscription.user_id == user_id)
        .order_by(Subscription.updated_at.desc())
        .first()
    )
    if not sub:
        return None, None
    plan = db.query(Plan).filter(Plan.id == sub.plan_id).first()
    return sub, plan


def activate_subscription_one_year(db: Session, user_id: int, plan: Plan) -> Subscription:
    now = datetime.utcnow()
    sub = (
        db.query(Subscription)
        .filter(Subscription.user_id == user_id)
        .order_by(Subscription.updated_at.desc())
        .first()
    )
    if not sub:
        sub = Subscription(
            user_id=user_id,
            plan_id=plan.id,
            status="active",
            access_tier="paid",
            started_at=now,
            expires_at=now + timedelta(days=plan.duration_days),
        )
        db.add(sub)
    else:
        expires_at = normalize_utc_naive(sub.expires_at)
        base = expires_at if expires_at and expires_at > now else now
        sub.plan_id = plan.id
        sub.status = "active"
        sub.access_tier = "paid"
        if not sub.started_at:
            sub.started_at = now
        sub.expires_at = base + timedelta(days=plan.duration_days)
        sub.trial_used = 1

    db.commit()
    db.refresh(sub)
    return sub


def start_trial_subscription(db: Session, user_id: int, trial_plan: Plan) -> Subscription:
    now = datetime.utcnow()
    sub = (
        db.query(Subscription)
        .filter(Subscription.user_id == user_id)
        .order_by(Subscription.updated_at.desc())
        .first()
    )
    if not sub:
        sub = Subscription(
            user_id=user_id,
            plan_id=trial_plan.id,
            status="active",
            access_tier="trial",
            trial_used=1,
            started_at=now,
            expires_at=now + timedelta(days=trial_plan.duration_days),
        )
        db.add(sub)
    else:
        sub.plan_id = trial_plan.id
        sub.status = "active"
        sub.access_tier = "trial"
        sub.trial_used = 1
        sub.started_at = now
        sub.expires_at = now + timedelta(days=trial_plan.duration_days)

    db.commit()
    db.refresh(sub)
    return sub
