from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings as app_settings
from app.core.database import get_db
from app.models.article import Article
from app.models.knowledge_file import KnowledgeFile
from app.models.payment import Payment
from app.models.plan import Plan
from app.models.subscription import Subscription
from app.models.user import User
from app.schemas.admin import (
    AdminAccountOut,
    AdminAccountStorageStatusOut,
    AdminRecentPaymentOut,
    AdminRecentUserOut,
    AdminStatsOut,
)
from app.utils.deps import require_admin_access

router = APIRouter(prefix="/admin", tags=["admin"])


def build_account_storage_status(
    *,
    database_url: str,
    persistent_storage_enabled: bool,
    storage_dir: str,
    require_persistent_database: bool,
) -> AdminAccountStorageStatusOut:
    database_backend = "sqlite" if database_url.startswith("sqlite") else "server"
    account_data_safe = persistent_storage_enabled
    warning = None
    if not account_data_safe:
        warning = "目前帳號資料不在持久化資料庫中；網站重新部署或服務重啟後，註冊帳號可能消失。請設定 DATABASE_URL 或 Persistent Disk。"

    return AdminAccountStorageStatusOut(
        database_backend=database_backend,
        persistent_storage_enabled=persistent_storage_enabled,
        require_persistent_database=require_persistent_database,
        account_data_safe=account_data_safe,
        storage_dir=storage_dir,
        warning=warning,
    )


def build_admin_account_rows(
    *,
    users: list[User],
    subscriptions: dict[int, Subscription],
    article_counts: dict[int, int],
    knowledge_counts: dict[int, int],
    payment_counts: dict[int, int],
) -> list[AdminAccountOut]:
    rows: list[AdminAccountOut] = []
    for user in users:
        subscription = subscriptions.get(user.id)
        rows.append(
            AdminAccountOut(
                id=user.id,
                email=user.email,
                created_at=user.created_at,
                updated_at=user.updated_at,
                subscription_status=subscription.status if subscription else "inactive",
                access_tier=subscription.access_tier if subscription else "inactive",
                expires_at=subscription.expires_at if subscription else None,
                article_count=article_counts.get(user.id, 0),
                knowledge_file_count=knowledge_counts.get(user.id, 0),
                payment_count=payment_counts.get(user.id, 0),
            )
        )
    return rows


def _count_by_user(db: Session, model: type, user_ids: list[int]) -> dict[int, int]:
    if not user_ids:
        return {}
    rows = db.query(model.user_id, func.count(model.id)).filter(model.user_id.in_(user_ids)).group_by(model.user_id).all()
    return {int(user_id): int(count) for user_id, count in rows}


@router.get("/account-storage", response_model=AdminAccountStorageStatusOut, dependencies=[Depends(require_admin_access)])
def get_account_storage_status():
    return build_account_storage_status(
        database_url=app_settings.database_url,
        persistent_storage_enabled=app_settings.persistent_storage_enabled,
        storage_dir=str(app_settings.storage_dir),
        require_persistent_database=app_settings.require_persistent_database,
    )


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


@router.get("/accounts", response_model=list[AdminAccountOut], dependencies=[Depends(require_admin_access)])
def list_admin_accounts(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    users = db.query(User).order_by(User.created_at.desc()).limit(limit).all()
    user_ids = [user.id for user in users]
    latest_subscriptions: dict[int, Subscription] = {}
    if user_ids:
        subscriptions = (
            db.query(Subscription)
            .filter(Subscription.user_id.in_(user_ids))
            .order_by(Subscription.updated_at.desc())
            .all()
        )
        for subscription in subscriptions:
            latest_subscriptions.setdefault(subscription.user_id, subscription)

    return build_admin_account_rows(
        users=users,
        subscriptions=latest_subscriptions,
        article_counts=_count_by_user(db, Article, user_ids),
        knowledge_counts=_count_by_user(db, KnowledgeFile, user_ids),
        payment_counts=_count_by_user(db, Payment, user_ids),
    )


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
