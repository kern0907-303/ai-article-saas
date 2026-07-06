from datetime import datetime

from pydantic import BaseModel, Field


class ArticleGenerateRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=255)
    outline: str = Field(min_length=1)
    selected_file_ids: list[int] = []
    use_default_references: bool = True
    workspace_id: int | None = None
    knowledge_categories: list[str] = []
    model: str | None = None
    prompt: str | None = None


class PromptExpandRequest(BaseModel):
    requirement: str = Field(min_length=1, max_length=500)
    model: str | None = None


class PromptExpandResponse(BaseModel):
    prompt: str


class ArticleUpdateRequest(BaseModel):
    content: str = Field(min_length=1)


class ArticleOut(BaseModel):
    id: int
    user_id: str
    workspace_id: int | None
    topic: str
    outline: str
    content: str | None
    generation_error: str | None
    selected_file_ids: str | None
    knowledge_categories: str | None
    generation_model: str | None
    generation_status: str
    published_to_website: bool
    published_to_social: bool
    publish_website_result: str | None
    publish_social_result: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PublishResponse(BaseModel):
    success: bool
    channel: str
    message: str
    article_id: int
