from datetime import datetime

from pydantic import BaseModel, Field


class WorkspaceCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    tone: str | None = None
    audience: str | None = None
    notes: str | None = None
    is_default: bool = False


class WorkspaceUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    tone: str | None = None
    audience: str | None = None
    notes: str | None = None
    is_default: bool | None = None


class WorkspaceOut(BaseModel):
    id: int
    user_id: str
    name: str
    description: str | None
    tone: str | None
    audience: str | None
    notes: str | None
    is_default: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
