import base64
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

import httpx


PCLOUD_TIMEOUT = httpx.Timeout(connect=10.0, read=120.0, write=120.0, pool=30.0)


@dataclass(frozen=True)
class PCloudConfig:
    auth_token: str | None
    api_host: str = "api.pcloud.com"
    folder_id: int | None = None
    folder_path: str | None = None
    create_public_link: bool = True
    use_direct_download_link: bool = True

    @property
    def enabled(self) -> bool:
        return bool((self.auth_token or "").strip() and (self.folder_id is not None or (self.folder_path or "").strip()))

    @property
    def api_base(self) -> str:
        host = (self.api_host or "api.pcloud.com").replace("https://", "").replace("http://", "").strip("/")
        return f"https://{host}"


def decode_data_url(data_url: str) -> tuple[bytes, str]:
    match = re.match(r"^data:(image/(?:png|jpeg|jpg|webp));base64,(.+)$", data_url, flags=re.DOTALL)
    if not match:
        raise ValueError("圖片資料格式不是支援的 base64 data URL")

    mime = match.group(1).replace("image/jpg", "image/jpeg")
    return base64.b64decode(match.group(2)), mime


def extension_from_mime(mime: str) -> str:
    if mime == "image/jpeg":
        return "jpg"
    if mime == "image/webp":
        return "webp"
    return "png"


def build_image_filename(*, article_id: int, image_id: int, mime: str) -> str:
    timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    return f"article-{article_id}-image-{image_id}-{timestamp}-{uuid4().hex[:8]}.{extension_from_mime(mime)}"


def _raise_for_pcloud_error(payload: dict) -> None:
    if int(payload.get("result", 0) or 0) != 0:
        message = payload.get("error") or payload.get("message") or "pCloud API error"
        raise RuntimeError(f"pCloud 上傳失敗：{message} (code={payload.get('result')})")


def _request_json(method: str, url: str, **kwargs) -> dict:
    with httpx.Client(timeout=PCLOUD_TIMEOUT) as client:
        response = client.request(method, url, **kwargs)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise RuntimeError("pCloud API 回傳格式不正確")
    _raise_for_pcloud_error(payload)
    return payload


def upload_file(config: PCloudConfig, *, filename: str, content: bytes, mime: str) -> int:
    if not config.enabled:
        raise RuntimeError("pCloud 尚未設定 PCLOUD_AUTH_TOKEN 與 PCLOUD_FOLDER_ID 或 PCLOUD_FOLDER_PATH")

    data: dict[str, str | int] = {
        "auth": config.auth_token or "",
        "filename": filename,
        "renameifexists": 1,
        "nopartial": 1,
    }
    if config.folder_id is not None:
        data["folderid"] = config.folder_id
    else:
        data["path"] = config.folder_path or ""

    payload = _request_json(
        "POST",
        f"{config.api_base}/uploadfile",
        data=data,
        files={"file": (filename, content, mime)},
    )
    fileids = payload.get("fileids") or []
    if not fileids:
        raise RuntimeError("pCloud 上傳成功但未回傳 fileid")
    return int(fileids[0])


def create_file_public_link(config: PCloudConfig, file_id: int) -> str | None:
    if not config.create_public_link:
        return None

    payload = _request_json(
        "GET",
        f"{config.api_base}/getfilepublink",
        params={"auth": config.auth_token, "fileid": file_id, "shortlink": 1},
    )
    shortlink = payload.get("shortlink")
    if isinstance(shortlink, str) and shortlink:
        return shortlink
    code = payload.get("code")
    if isinstance(code, str) and code:
        return f"https://u.pcloud.link/publink/show?code={code}"
    return None


def create_direct_download_link(config: PCloudConfig, file_id: int, mime: str) -> str | None:
    if not config.use_direct_download_link:
        return None

    payload = _request_json(
        "GET",
        f"{config.api_base}/getfilelink",
        params={"auth": config.auth_token, "fileid": file_id, "contenttype": mime, "skipfilename": 1},
    )
    hosts = payload.get("hosts") or []
    path = payload.get("path")
    if not hosts or not path:
        return None
    return f"https://{hosts[0]}{path}"


def upload_data_url_to_pcloud(config: PCloudConfig, *, data_url: str, article_id: int, image_id: int) -> str:
    content, mime = decode_data_url(data_url)
    filename = build_image_filename(article_id=article_id, image_id=image_id, mime=mime)
    file_id = upload_file(config, filename=filename, content=content, mime=mime)
    return (
        create_direct_download_link(config, file_id, mime)
        or create_file_public_link(config, file_id)
        or data_url
    )
