from datetime import datetime

from pydantic import BaseModel


class SettingsBase(BaseModel):
    openai_api_key: str | None = None
    website_api_key: str | None = None
    social_api_key: str | None = None

    article_model: str = "gpt-4.1-mini"
    prompt_model: str = "gpt-4.1-mini"
    image_model: str = "gpt-image-1"

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
