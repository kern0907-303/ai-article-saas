from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.article import Article
from app.models.knowledge_file import KnowledgeFile
from app.models.payment import Payment
from app.models.plan import Plan
from app.models.subscription import Subscription
from app.models.user import User
from app.schemas.admin import AdminRecentPaymentOut, AdminRecentUserOut, AdminStatsOut
from app.utils.deps import require_admin_access

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/stats", response_model=AdminStatsOut, dependencies=[Depends(require_admin_access)])
def get_admin_stats(db: Session = Depends(get_db)):
    now = datetime.utcnow()
    since_7d = now - timedelta(days=7)

    total_users = db.query(func.count(User.id)).scalar() or 0
    new_users_7d = db.query(func.count(User.id)).filter(User.created_at >= since_7d).scalar() or 0

    active_paid_users = (
        db.query(func.count(func.distinct(Subscription.user_id)))
        .filter(
            Subscription.status == "active",
            Subscription.access_tier == "paid",
            Subscription.expires_at.is_not(None),
            Subscription.expires_at > now,
        )
        .scalar()
        or 0
    )
    active_trial_users = (
        db.query(func.count(func.distinct(Subscription.user_id)))
        .filter(
            Subscription.status == "active",
            Subscription.access_tier == "trial",
            Subscription.expires_at.is_not(None),
            Subscription.expires_at > now,
        )
        .scalar()
        or 0
    )

    total_paid_users = (
        db.query(func.count(func.distinct(Subscription.user_id)))
        .filter(Subscription.access_tier == "paid")
        .scalar()
        or 0
    )

    total_articles = db.query(func.count(Article.id)).scalar() or 0
    articles_7d = db.query(func.count(Article.id)).filter(Article.created_at >= since_7d).scalar() or 0

    total_knowledge_files = db.query(func.count(KnowledgeFile.id)).scalar() or 0

    total_payments = db.query(func.count(Payment.id)).scalar() or 0
    paid_payments = db.query(func.count(Payment.id)).filter(Payment.status == "paid").scalar() or 0
    paid_revenue_cents = db.query(func.coalesce(func.sum(Payment.amount_cents), 0)).filter(Payment.status == "paid").scalar() or 0

    return AdminStatsOut(
        total_users=int(total_users),
        new_users_7d=int(new_users_7d),
        total_paid_users=int(total_paid_users),
        active_paid_users=int(active_paid_users),
        active_trial_users=int(active_trial_users),
        total_articles=int(total_articles),
        articles_7d=int(articles_7d),
        total_knowledge_files=int(total_knowledge_files),
        total_payments=int(total_payments),
        paid_payments=int(paid_payments),
        paid_revenue_cents=int(paid_revenue_cents),
        paid_revenue_twd=round(float(paid_revenue_cents) / 100.0, 2),
    )


@router.get("/recent-users", response_model=list[AdminRecentUserOut], dependencies=[Depends(require_admin_access)])
def list_recent_users(
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    rows = db.query(User).order_by(User.created_at.desc()).limit(limit).all()
    return [AdminRecentUserOut(id=row.id, email=row.email, created_at=row.created_at) for row in rows]


@router.get("/recent-payments", response_model=list[AdminRecentPaymentOut], dependencies=[Depends(require_admin_access)])
def list_recent_payments(
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(Payment, User, Plan)
        .outerjoin(User, User.id == Payment.user_id)
        .outerjoin(Plan, Plan.id == Payment.plan_id)
        .order_by(Payment.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        AdminRecentPaymentOut(
            payment_id=payment.id,
            user_id=payment.user_id,
            user_email=user.email if user else None,
            plan_code=plan.code if plan else None,
            amount_cents=payment.amount_cents,
            currency=payment.currency,
            provider=payment.provider,
            status=payment.status,
            created_at=payment.created_at,
        )
        for payment, user, plan in rows
    ]
