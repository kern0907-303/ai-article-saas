from datetime import datetime

import pytest

from app.services.google_sheets_service import (
    GoogleSheetsAppendResult,
    build_article_sheet_row,
    normalize_sheet_destination_payload,
)


class ArticleStub:
    id = 42
    topic = "品牌定位"
    outline = "一、問題\n二、方法"
    content = "這是一篇已完成文章"
    generation_model = "gpt-5.4-mini"
    generation_status = "edited"
    published_to_website = False
    published_to_social = True
    created_at = datetime(2026, 6, 4, 9, 30, 0)
    updated_at = datetime(2026, 6, 4, 10, 0, 0)


def test_normalize_sheet_destination_payload_requires_service_account_email():
    payload = normalize_sheet_destination_payload(
        {
            "label": "客戶 A",
            "spreadsheet_id": "sheet-123",
            "sheet_name": "文章準備",
            "service_account_json": '{"client_email":"bot@example.iam.gserviceaccount.com","private_key":"key"}',
            "is_default": True,
        }
    )

    assert payload["label"] == "客戶 A"
    assert payload["sheet_name"] == "文章準備"
    assert payload["service_account_email"] == "bot@example.iam.gserviceaccount.com"


def test_normalize_sheet_destination_payload_rejects_invalid_json():
    with pytest.raises(ValueError, match="Service Account JSON"):
        normalize_sheet_destination_payload(
            {
                "label": "客戶 A",
                "spreadsheet_id": "sheet-123",
                "sheet_name": "文章準備",
                "service_account_json": "{bad json",
            }
        )


def test_build_article_sheet_row_contains_publish_ready_fields():
    row = build_article_sheet_row(
        ArticleStub(),
        destination_label="客戶 A",
        image_links=["https://public.example.com/article/cover.png"],
    )

    assert row[0] == "2026-06-04T10:00:00"
    assert row[1] == "客戶 A"
    assert row[2] == 42
    assert row[3] == "品牌定位"
    assert row[5] == "這是一篇已完成文章"
    assert row[6] == "gpt-5.4-mini"
    assert row[9] == "yes"
    assert row[10] == "https://public.example.com/article/cover.png"


def test_append_result_reports_updated_range():
    result = GoogleSheetsAppendResult(
        spreadsheet_id="sheet-123",
        sheet_name="文章準備",
        updated_range="文章準備!A2:K2",
        updated_rows=1,
    )

    assert result.updated_range == "文章準備!A2:K2"
