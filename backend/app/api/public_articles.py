from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.article import Article
from app.schemas.article import PublicArticleOut

router = APIRouter(prefix="/public/articles", tags=["public-articles"])


@router.get("", response_model=list[PublicArticleOut])
def list_public_articles(
    owner_id: str = Query(min_length=1, max_length=64),
    workspace_id: int | None = None,
    db: Session = Depends(get_db),
):
    query = (
        db.query(Article)
        .filter(
            Article.user_id == owner_id,
            Article.published_to_website.is_(True),
            Article.content.isnot(None),
        )
        .order_by(Article.updated_at.desc(), Article.id.desc())
    )
    if workspace_id is not None:
        query = query.filter(Article.workspace_id == workspace_id)
    return [PublicArticleOut.model_validate(article) for article in query.all()]
