from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.article import Article
from app.schemas.article import PublishResponse
from app.services.audit_service import log_audit
from app.utils.deps import get_current_user_id, require_active_subscription

router = APIRouter(prefix="/publish", tags=["publish"], dependencies=[Depends(require_active_subscription)])


def _get_article(db: Session, article_id: int, user_id: str) -> Article:
    article = db.query(Article).filter(Article.id == article_id, Article.user_id == user_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="找不到文章")
    return article


@router.post("/website/{article_id}", response_model=PublishResponse)
def publish_to_website(
    article_id: int,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    article = _get_article(db, article_id, user_id)
    article.published_to_website = True
    article.publish_website_result = "模擬發布成功：文章已送往個人網頁 API"
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
    article.published_to_social = True
    article.publish_social_result = "模擬發布成功：文章已送往社交平台 API"
    db.commit()

    log_audit(db, action="publish.social", user_id=user_id, metadata={"article_id": article.id})

    return PublishResponse(
        success=True,
        channel="social",
        message=article.publish_social_result,
        article_id=article.id,
    )
