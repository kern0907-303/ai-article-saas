from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.settings import Setting
from app.schemas.settings import ModelCatalogItem, ModelCatalogResponse, SettingsOut, SettingsUpsert
from app.services.audit_service import log_audit
from app.services.crypto_service import decrypt_text, encrypt_text
from app.utils.deps import get_current_user_id

router = APIRouter(prefix="/settings", tags=["settings"])

MODEL_CATALOG: list[ModelCatalogItem] = [
    ModelCatalogItem(
        key="gpt-4.1-mini",
        provider="openai",
        category="text",
        label="GPT-4.1 Mini",
        description="速度快，成本較低，適合日常內容生成",
        cost_tier="low",
    ),
    ModelCatalogItem(
        key="gpt-4.1",
        provider="openai",
        category="text",
        label="GPT-4.1",
        description="品質更高，適合長文與高精度需求",
        cost_tier="high",
    ),
    ModelCatalogItem(
        key="gpt-image-1",
        provider="openai",
        category="image",
        label="GPT Image 1",
        description="通用圖片生成模型",
        cost_tier="medium",
    ),
    ModelCatalogItem(
        key="nano-banana-v1",
        provider="nano_banana",
        category="image",
        label="Nano Banana v1",
        description="中文文字排版表現較佳",
        cost_tier="medium",
    ),
]


def _out_from_setting(record: Setting) -> SettingsOut:
    return SettingsOut(
        id=record.id,
        user_id=record.user_id,
        openai_api_key=decrypt_text(record.openai_api_key_encrypted) or record.openai_api_key,
        website_api_key=decrypt_text(record.website_api_key_encrypted) or record.website_api_key,
        social_api_key=decrypt_text(record.social_api_key_encrypted) or record.social_api_key,
        article_model=record.article_model,
        prompt_model=record.prompt_model,
        image_model=record.image_model,
        website_endpoint=record.website_endpoint,
        social_endpoint=record.social_endpoint,
        notes=record.notes,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@router.get("", response_model=SettingsOut | None)
def get_settings(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    record = db.query(Setting).filter(Setting.user_id == user_id).first()
    if not record:
        return None
    return _out_from_setting(record)


@router.put("", response_model=SettingsOut)
def upsert_settings(
    payload: SettingsUpsert,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    record = db.query(Setting).filter(Setting.user_id == user_id).first()
    if not record:
        record = Setting(user_id=user_id)
        db.add(record)

    data = payload.model_dump()

    record.openai_api_key_encrypted = encrypt_text(data.get("openai_api_key"))
    record.website_api_key_encrypted = encrypt_text(data.get("website_api_key"))
    record.social_api_key_encrypted = encrypt_text(data.get("social_api_key"))

    # 去除明文殘留
    record.openai_api_key = None
    record.website_api_key = None
    record.social_api_key = None

    record.article_model = data.get("article_model") or record.article_model
    record.prompt_model = data.get("prompt_model") or record.prompt_model
    record.image_model = data.get("image_model") or record.image_model
    record.website_endpoint = data.get("website_endpoint")
    record.social_endpoint = data.get("social_endpoint")
    record.notes = data.get("notes")

    db.commit()
    db.refresh(record)

    log_audit(db, action="settings.update", user_id=user_id, metadata={"article_model": record.article_model, "prompt_model": record.prompt_model, "image_model": record.image_model})
    return _out_from_setting(record)


@router.get("/model-catalog", response_model=ModelCatalogResponse)
def get_model_catalog():
    return ModelCatalogResponse(models=MODEL_CATALOG)
