from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import settings


def decode_file_bytes(raw: bytes) -> str:
    for encoding in ("utf-8", "utf-8-sig", "big5", "cp950"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="ignore")


def ensure_user_storage(user_id: str) -> Path:
    user_folder = settings.storage_dir / user_id
    user_folder.mkdir(parents=True, exist_ok=True)
    return user_folder


async def save_uploaded_file(user_id: str, upload: UploadFile) -> tuple[str, int, str]:
    user_folder = ensure_user_storage(user_id)
    suffix = Path(upload.filename or "untitled.txt").suffix
    safe_name = f"{uuid4().hex}{suffix}"
    target_path = user_folder / safe_name

    content = await upload.read()
    target_path.write_bytes(content)
    return str(target_path), len(content), decode_file_bytes(content)


def extract_text_from_file(path: str, fallback_text: str | None = None) -> str:
    if fallback_text:
        return fallback_text
    if path.startswith("db://"):
        return ""

    raw = Path(path).read_bytes()
    return decode_file_bytes(raw)
