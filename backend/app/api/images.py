from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings as app_settings
from app.core.database import SessionLocal, get_db
from app.models.article import Article
from app.models.article_image import ArticleImage
from app.models.image_setting import ImageSetting
from app.models.settings import Setting
from app.schemas.image import (
    ArticleImageOut,
    GenerateArticleImagesRequest,
    ImageSizePresetOut,
    ImageSettingsOut,
    ImageSettingsUpsert,
    ImageStylePresetOut,
    RegenerateArticleImageRequest,
)
from app.services.audit_service import log_audit
from app.services.crypto_service import decrypt_text
from app.services.entitlement_service import consume_feature_usage, require_feature_access
from app.services.image_service import generate_image_plan, list_size_presets, list_style_presets
from app.services.pcloud_service import PCloudConfig, upload_data_url_to_pcloud
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


def _get_openai_image_api_key(db: Session, user_id: str) -> str | None:
    setting = db.query(Setting).filter(Setting.user_id == user_id).first()
    if not setting:
        return None
    return decrypt_text(setting.openai_api_key_encrypted) or setting.openai_api_key


def _get_pcloud_config() -> PCloudConfig:
    return PCloudConfig(
        auth_token=app_settings.pcloud_auth_token,
        api_host=app_settings.pcloud_api_host,
        folder_id=app_settings.pcloud_folder_id,
        folder_path=app_settings.pcloud_folder_path,
        create_public_link=app_settings.pcloud_create_public_link,
        use_direct_download_link=app_settings.pcloud_use_direct_download_link,
    )


def _persist_image_url(image_url: str, *, article_id: int, image_id: int) -> str:
    pcloud_config = _get_pcloud_config()
    if pcloud_config.enabled and image_url.startswith("data:image/"):
        return upload_data_url_to_pcloud(
            pcloud_config,
            data_url=image_url,
            article_id=article_id,
            image_id=image_id,
        )
    return image_url


def _generate_images_in_background(
    *,
    image_ids: list[int],
    article_id: int,
    user_id: str,
    style_preset: str,
    output_size: str | None,
    custom_prompt: str | None,
    need_text_overlay: bool,
    text_language: str,
    text_content: str | None,
    num_images: int,
) -> None:
    db = SessionLocal()
    try:
        article = db.query(Article).filter(Article.id == article_id, Article.user_id == user_id).first()
        if not article:
            return

        records = (
            db.query(ArticleImage)
            .filter(ArticleImage.user_id == user_id, ArticleImage.article_id == article_id, ArticleImage.id.in_(image_ids))
            .all()
        )
        if not records:
            return

        for record in records:
            record.status = "generating"
            record.generation_error = None
        db.commit()

        setting = _get_or_create_setting(db, user_id)
        plans = generate_image_plan(
            article_topic=article.topic,
            article_outline=article.outline,
            style_preset=style_preset,
            output_size=output_size,
            custom_prompt=custom_prompt,
            need_text_overlay=need_text_overlay,
            text_language=text_language,
            text_content=text_content,
            num_images=num_images,
            setting=setting,
            openai_api_key=_get_openai_image_api_key(db, user_id),
        )

        for record, plan in zip(records, plans, strict=False):
            record.provider = plan["provider"]
            record.model = plan["model"]
            record.prompt = plan["prompt"]
            record.image_url = _persist_image_url(plan["image_url"], article_id=article_id, image_id=record.id)
            record.width = plan["width"]
            record.height = plan["height"]
            record.text_language = plan["text_language"]
            record.text_content = plan["text_content"]
            record.generation_error = None
            record.status = "generated"

        db.commit()
        log_audit(db, action="images.generate", user_id=user_id, metadata={"article_id": article_id, "count": len(records)})
        consume_feature_usage(db, int(user_id), feature="image_generate", amount=len(records))
    except Exception as exc:
        db.rollback()
        failed_records = (
            db.query(ArticleImage)
            .filter(ArticleImage.user_id == user_id, ArticleImage.article_id == article_id, ArticleImage.id.in_(image_ids))
            .all()
        )
        for record in failed_records:
            record.status = "failed"
            record.generation_error = str(exc)
        db.commit()
    finally:
        db.close()


@router.get("/image-style-presets", response_model=list[ImageStylePresetOut])
def get_style_presets():
    return list_style_presets()


@router.get("/image-size-presets", response_model=list[ImageSizePresetOut])
def get_size_presets():
    return list_size_presets()


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
    background_tasks: BackgroundTasks,
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

    records: list[ArticleImage] = []
    for _ in range(num_images):
        record = ArticleImage(
            user_id=user_id,
            article_id=article.id,
            provider="pending",
            model="pending",
            style_preset=payload.style_preset,
            prompt=payload.custom_prompt or "",
            image_url="",
            width=1536,
            height=1024,
            text_language=payload.text_language,
            text_content=payload.text_content,
            generation_error=None,
            status="queued",
        )
        db.add(record)
        records.append(record)

    db.commit()
    for record in records:
        db.refresh(record)

    background_tasks.add_task(
        _generate_images_in_background,
        image_ids=[record.id for record in records],
        article_id=article.id,
        user_id=user_id,
        style_preset=payload.style_preset,
        output_size=payload.output_size,
        custom_prompt=payload.custom_prompt,
        need_text_overlay=payload.need_text_overlay,
        text_language=payload.text_language,
        text_content=payload.text_content,
        num_images=len(records),
    )
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
        output_size=None,
        custom_prompt=payload.custom_prompt,
        need_text_overlay=payload.need_text_overlay,
        text_language=payload.text_language,
        text_content=payload.text_content,
        num_images=1,
        setting=setting,
        openai_api_key=_get_openai_image_api_key(db, user_id),
    )
    plan = plans[0]

    record.provider = plan["provider"]
    record.model = plan["model"]
    record.style_preset = style_preset
    record.prompt = plan["prompt"]
    record.image_url = _persist_image_url(plan["image_url"], article_id=article.id, image_id=record.id)
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
