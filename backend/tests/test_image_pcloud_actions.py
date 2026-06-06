from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api import images
from app.services.pcloud_service import PCloudConfig


def test_ensure_public_image_link_returns_existing_public_url():
    record = SimpleNamespace(id=5, image_url="https://public.example.com/image.png", generation_error="old")

    assert images._ensure_public_image_link(record, article_id=9) == "https://public.example.com/image.png"


def test_ensure_public_image_link_requires_pcloud_for_data_url(monkeypatch):
    record = SimpleNamespace(id=5, image_url="data:image/png;base64,abc", generation_error=None)
    monkeypatch.setattr(images, "_get_pcloud_config", lambda: PCloudConfig(auth_token=None))

    with pytest.raises(HTTPException, match="尚未設定 pCloud"):
        images._ensure_public_image_link(record, article_id=9)


def test_ensure_public_image_link_uploads_data_url(monkeypatch):
    record = SimpleNamespace(id=5, image_url="data:image/png;base64,abc", generation_error="old")
    monkeypatch.setattr(images, "_get_pcloud_config", lambda: PCloudConfig(auth_token="token", folder_id=123))
    monkeypatch.setattr(
        images,
        "upload_data_url_to_pcloud",
        lambda config, data_url, article_id, image_id: "https://public.example.com/generated.png",
    )

    url = images._ensure_public_image_link(record, article_id=9)

    assert url == "https://public.example.com/generated.png"
    assert record.image_url == "https://public.example.com/generated.png"
    assert record.generation_error is None
