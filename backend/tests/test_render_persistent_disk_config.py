from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
RENDER_YAML = REPO_ROOT / "render.yaml"


def test_render_blueprint_uses_free_web_service_with_external_database():
    content = RENDER_YAML.read_text(encoding="utf-8")

    assert "plan: free" in content
    assert "disk:" not in content
    assert "DATABASE_URL" in content
    database_index = content.index("key: DATABASE_URL")
    database_block = content[database_index : database_index + 80]
    assert "sync: false" in database_block
    assert "sqlite:" not in database_block
    assert "fromDatabase:" not in content


def test_render_blueprint_keeps_sensitive_secrets_manual_and_stable():
    content = RENDER_YAML.read_text(encoding="utf-8")

    for key in ["JWT_SECRET_KEY", "ENCRYPTION_SECRET", "ADMIN_API_KEY"]:
        key_index = content.index(f"key: {key}")
        block = content[key_index : key_index + 120]
        assert "sync: false" in block
        assert "generateValue" not in block
