from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
RENDER_YAML = REPO_ROOT / "render.yaml"


def test_render_blueprint_uses_persistent_disk_sqlite_storage():
    content = RENDER_YAML.read_text(encoding="utf-8")

    assert "disk:" in content
    assert "mountPath: /var/data" in content
    assert "DATABASE_URL" in content
    assert "sqlite:////var/data/ai-article-saas/app.db" in content
    assert "STORAGE_DIR" in content
    assert "/var/data/ai-article-saas/storage" in content
    assert "fromDatabase:" not in content


def test_render_blueprint_keeps_sensitive_secrets_manual_and_stable():
    content = RENDER_YAML.read_text(encoding="utf-8")

    for key in ["JWT_SECRET_KEY", "ENCRYPTION_SECRET", "ADMIN_API_KEY"]:
        key_index = content.index(f"key: {key}")
        block = content[key_index : key_index + 120]
        assert "sync: false" in block
        assert "generateValue" not in block
