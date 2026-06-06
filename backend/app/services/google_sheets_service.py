import json
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from urllib.parse import quote

import httpx
import jwt

SHEETS_SCOPE = "https://www.googleapis.com/auth/spreadsheets"
TOKEN_URL = "https://oauth2.googleapis.com/token"
SHEETS_APPEND_URL = "https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{range_name}:append"
GOOGLE_TIMEOUT = httpx.Timeout(connect=15.0, read=60.0, write=30.0, pool=30.0)
GOOGLE_SHEETS_CELL_LIMIT = 50000
ARTICLE_CONTENT_CHUNK_SIZE = 45000


@dataclass(frozen=True)
class GoogleSheetsAppendResult:
    spreadsheet_id: str
    sheet_name: str
    updated_range: str
    updated_rows: int


def _parse_service_account_json(service_account_json: str) -> dict[str, Any]:
    try:
        data = json.loads(service_account_json)
    except json.JSONDecodeError as exc:
        raise ValueError("Service Account JSON 格式不正確") from exc

    if not isinstance(data, dict):
        raise ValueError("Service Account JSON 必須是 JSON object")
    if not isinstance(data.get("client_email"), str) or not data["client_email"].strip():
        raise ValueError("Service Account JSON 缺少 client_email")
    if not isinstance(data.get("private_key"), str) or not data["private_key"].strip():
        raise ValueError("Service Account JSON 缺少 private_key")
    return data


def normalize_sheet_destination_payload(payload: dict[str, Any]) -> dict[str, Any]:
    data = dict(payload)
    service_account_json = str(data.get("service_account_json") or "")
    account = _parse_service_account_json(service_account_json)
    data["label"] = str(data.get("label") or "").strip()
    data["spreadsheet_id"] = str(data.get("spreadsheet_id") or "").strip()
    data["sheet_name"] = str(data.get("sheet_name") or "文章準備").strip()
    data["service_account_json"] = service_account_json
    data["service_account_email"] = account["client_email"].strip()
    data["is_default"] = bool(data.get("is_default"))
    if not data["label"]:
        raise ValueError("請填入目的地名稱")
    if not data["spreadsheet_id"]:
        raise ValueError("請填入 Spreadsheet ID")
    if not data["sheet_name"]:
        raise ValueError("請填入工作表名稱")
    return data


def split_article_content_for_sheet(content: str) -> list[str]:
    if len(content) <= GOOGLE_SHEETS_CELL_LIMIT:
        return [content]

    chunks: list[str] = []
    remaining = content
    while remaining:
        chunks.append(remaining[:ARTICLE_CONTENT_CHUNK_SIZE])
        remaining = remaining[ARTICLE_CONTENT_CHUNK_SIZE:]
    return chunks


def _build_article_sheet_base_row(article: Any, destination_label: str, image_links: list[str] | None = None) -> list[Any]:
    updated_at = getattr(article, "updated_at", None) or datetime.utcnow()
    if hasattr(updated_at, "isoformat"):
        updated_text = updated_at.isoformat()
    else:
        updated_text = str(updated_at)

    return [
        updated_text,
        destination_label,
        article.id,
        article.topic,
        article.outline,
        "",
        article.generation_model or "",
        article.generation_status,
        "yes" if article.published_to_website else "no",
        "yes" if article.published_to_social else "no",
        "\n".join(image_links or []),
    ]


def build_article_sheet_rows(article: Any, destination_label: str, image_links: list[str] | None = None) -> list[list[Any]]:
    base_row = _build_article_sheet_base_row(article, destination_label, image_links)
    content_chunks = split_article_content_for_sheet(article.content or "")
    if len(content_chunks) == 1:
        row = list(base_row)
        row[5] = content_chunks[0]
        return [row]

    rows: list[list[Any]] = []
    total = len(content_chunks)
    for index, chunk in enumerate(content_chunks, start=1):
        row = list(base_row)
        row[5] = f"[第 {index}/{total} 段]\n{chunk}"
        rows.append(row)
    return rows


def build_article_sheet_row(article: Any, destination_label: str, image_links: list[str] | None = None) -> list[Any]:
    return build_article_sheet_rows(article, destination_label, image_links)[0]


def _build_jwt_assertion(service_account: dict[str, Any]) -> str:
    now = int(time.time())
    payload = {
        "iss": service_account["client_email"],
        "scope": SHEETS_SCOPE,
        "aud": TOKEN_URL,
        "iat": now,
        "exp": now + 3600,
    }
    return jwt.encode(payload, service_account["private_key"], algorithm="RS256")


def fetch_access_token(service_account_json: str) -> str:
    service_account = _parse_service_account_json(service_account_json)
    assertion = _build_jwt_assertion(service_account)
    response = httpx.post(
        TOKEN_URL,
        data={
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": assertion,
        },
        timeout=GOOGLE_TIMEOUT,
    )
    if response.is_error:
        raise RuntimeError(f"Google OAuth 驗證失敗：{response.text}")
    token = response.json().get("access_token")
    if not isinstance(token, str) or not token:
        raise RuntimeError("Google OAuth 未回傳 access_token")
    return token


def append_article_row_to_sheet(
    *,
    service_account_json: str,
    spreadsheet_id: str,
    sheet_name: str,
    row: list[Any],
) -> GoogleSheetsAppendResult:
    return append_article_rows_to_sheet(
        service_account_json=service_account_json,
        spreadsheet_id=spreadsheet_id,
        sheet_name=sheet_name,
        rows=[row],
    )


def append_article_rows_to_sheet(
    *,
    service_account_json: str,
    spreadsheet_id: str,
    sheet_name: str,
    rows: list[list[Any]],
) -> GoogleSheetsAppendResult:
    access_token = fetch_access_token(service_account_json)
    range_name = f"{sheet_name}!A:K"
    url = SHEETS_APPEND_URL.format(
        spreadsheet_id=quote(spreadsheet_id, safe=""),
        range_name=quote(range_name, safe=""),
    )
    response = httpx.post(
        url,
        params={"valueInputOption": "USER_ENTERED", "insertDataOption": "INSERT_ROWS"},
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
        json={"values": rows},
        timeout=GOOGLE_TIMEOUT,
    )
    if response.is_error:
        raise RuntimeError(f"Google Sheets 寫入失敗：{response.text}")

    updates = response.json().get("updates", {})
    return GoogleSheetsAppendResult(
        spreadsheet_id=spreadsheet_id,
        sheet_name=sheet_name,
        updated_range=str(updates.get("updatedRange") or ""),
        updated_rows=int(updates.get("updatedRows") or 0),
    )
