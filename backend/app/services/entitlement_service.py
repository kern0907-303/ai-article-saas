from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings as app_settings
from app.models.knowledge_file import KnowledgeFile
from app.models.plan import Plan
from app.models.subscription import Subscription
from app.models.usage_counter import UsageCounter
from app.services.subscription_service import normalize_utc_naive

TRIAL_LIMITS = {
    "article_generate": 5,
    "prompt_expand": 20,
    "image_generate": 10,
    "knowledge_total_bytes": 50 * 1024 * 1024,
}


def _today_key() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d")


def _find_latest_subscription(db: Session, user_id: int) -> tuple[Subscription | None, Plan | None]:
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


def _is_subscription_active(sub: Subscription | None) -> bool:
    if not sub:
        return False
    expires_at = normalize_utc_naive(sub.expires_at)
    return bool(sub.status == "active" and expires_at and expires_at > datetime.utcnow())


def get_entitlements(db: Session, user_id: int) -> dict:
    if not app_settings.auth_enabled:
        return {
            "status": "active",
            "access_tier": "paid",
            "plan_code": "auth-disabled",
            "started_at": None,
            "expires_at": None,
            "is_active": True,
            "trial_used": False,
            "limits": {
                "article_generate_per_day": -1,
                "prompt_expand_per_day": -1,
                "image_generate_per_day": -1,
                "knowledge_total_bytes": -1,
            },
            "usage": {
                "article_generate_today": 0,
                "prompt_expand_today": 0,
                "image_generate_today": 0,
                "knowledge_total_bytes": 0,
            },
            "remaining": {
                "article_generate_today": -1,
                "prompt_expand_today": -1,
                "image_generate_today": -1,
                "knowledge_total_bytes": -1,
            },
        }

    sub, plan = _find_latest_subscription(db, user_id)
    active = _is_subscription_active(sub)
    tier = sub.access_tier if sub and sub.access_tier else "inactive"
    if tier == "inactive" and active:
        tier = "paid"

    usage_date = _today_key()
    usage = (
        db.query(UsageCounter)
        .filter(UsageCounter.user_id == user_id, UsageCounter.usage_date == usage_date)
        .first()
    )
    article_used = usage.article_generate_count if usage else 0
    prompt_used = usage.prompt_expand_count if usage else 0
    image_used = usage.image_generate_count if usage else 0

    total_knowledge_size = (
        db.query(func.coalesce(func.sum(KnowledgeFile.file_size), 0))
        .filter(KnowledgeFile.user_id == str(user_id), KnowledgeFile.is_active.is_(True))
        .scalar()
    )
    total_knowledge_size = int(total_knowledge_size or 0)

    is_trial_active = bool(tier == "trial" and active)
    is_paid_active = bool(tier == "paid" and active)

    if is_paid_active:
        article_remaining = -1
        prompt_remaining = -1
        image_remaining = -1
        knowledge_remaining = -1
    elif is_trial_active:
        article_remaining = max(0, TRIAL_LIMITS["article_generate"] - article_used)
        prompt_remaining = max(0, TRIAL_LIMITS["prompt_expand"] - prompt_used)
        image_remaining = max(0, TRIAL_LIMITS["image_generate"] - image_used)
        knowledge_remaining = max(0, TRIAL_LIMITS["knowledge_total_bytes"] - total_knowledge_size)
    else:
        article_remaining = 0
        prompt_remaining = 0
        image_remaining = 0
        knowledge_remaining = 0

    return {
        "status": sub.status if sub else "inactive",
        "access_tier": "paid" if is_paid_active else ("trial" if is_trial_active else "inactive"),
        "plan_code": plan.code if plan else None,
        "started_at": sub.started_at if sub else None,
        "expires_at": sub.expires_at if sub else None,
        "is_active": bool(is_paid_active or is_trial_active),
        "trial_used": bool(sub.trial_used) if sub else False,
        "limits": {
            "article_generate_per_day": TRIAL_LIMITS["article_generate"],
            "prompt_expand_per_day": TRIAL_LIMITS["prompt_expand"],
            "image_generate_per_day": TRIAL_LIMITS["image_generate"],
            "knowledge_total_bytes": TRIAL_LIMITS["knowledge_total_bytes"],
        },
        "usage": {
            "article_generate_today": article_used,
            "prompt_expand_today": prompt_used,
            "image_generate_today": image_used,
            "knowledge_total_bytes": total_knowledge_size,
        },
        "remaining": {
            "article_generate_today": article_remaining,
            "prompt_expand_today": prompt_remaining,
            "image_generate_today": image_remaining,
            "knowledge_total_bytes": knowledge_remaining,
        },
    }


def _get_or_create_usage_counter(db: Session, user_id: int, usage_date: str) -> UsageCounter:
    usage = (
        db.query(UsageCounter)
        .filter(UsageCounter.user_id == user_id, UsageCounter.usage_date == usage_date)
        .first()
    )
    if usage:
        return usage
    usage = UsageCounter(user_id=user_id, usage_date=usage_date)
    db.add(usage)
    db.flush()
    return usage


def require_feature_access(db: Session, user_id: int, feature: str, amount: int = 1, extra_bytes: int = 0) -> None:
    ent = get_entitlements(db, user_id)
    if not ent["is_active"]:
        raise HTTPException(status_code=402, detail="目前未開通方案，可先啟用 7 天試用或升級年繳")

    if ent["access_tier"] != "trial":
        return

    if feature == "article_generate" and ent["remaining"]["article_generate_today"] < amount:
        raise HTTPException(status_code=429, detail="試用額度不足：今日文章生成次數已用完")
    if feature == "prompt_expand" and ent["remaining"]["prompt_expand_today"] < amount:
        raise HTTPException(status_code=429, detail="試用額度不足：今日提示詞擴寫次數已用完")
    if feature == "image_generate" and ent["remaining"]["image_generate_today"] < amount:
        raise HTTPException(status_code=429, detail="試用額度不足：今日圖片生成張數已達上限")
    if feature == "knowledge_upload" and ent["remaining"]["knowledge_total_bytes"] < extra_bytes:
        raise HTTPException(status_code=429, detail="試用額度不足：知識庫總容量已達上限 50MB")


def consume_feature_usage(db: Session, user_id: int, feature: str, amount: int = 1) -> None:
    ent = get_entitlements(db, user_id)
    if ent["access_tier"] != "trial":
        return

    usage = _get_or_create_usage_counter(db, user_id, _today_key())
    if feature == "article_generate":
        usage.article_generate_count += amount
    elif feature == "prompt_expand":
        usage.prompt_expand_count += amount
    elif feature == "image_generate":
        usage.image_generate_count += amount
    db.commit()
