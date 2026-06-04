from datetime import datetime

from pydantic import BaseModel, Field


class GoogleSheetDestinationBase(BaseModel):
    label: str = Field(min_length=1, max_length=120)
    spreadsheet_id: str = Field(min_length=1, max_length=255)
    sheet_name: str = Field(default="文章準備", min_length=1, max_length=120)
    is_default: bool = False


class GoogleSheetDestinationCreate(GoogleSheetDestinationBase):
    service_account_json: str = Field(min_length=1)


class GoogleSheetDestinationUpdate(GoogleSheetDestinationBase):
    service_account_json: str | None = None


class GoogleSheetDestinationOut(GoogleSheetDestinationBase):
    id: int
    user_id: str
    service_account_email: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ExportArticleToSheetRequest(BaseModel):
    destination_id: int | None = None


class ExportArticleToSheetResponse(BaseModel):
    success: bool
    article_id: int
    destination_id: int
    destination_label: str
    spreadsheet_id: str
    sheet_name: str
    updated_range: str
    updated_rows: int
    message: str
