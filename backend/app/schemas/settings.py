from datetime import datetime

from pydantic import BaseModel


class SettingsBase(BaseModel):
    ai_provider: str = "openai"
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    gemini_api_key: str | None = None
    github_api_key: str | None = None
    website_api_key: str | None = None
    social_api_key: str | None = None

    article_model: str = "gpt-5.4-mini"
    prompt_model: str = "gpt-5.4-mini"
    image_model: str = "gpt-image-2"

    website_endpoint: str | None = None
    social_endpoint: str | None = None
    notes: str | None = None


class SettingsUpsert(SettingsBase):
    pass


class SettingsOut(SettingsBase):
    id: int
    user_id: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ModelCatalogItem(BaseModel):
    key: str
    provider: str
    category: str
    label: str
    description: str
    cost_tier: str


class ModelCatalogResponse(BaseModel):
    models: list[ModelCatalogItem]
