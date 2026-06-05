import base64

from app.services import pcloud_service
from app.services.pcloud_service import PCloudConfig, decode_data_url, upload_data_url_to_pcloud


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeClient:
    requests = []

    def __init__(self, timeout=None):
        self.timeout = timeout

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def request(self, method, url, **kwargs):
        self.requests.append({"method": method, "url": url, **kwargs})
        if url.endswith("/uploadfile"):
            return FakeResponse({"result": 0, "fileids": [321]})
        if url.endswith("/getfilelink"):
            return FakeResponse({"result": 0, "hosts": ["c1.pcloud.com"], "path": "/hash/generated.png"})
        if url.endswith("/getfilepublink"):
            return FakeResponse({"result": 0, "shortlink": "https://pc.cd/example"})
        raise AssertionError(f"unexpected url: {url}")


def test_decode_data_url_returns_image_bytes_and_mime():
    raw = b"fake-png"
    data_url = f"data:image/png;base64,{base64.b64encode(raw).decode()}"

    content, mime = decode_data_url(data_url)

    assert content == raw
    assert mime == "image/png"


def test_upload_data_url_to_pcloud_uploads_file_and_returns_direct_link(monkeypatch):
    FakeClient.requests = []
    monkeypatch.setattr(pcloud_service.httpx, "Client", FakeClient)
    data_url = f"data:image/png;base64,{base64.b64encode(b'image-bytes').decode()}"

    url = upload_data_url_to_pcloud(
        PCloudConfig(auth_token="token", folder_id=123, api_host="api.pcloud.com"),
        data_url=data_url,
        article_id=7,
        image_id=9,
    )

    assert url == "https://c1.pcloud.com/hash/generated.png"
    upload_request = FakeClient.requests[0]
    assert upload_request["url"] == "https://api.pcloud.com/uploadfile"
    assert upload_request["data"]["auth"] == "token"
    assert upload_request["data"]["folderid"] == 123
    assert upload_request["files"]["file"][0].startswith("article-7-image-9-")


def test_upload_data_url_to_pcloud_can_return_public_share_link(monkeypatch):
    FakeClient.requests = []
    monkeypatch.setattr(pcloud_service.httpx, "Client", FakeClient)
    data_url = f"data:image/png;base64,{base64.b64encode(b'image-bytes').decode()}"

    url = upload_data_url_to_pcloud(
        PCloudConfig(auth_token="token", folder_path="/AI Images", use_direct_download_link=False),
        data_url=data_url,
        article_id=7,
        image_id=9,
    )

    assert url == "https://pc.cd/example"
    public_request = FakeClient.requests[1]
    assert public_request["url"] == "https://api.pcloud.com/getfilepublink"
    assert public_request["params"]["fileid"] == 321


def test_upload_data_url_to_pcloud_saves_to_local_public_folder(tmp_path):
    data_url = f"data:image/png;base64,{base64.b64encode(b'image-bytes').decode()}"

    url = upload_data_url_to_pcloud(
        PCloudConfig(
            auth_token=None,
            public_folder_path=str(tmp_path),
            public_base_url="https://public.example.com/article",
        ),
        data_url=data_url,
        article_id=7,
        image_id=9,
    )

    saved_files = list(tmp_path.iterdir())
    assert len(saved_files) == 1
    assert saved_files[0].read_bytes() == b"image-bytes"
    assert url.startswith("https://public.example.com/article/article-7-image-9-")
