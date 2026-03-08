import re
from typing import Any
from urllib.parse import quote
from uuid import uuid4

STYLE_PRESETS: dict[str, dict[str, str]] = {
    "blog_cover": {
        "label": "部落客封面圖",
        "description": "清新、留白、生活感，適合作為首圖",
        "prompt_suffix": "clean composition, soft daylight, modern blog cover, minimal and elegant",
    },
    "expert_infographic": {
        "label": "專家解析資訊圖",
        "description": "專業、圖解、重點清楚",
        "prompt_suffix": "professional infographic style, clear structure, data-driven visual",
    },
    "emotional_story": {
        "label": "情感敘事插畫",
        "description": "溫暖敘事、情緒光影",
        "prompt_suffix": "emotional storytelling illustration, cinematic lighting, warm tone",
    },
    "knowledge_diagram": {
        "label": "知識圖解",
        "description": "教學導向、框架清晰",
        "prompt_suffix": "educational diagram style, clear sections, concept visualization",
    },
}


def parse_size(size: str) -> tuple[int, int]:
    try:
        width, height = size.split("x")
        return int(width), int(height)
    except Exception:
        return 1536, 1024


def has_cjk(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", text))


def detect_zh_text_intent(source_text: str, keywords_csv: str) -> bool:
    lowered = source_text.lower()
    keywords = [kw.strip().lower() for kw in keywords_csv.split(",") if kw.strip()]
    return any(kw in lowered for kw in keywords)


def resolve_provider(
    image_provider_mode: str,
    default_provider: str,
    force_nano_banana_for_zh_text: bool,
    need_text_overlay: bool,
    text_language: str,
    text_content: str,
    source_text: str,
    keywords_csv: str,
) -> str:
    mode = image_provider_mode.lower()
    if mode != "auto":
        return mode

    zh_signal = (
        text_language.lower().startswith("zh")
        or has_cjk(text_content)
        or detect_zh_text_intent(source_text, keywords_csv)
    )
    if force_nano_banana_for_zh_text and (need_text_overlay and zh_signal):
        return "nano_banana"

    return default_provider.lower()


def resolve_model(provider: str, nano_banana_model: str, openai_image_model: str) -> str:
    if provider == "nano_banana":
        return nano_banana_model
    return openai_image_model


def build_image_prompt(
    article_topic: str,
    article_outline: str,
    style_preset: str,
    custom_prompt: str | None,
    need_text_overlay: bool,
    text_content: str | None,
) -> str:
    preset = STYLE_PRESETS.get(style_preset, STYLE_PRESETS["blog_cover"])
    text_instruction = (
        f"Include readable text: {text_content.strip()}"
        if need_text_overlay and text_content
        else "No text overlay"
    )

    return (
        f"Topic: {article_topic}\n"
        f"Outline: {article_outline}\n"
        f"Style: {preset['label']}\n"
        f"Style detail: {preset['prompt_suffix']}\n"
        f"Extra instruction: {(custom_prompt or '').strip() or 'none'}\n"
        f"Text overlay: {text_instruction}\n"
        "Output should be commercial-quality cover image."
    )


def build_placeholder_image_url(width: int, height: int, provider: str, style_preset: str) -> str:
    tag = quote(f"{provider} | {style_preset} | {uuid4().hex[:6]}")
    return f"https://placehold.co/{width}x{height}/E8F9F8/0D7F7A?text={tag}"


def list_style_presets() -> list[dict[str, str]]:
    return [
        {
            "key": key,
            "label": value["label"],
            "description": value["description"],
        }
        for key, value in STYLE_PRESETS.items()
    ]


def build_source_text_for_provider_decision(
    article_topic: str,
    article_outline: str,
    custom_prompt: str | None,
    text_content: str | None,
) -> str:
    return "\n".join(
        [
            article_topic,
            article_outline,
            custom_prompt or "",
            text_content or "",
        ]
    )


def generate_image_plan(
    *,
    article_topic: str,
    article_outline: str,
    style_preset: str,
    custom_prompt: str | None,
    need_text_overlay: bool,
    text_language: str,
    text_content: str | None,
    num_images: int,
    setting: Any,
) -> list[dict[str, Any]]:
    width, height = parse_size(setting.default_size)
    source_text = build_source_text_for_provider_decision(
        article_topic,
        article_outline,
        custom_prompt,
        text_content,
    )

    provider = resolve_provider(
        image_provider_mode=setting.image_provider_mode,
        default_provider=setting.default_provider,
        force_nano_banana_for_zh_text=setting.force_nano_banana_for_zh_text,
        need_text_overlay=need_text_overlay,
        text_language=text_language,
        text_content=text_content or "",
        source_text=source_text,
        keywords_csv=setting.zh_text_detection_keywords,
    )
    model = resolve_model(provider, setting.nano_banana_model, setting.openai_image_model)

    prompt = build_image_prompt(
        article_topic=article_topic,
        article_outline=article_outline,
        style_preset=style_preset,
        custom_prompt=custom_prompt,
        need_text_overlay=need_text_overlay,
        text_content=text_content,
    )

    plans: list[dict[str, Any]] = []
    for _ in range(num_images):
        plans.append(
            {
                "provider": provider,
                "model": model,
                "prompt": prompt,
                "image_url": build_placeholder_image_url(width, height, provider, style_preset),
                "width": width,
                "height": height,
                "text_language": text_language,
                "text_content": text_content,
            }
        )

    return plans
