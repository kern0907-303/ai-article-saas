from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.article import Article
from app.models.article_image import ArticleImage
from app.models.image_setting import ImageSetting
from app.schemas.image import (
    ArticleImageOut,
    GenerateArticleImagesRequest,
    ImageSettingsOut,
    ImageSettingsUpsert,
    ImageStylePresetOut,
    RegenerateArticleImageRequest,
)
from app.services.audit_service import log_audit
from app.services.entitlement_service import consume_feature_usage, require_feature_access
from app.services.image_service import generate_image_plan, list_style_presets
from app.services.rate_limit_service import check_rate_limit
from app.utils.deps import get_current_user_id, require_active_subscription

router = APIRouter(tags=["images"])


def _get_or_create_setting(db: Session, user_id: str) -> ImageSetting:
    setting = db.query(ImageSetting).filter(ImageSetting.user_id == user_id).first()
    if setting:
        return setting

    setting = ImageSetting(user_id=user_id)
    db.add(setting)
    try:
        db.commit()
        db.refresh(setting)
        return setting
    except IntegrityError:
        db.rollback()
        existing = db.query(ImageSetting).filter(ImageSetting.user_id == user_id).first()
        if existing:
            return existing
        raise


@router.get("/image-style-presets", response_model=list[ImageStylePresetOut])
def get_style_presets():
    return list_style_presets()


@router.get("/image-settings", response_model=ImageSettingsOut)
def get_image_settings(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    return _get_or_create_setting(db, user_id)


@router.put("/image-settings", response_model=ImageSettingsOut)
def upsert_image_settings(
    payload: ImageSettingsUpsert,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    setting = _get_or_create_setting(db, user_id)
    for key, value in payload.model_dump().items():
        setattr(setting, key, value)

    db.commit()
    db.refresh(setting)
    log_audit(db, action="images.settings_update", user_id=user_id, metadata={"mode": setting.image_provider_mode})
    return setting


@router.get("/articles/{article_id}/images", response_model=list[ArticleImageOut])
def list_article_images(
    article_id: int,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    _: object = Depends(require_active_subscription),
):
    article = db.query(Article).filter(Article.id == article_id, Article.user_id == user_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="找不到文章")

    return (
        db.query(ArticleImage)
        .filter(ArticleImage.article_id == article_id, ArticleImage.user_id == user_id)
        .order_by(ArticleImage.created_at.desc())
        .all()
    )


@router.post("/articles/{article_id}/generate-images", response_model=list[ArticleImageOut])
def generate_article_images(
    article_id: int,
    payload: GenerateArticleImagesRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    _: object = Depends(require_active_subscription),
):
    article = db.query(Article).filter(Article.id == article_id, Article.user_id == user_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="找不到文章")

    check_rate_limit(f"image-generate:{user_id}", limit=15, window_seconds=60)

    setting = _get_or_create_setting(db, user_id)
    num_images = payload.num_images or setting.images_per_article
    require_feature_access(db, int(user_id), feature="image_generate", amount=num_images)

    plans = generate_image_plan(
        article_topic=article.topic,
        article_outline=article.outline,
        style_preset=payload.style_preset,
        custom_prompt=payload.custom_prompt,
        need_text_overlay=payload.need_text_overlay,
        text_language=payload.text_language,
        text_content=payload.text_content,
        num_images=num_images,
        setting=setting,
    )

    records: list[ArticleImage] = []
    for plan in plans:
        record = ArticleImage(
            user_id=user_id,
            article_id=article.id,
            provider=plan["provider"],
            model=plan["model"],
            style_preset=payload.style_preset,
            prompt=plan["prompt"],
            image_url=plan["image_url"],
            width=plan["width"],
            height=plan["height"],
            text_language=plan["text_language"],
            text_content=plan["text_content"],
            status="generated",
        )
        db.add(record)
        records.append(record)

    db.commit()
    for record in records:
        db.refresh(record)

    log_audit(db, action="images.generate", user_id=user_id, metadata={"article_id": article.id, "count": len(records)})
    consume_feature_usage(db, int(user_id), feature="image_generate", amount=len(records))
    return records


@router.put("/article-images/{image_id}", response_model=ArticleImageOut)
def regenerate_article_image(
    image_id: int,
    payload: RegenerateArticleImageRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    _: object = Depends(require_active_subscription),
):
    record = db.query(ArticleImage).filter(ArticleImage.id == image_id, ArticleImage.user_id == user_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="找不到圖片")

    article = db.query(Article).filter(Article.id == record.article_id, Article.user_id == user_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="找不到圖片對應文章")

    setting = _get_or_create_setting(db, user_id)
    style_preset = payload.style_preset or record.style_preset
    require_feature_access(db, int(user_id), feature="image_generate", amount=1)

    plans = generate_image_plan(
        article_topic=article.topic,
        article_outline=article.outline,
        style_preset=style_preset,
        custom_prompt=payload.custom_prompt,
        need_text_overlay=payload.need_text_overlay,
        text_language=payload.text_language,
        text_content=payload.text_content,
        num_images=1,
        setting=setting,
    )
    plan = plans[0]

    record.provider = plan["provider"]
    record.model = plan["model"]
    record.style_preset = style_preset
    record.prompt = plan["prompt"]
    record.image_url = plan["image_url"]
    record.width = plan["width"]
    record.height = plan["height"]
    record.text_language = plan["text_language"]
    record.text_content = plan["text_content"]
    record.status = "generated"

    db.commit()
    db.refresh(record)
    consume_feature_usage(db, int(user_id), feature="image_generate", amount=1)
    log_audit(db, action="images.regenerate", user_id=user_id, metadata={"image_id": record.id})
    return record


@router.delete("/article-images/{image_id}")
def delete_article_image(
    image_id: int,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    _: object = Depends(require_active_subscription),
):
    record = db.query(ArticleImage).filter(ArticleImage.id == image_id, ArticleImage.user_id == user_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="找不到圖片")

    db.delete(record)
    db.commit()
    log_audit(db, action="images.delete", user_id=user_id, metadata={"image_id": image_id})
    return {"success": True, "message": "圖片已刪除", "image_id": image_id}
