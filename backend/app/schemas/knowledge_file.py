from datetime import datetime

from pydantic import BaseModel


class KnowledgeFileOut(BaseModel):
    id: int
    user_id: str
    file_name: str
    stored_path: str
    workspace_id: int | None
    category: str
    content_type: str | None
    file_size: int
    extracted_text_preview: str | None
    is_active: bool
    is_default_reference: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class KnowledgeFileDefaultReferenceUpdate(BaseModel):
    is_default_reference: bool
