from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import settings


def ensure_user_storage(user_id: str) -> Path:
    user_folder = settings.storage_dir / user_id
    user_folder.mkdir(parents=True, exist_ok=True)
    return user_folder


async def save_uploaded_file(user_id: str, upload: UploadFile) -> tuple[str, int]:
    user_folder = ensure_user_storage(user_id)
    suffix = Path(upload.filename or "untitled.txt").suffix
    safe_name = f"{uuid4().hex}{suffix}"
    target_path = user_folder / safe_name

    content = await upload.read()
    target_path.write_bytes(content)
    return str(target_path), len(content)


def extract_text_from_file(path: str) -> str:
    raw = Path(path).read_bytes()
    for encoding in ("utf-8", "utf-8-sig", "big5", "cp950"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="ignore")
