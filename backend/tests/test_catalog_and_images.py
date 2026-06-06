from app.api.settings import MODEL_CATALOG
from app.services.image_service import (
    IMAGE_SIZE_PRESETS,
    build_openai_image_generate_params,
    parse_size,
    resolve_size,
    resolve_output_format,
    resolve_quality,
)


def test_model_catalog_uses_current_text_and_image_models():
    keys = {item.key for item in MODEL_CATALOG}

    assert "gpt-5.5" in keys
    assert "gpt-5.4-mini" in keys
    assert "claude-sonnet-4-6" in keys
    assert "claude-opus-4-8" in keys
    assert "gemini-3.5-flash" in keys
    assert "gemini-3.1-pro" in keys
    assert "gpt-image-1.5" in keys
    assert "gpt-image-1" in keys
    assert "nano-banana-pro" in keys


def test_social_image_size_presets_are_named_for_platforms():
    preset_keys = {preset["key"] for preset in IMAGE_SIZE_PRESETS}

    assert {
        "instagram_square",
        "instagram_story",
        "facebook_link",
        "x_landscape",
        "blog_cover",
    }.issubset(preset_keys)

    sizes = {preset["key"]: preset["size"] for preset in IMAGE_SIZE_PRESETS}
    assert parse_size(sizes["instagram_square"]) == (1080, 1080)
    assert parse_size(sizes["instagram_story"]) == (1080, 1920)
    assert parse_size(sizes["facebook_link"]) == (1200, 630)


def test_social_image_presets_resolve_to_gpt_image_supported_sizes():
    assert resolve_size("instagram_square", "1080x1080") == "1024x1024"
    assert resolve_size("instagram_story", "1080x1080") == "1024x1536"
    assert resolve_size("facebook_link", "1080x1080") == "1536x1024"
    assert resolve_size("1200x630", "1080x1080") == "1536x1024"


def test_openai_image_accepts_auto_quality_and_webp_format():
    assert resolve_quality("auto") == "auto"
    assert resolve_output_format("webp") == "webp"


def test_gpt_image_generation_params_do_not_send_response_format():
    params = build_openai_image_generate_params(
        model="gpt-image-1.5",
        prompt="cover image",
        size="1536x1024",
        quality="high",
        output_format="png",
        num_images=1,
    )

    assert params["output_format"] == "png"
    assert "response_format" not in params
