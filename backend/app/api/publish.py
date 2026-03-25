import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.article import Article
from app.models.settings import Setting
from app.schemas.article import PublishResponse
from app.services.audit_service import log_audit
from app.services.crypto_service import decrypt_text
from app.utils.deps import get_current_user_id, require_active_subscription

router = APIRouter(prefix="/publish", tags=["publish"], dependencies=[Depends(require_active_subscription)])
PUBLISH_TIMEOUT = httpx.Timeout(connect=10.0, read=20.0, write=20.0, pool=10.0)


def _get_article(db: Session, article_id: int, user_id: str) -> Article:
    article = db.query(Article).filter(Article.id == article_id, Article.user_id == user_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="找不到文章")
    return article


def _get_user_settings(db: Session, user_id: str) -> Setting:
    setting = db.query(Setting).filter(Setting.user_id == user_id).first()
    if not setting:
        raise HTTPException(status_code=400, detail="尚未完成系統設定，請先到設定頁填入發布 API 資訊")
    return setting


def _require_publish_config(setting: Setting, channel: str) -> tuple[str, str]:
    if channel == "website":
        endpoint = (setting.website_endpoint or "").strip()
        api_key = (decrypt_text(setting.website_api_key_encrypted) or setting.website_api_key or "").strip()
        label = "個人網頁"
    else:
        endpoint = (setting.social_endpoint or "").strip()
        api_key = (decrypt_text(setting.social_api_key_encrypted) or setting.social_api_key or "").strip()
        label = "社交平台"

    if not endpoint:
        raise HTTPException(status_code=400, detail=f"尚未設定{label} Endpoint，請先到設定頁完成設定")
    if not api_key:
        raise HTTPException(status_code=400, detail=f"尚未設定{label} API Key，請先到設定頁完成設定")

    return endpoint, api_key


def _send_publish_request(endpoint: str, api_key: str, article: Article, channel: str) -> str:
    payload = {
        "article_id": article.id,
        "topic": article.topic,
        "outline": article.outline,
        "content": article.content,
        "channel": channel,
    }

    try:
        response = httpx.post(
            endpoint,
            json=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=PUBLISH_TIMEOUT,
        )
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="發布請求逾時，請檢查對方 API 是否正常運作") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="無法連線到發布 API，請檢查 Endpoint 是否正確") from exc

    if response.is_error:
        detail = response.text.strip() or f"HTTP {response.status_code}"
        raise HTTPException(status_code=502, detail=f"發布 API 回應失敗：{detail}")

    return response.text.strip() or "發布成功"


@router.post("/website/{article_id}", response_model=PublishResponse)
def publish_to_website(
    article_id: int,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    article = _get_article(db, article_id, user_id)
    setting = _get_user_settings(db, user_id)
    endpoint, api_key = _require_publish_config(setting, "website")
    publish_result = _send_publish_request(endpoint, api_key, article, "website")
    article.published_to_website = True
    article.publish_website_result = publish_result
    db.commit()

    log_audit(db, action="publish.website", user_id=user_id, metadata={"article_id": article.id})

    return PublishResponse(
        success=True,
        channel="website",
        message=article.publish_website_result,
        article_id=article.id,
    )


@router.post("/social/{article_id}", response_model=PublishResponse)
def publish_to_social(
    article_id: int,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    article = _get_article(db, article_id, user_id)
    setting = _get_user_settings(db, user_id)
    endpoint, api_key = _require_publish_config(setting, "social")
    publish_result = _send_publish_request(endpoint, api_key, article, "social")
    article.published_to_social = True
    article.publish_social_result = publish_result
    db.commit()

    log_audit(db, action="publish.social", user_id=user_id, metadata={"article_id": article.id})

    return PublishResponse(
        success=True,
        channel="social",
        message=article.publish_social_result,
        article_id=article.id,
    )
