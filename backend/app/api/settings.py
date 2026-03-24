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
        key="claude-3-5-haiku-latest",
        provider="anthropic",
        category="text",
        label="Claude 3.5 Haiku",
        description="回應快，適合提示詞擴寫與一般文章草稿",
        cost_tier="low",
    ),
    ModelCatalogItem(
        key="claude-3-5-sonnet-latest",
        provider="anthropic",
        category="text",
        label="Claude 3.5 Sonnet",
        description="平衡品質與速度，適合較完整長文寫作",
        cost_tier="medium",
    ),
    ModelCatalogItem(
        key="gemini-1.5-flash",
        provider="gemini",
        category="text",
        label="Gemini 1.5 Flash",
        description="速度快，適合大量生成與快速試稿",
        cost_tier="low",
    ),
    ModelCatalogItem(
        key="gemini-1.5-pro",
        provider="gemini",
        category="text",
        label="Gemini 1.5 Pro",
        description="較適合長文、推理與較高品質內容生成",
        cost_tier="high",
    ),
    ModelCatalogItem(
        key="openai/gpt-4.1-mini",
        provider="github",
        category="text",
        label="GitHub Models: GPT-4.1 Mini",
        description="透過 GitHub Models 使用 OpenAI 的輕量模型",
        cost_tier="low",
    ),
    ModelCatalogItem(
        key="openai/gpt-4.1",
        provider="github",
        category="text",
        label="GitHub Models: GPT-4.1",
        description="透過 GitHub Models 使用 OpenAI 的高品質模型",
        cost_tier="high",
    ),
    ModelCatalogItem(
        key="openai/gpt-5-mini",
        provider="github",
        category="text",
        label="GitHub Models: GPT-5 mini",
        description="透過 GitHub Models 使用 OpenAI 的快速模型",
        cost_tier="low",
    ),
    ModelCatalogItem(
        key="openai/gpt-5.4",
        provider="github",
        category="text",
        label="GitHub Models: GPT-5.4",
        description="透過 GitHub Models 使用 OpenAI 的高能力模型",
        cost_tier="high",
    ),
    ModelCatalogItem(
        key="anthropic/claude-haiku-4.5",
        provider="github",
        category="text",
        label="GitHub Models: Claude Haiku 4.5",
        description="透過 GitHub Models 使用 Anthropic 的輕量模型",
        cost_tier="low",
    ),
    ModelCatalogItem(
        key="anthropic/claude-sonnet-4.5",
        provider="github",
        category="text",
        label="GitHub Models: Claude Sonnet 4.5",
        description="透過 GitHub Models 使用 Anthropic 的平衡模型",
        cost_tier="medium",
    ),
    ModelCatalogItem(
        key="google/gemini-2.5-pro",
        provider="github",
        category="text",
        label="GitHub Models: Gemini 2.5 Pro",
        description="透過 GitHub Models 使用 Google 的高品質模型",
        cost_tier="high",
    ),
    ModelCatalogItem(
        key="google/gemini-3-flash",
        provider="github",
        category="text",
        label="GitHub Models: Gemini 3 Flash",
        description="透過 GitHub Models 使用 Google 的快速模型",
        cost_tier="low",
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
        ai_provider=record.ai_provider or "openai",
        openai_api_key=decrypt_text(record.openai_api_key_encrypted) or record.openai_api_key,
        anthropic_api_key=decrypt_text(record.anthropic_api_key_encrypted) or record.anthropic_api_key,
        gemini_api_key=decrypt_text(record.gemini_api_key_encrypted) or record.gemini_api_key,
        github_api_key=decrypt_text(record.github_api_key_encrypted) or record.github_api_key,
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

    record.ai_provider = data.get("ai_provider") or record.ai_provider or "openai"
    record.openai_api_key_encrypted = encrypt_text(data.get("openai_api_key"))
    record.anthropic_api_key_encrypted = encrypt_text(data.get("anthropic_api_key"))
    record.gemini_api_key_encrypted = encrypt_text(data.get("gemini_api_key"))
    record.github_api_key_encrypted = encrypt_text(data.get("github_api_key"))
    record.website_api_key_encrypted = encrypt_text(data.get("website_api_key"))
    record.social_api_key_encrypted = encrypt_text(data.get("social_api_key"))

    # 去除明文殘留
    record.openai_api_key = None
    record.anthropic_api_key = None
    record.gemini_api_key = None
    record.github_api_key = None
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

    log_audit(
        db,
        action="settings.update",
        user_id=user_id,
        metadata={
            "ai_provider": record.ai_provider,
            "article_model": record.article_model,
            "prompt_model": record.prompt_model,
            "image_model": record.image_model,
        },
    )
    return _out_from_setting(record)


@router.get("/model-catalog", response_model=ModelCatalogResponse)
def get_model_catalog():
    return ModelCatalogResponse(models=MODEL_CATALOG)
