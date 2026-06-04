from datetime import datetime

from pydantic import BaseModel, Field


class ImageSettingsBase(BaseModel):
    image_provider_mode: str = Field(default="auto")
    default_provider: str = Field(default="openai")
    force_nano_banana_for_zh_text: bool = True
    nano_banana_model: str = "nano-banana-pro"
    openai_image_model: str = "gpt-image-2"
    default_size: str = "1080x1080"
    default_quality: str = "high"
    output_format: str = "png"
    images_per_article: int = Field(default=1, ge=1, le=5)
    zh_text_detection_keywords: str = "中文,繁體,標語,文案,海報,banner,封面文字,字卡"


class ImageSettingsUpsert(ImageSettingsBase):
    pass


class ImageSettingsOut(ImageSettingsBase):
    id: int
    user_id: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ImageStylePresetOut(BaseModel):
    key: str
    label: str
    description: str


class ImageSizePresetOut(BaseModel):
    key: str
    label: str
    description: str
    size: str
    width: int
    height: int


class ArticleImageOut(BaseModel):
    id: int
    user_id: str
    article_id: int
    provider: str
    model: str
    style_preset: str
    prompt: str
    image_url: str
    width: int
    height: int
    text_language: str | None
    text_content: str | None
    generation_error: str | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class GenerateArticleImagesRequest(BaseModel):
    style_preset: str = "blog_cover"
    output_size: str | None = None
    custom_prompt: str | None = None
    need_text_overlay: bool = False
    text_language: str = "none"
    text_content: str | None = None
    num_images: int | None = Field(default=None, ge=1, le=5)


class RegenerateArticleImageRequest(BaseModel):
    style_preset: str | None = None
    custom_prompt: str | None = None
    need_text_overlay: bool = False
    text_language: str = "none"
    text_content: str | None = None
