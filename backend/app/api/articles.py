from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.article import Article
from app.models.knowledge_file import KnowledgeFile
from app.models.settings import Setting
from app.schemas.article import (
    ArticleGenerateRequest,
    ArticleOut,
    ArticleUpdateRequest,
    PromptExpandRequest,
    PromptExpandResponse,
)
from app.services.ai_service import expand_prompt as expand_prompt_with_provider
from app.services.ai_service import generate_article as generate_article_with_provider
from app.services.audit_service import log_audit
from app.services.entitlement_service import consume_feature_usage, require_feature_access
from app.services.file_service import extract_text_from_file
from app.services.rate_limit_service import check_rate_limit
from app.services.crypto_service import decrypt_text
from app.utils.deps import get_current_user_id, require_active_subscription

router = APIRouter(prefix="/articles", tags=["articles"], dependencies=[Depends(require_active_subscription)])


def _hydrate_provider_keys(setting: Setting) -> Setting:
    setting.openai_api_key = decrypt_text(setting.openai_api_key_encrypted) or setting.openai_api_key
    setting.anthropic_api_key = decrypt_text(setting.anthropic_api_key_encrypted) or setting.anthropic_api_key
    setting.gemini_api_key = decrypt_text(setting.gemini_api_key_encrypted) or setting.gemini_api_key
    return setting


@router.get("", response_model=list[ArticleOut])
def list_articles(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    return (
        db.query(Article)
        .filter(Article.user_id == user_id)
        .order_by(Article.created_at.desc())
        .all()
    )


@router.post("/prompt-expand", response_model=PromptExpandResponse)
def expand_prompt(
    payload: PromptExpandRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    setting = db.query(Setting).filter(Setting.user_id == user_id).first()
    if not setting:
        raise HTTPException(status_code=400, detail="請先在系統設定完成 AI 供應商與 API Key 設定")

    check_rate_limit(f"prompt-expand:{user_id}", limit=20, window_seconds=60)
    require_feature_access(db, int(user_id), feature="prompt_expand", amount=1)

    model = payload.model or setting.prompt_model or "gpt-4.1-mini"

    try:
        prompt = expand_prompt_with_provider(
            user_setting=_hydrate_provider_keys(setting),
            requirement=payload.requirement,
            model=model,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"提示詞擴寫失敗：{exc}") from exc

    log_audit(db, action="articles.prompt_expand", user_id=user_id, metadata={"model": model})
    consume_feature_usage(db, int(user_id), feature="prompt_expand", amount=1)
    return PromptExpandResponse(prompt=prompt)


@router.post("/generate", response_model=ArticleOut)
def generate_article(
    payload: ArticleGenerateRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    setting = db.query(Setting).filter(Setting.user_id == user_id).first()
    if not setting:
        raise HTTPException(status_code=400, detail="請先在系統設定完成 AI 供應商與 API Key 設定")

    contexts: list[str] = []
    if payload.selected_file_ids:
        files = (
            db.query(KnowledgeFile)
            .filter(
                KnowledgeFile.user_id == user_id,
                KnowledgeFile.id.in_(payload.selected_file_ids),
                KnowledgeFile.is_active.is_(True),
            )
            .all()
        )
        contexts = [extract_text_from_file(f.stored_path) for f in files]

    check_rate_limit(f"article-generate:{user_id}", limit=10, window_seconds=60)
    require_feature_access(db, int(user_id), feature="article_generate", amount=1)

    model = payload.model or setting.article_model or "gpt-4.1-mini"

    try:
        content = generate_article_with_provider(
            user_setting=_hydrate_provider_keys(setting),
            topic=payload.topic,
            outline=payload.outline,
            contexts=contexts,
            model=model,
            user_prompt=payload.prompt,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"生成失敗：{exc}") from exc

    article = Article(
        user_id=user_id,
        topic=payload.topic,
        outline=payload.outline,
        content=content,
        selected_file_ids=",".join(str(fid) for fid in payload.selected_file_ids) if payload.selected_file_ids else None,
        generation_model=model,
        generation_status="generated",
    )
    db.add(article)
    db.commit()
    db.refresh(article)

    log_audit(db, action="articles.generate", user_id=user_id, metadata={"article_id": article.id, "model": model})
    consume_feature_usage(db, int(user_id), feature="article_generate", amount=1)
    return article


@router.get("/{article_id}", response_model=ArticleOut)
def get_article(
    article_id: int,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    article = db.query(Article).filter(Article.id == article_id, Article.user_id == user_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="找不到文章")
    return article


@router.put("/{article_id}", response_model=ArticleOut)
def update_article_content(
    article_id: int,
    payload: ArticleUpdateRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    article = db.query(Article).filter(Article.id == article_id, Article.user_id == user_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="找不到文章")

    article.content = payload.content
    article.generation_status = "edited"
    db.commit()
    db.refresh(article)

    log_audit(db, action="articles.update", user_id=user_id, metadata={"article_id": article.id})
    return article
