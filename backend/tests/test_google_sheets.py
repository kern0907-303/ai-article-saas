from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api import google_sheets
from app.services.google_sheets_service import (
    GOOGLE_SHEETS_CELL_LIMIT,
    OVERSIZED_CELL_PLACEHOLDER,
    GoogleSheetsAppendResult,
    build_article_sheet_row,
    build_article_sheet_rows,
    normalize_sheet_destination_payload,
    sanitize_sheet_rows,
)
from app.services.pcloud_service import PCloudConfig


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


def test_build_article_sheet_rows_splits_long_content_for_google_cell_limit():
    class LongArticleStub(ArticleStub):
        content = "A" * (GOOGLE_SHEETS_CELL_LIMIT + 1000)

    rows = build_article_sheet_rows(LongArticleStub(), destination_label="客戶 A")

    assert len(rows) == 2
    assert rows[0][5].startswith("[第 1/2 段]\n")
    assert rows[1][5].startswith("[第 2/2 段]\n")
    assert all(len(str(row[5])) <= GOOGLE_SHEETS_CELL_LIMIT for row in rows)
    assert rows[0][0] == rows[1][0] == "2026-06-04T10:00:00"
    assert rows[0][2] == rows[1][2] == 42


def test_build_article_sheet_row_only_exports_public_image_links():
    row = build_article_sheet_row(
        ArticleStub(),
        destination_label="客戶 A",
        image_links=[
            f"data:image/png;base64,{'A' * 60000}",
            "/local/path/image.png",
            "https://public.example.com/article/cover.png",
        ],
    )

    assert "data:image" not in row[10]
    assert "/local/path" not in row[10]
    assert "https://public.example.com/article/cover.png" in row[10]
    assert len(row[10]) < GOOGLE_SHEETS_CELL_LIMIT


def test_sanitize_sheet_rows_replaces_any_oversized_cell_before_append():
    rows = [["ok", "B" * (GOOGLE_SHEETS_CELL_LIMIT + 1)]]

    sanitized = sanitize_sheet_rows(rows)

    assert sanitized == [["ok", OVERSIZED_CELL_PLACEHOLDER]]


def test_append_result_reports_updated_range():
    result = GoogleSheetsAppendResult(
        spreadsheet_id="sheet-123",
        sheet_name="文章準備",
        updated_range="文章準備!A2:K2",
        updated_rows=1,
    )

    assert result.updated_range == "文章準備!A2:K2"


def test_resolve_sheet_image_link_returns_public_url():
    image = SimpleNamespace(id=9, image_url="https://public.example.com/article/cover.png")

    assert google_sheets._resolve_sheet_image_link(image, article_id=42) == "https://public.example.com/article/cover.png"


def test_resolve_sheet_image_link_requires_pcloud_for_data_url(monkeypatch):
    image = SimpleNamespace(id=9, image_url="data:image/png;base64,abc")
    monkeypatch.setattr(google_sheets, "_get_pcloud_config", lambda: PCloudConfig(auth_token=None))

    with pytest.raises(HTTPException, match="圖片尚未轉成公開網址"):
        google_sheets._resolve_sheet_image_link(image, article_id=42)


def test_resolve_sheet_image_link_uploads_data_url_for_sheets(monkeypatch):
    image = SimpleNamespace(id=9, image_url="data:image/png;base64,abc")
    monkeypatch.setattr(google_sheets, "_get_pcloud_config", lambda: PCloudConfig(auth_token="token", folder_id=123))
    monkeypatch.setattr(
        google_sheets,
        "upload_data_url_to_pcloud",
        lambda config, data_url, article_id, image_id: "https://public.example.com/article/generated.png",
    )

    url = google_sheets._resolve_sheet_image_link(image, article_id=42)

    assert url == "https://public.example.com/article/generated.png"
    assert image.image_url == "https://public.example.com/article/generated.png"
