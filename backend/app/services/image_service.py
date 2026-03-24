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


def _safe_svg_text(text: str, fallback: str) -> str:
    cleaned = re.sub(r"\s+", " ", (text or "").strip())
    cleaned = cleaned[:48]
    return cleaned or fallback


def _style_palette(style_preset: str) -> dict[str, str]:
    palettes = {
        "blog_cover": {
            "start": "#DBF5F2",
            "end": "#BDE6FF",
            "accent": "#0F766E",
            "accent_soft": "#7DD3C7",
            "panel": "#FFFFFF",
            "panel_opacity": "0.78",
        },
        "expert_infographic": {
            "start": "#DDE7FF",
            "end": "#C6F3EA",
            "accent": "#1D4ED8",
            "accent_soft": "#60A5FA",
            "panel": "#F8FAFC",
            "panel_opacity": "0.82",
        },
        "emotional_story": {
            "start": "#FFE2DB",
            "end": "#FFEEC9",
            "accent": "#BE4B49",
            "accent_soft": "#F59E8B",
            "panel": "#FFF9F4",
            "panel_opacity": "0.8",
        },
        "knowledge_diagram": {
            "start": "#E1F0FF",
            "end": "#DDF8E6",
            "accent": "#2563EB",
            "accent_soft": "#7CC5FF",
            "panel": "#F8FAFC",
            "panel_opacity": "0.82",
        },
    }
    return palettes.get(style_preset, palettes["blog_cover"])


def build_placeholder_image_url(
    width: int,
    height: int,
    provider: str,
    style_preset: str,
    article_topic: str,
    text_content: str | None,
) -> str:
    palette = _style_palette(style_preset)
    label = f"{provider} / {style_preset} / {uuid4().hex[:6]}"
    title = _safe_svg_text(text_content or article_topic, "AI 預覽封面")
    subtitle = _safe_svg_text(article_topic, "Article Cover Preview")
    svg = f"""
    <svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
      <defs>
        <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stop-color="{palette['start']}" />
          <stop offset="100%" stop-color="{palette['end']}" />
        </linearGradient>
      </defs>
      <rect width="100%" height="100%" fill="url(#bg)" rx="24" ry="24" />
      <circle cx="{width * 0.82}" cy="{height * 0.18}" r="{max(40, min(width, height) * 0.08)}" fill="{palette['accent_soft']}" opacity="0.9" />
      <circle cx="{width * 0.14}" cy="{height * 0.8}" r="{max(56, min(width, height) * 0.11)}" fill="{palette['accent_soft']}" opacity="0.5" />
      <rect x="{width * 0.07}" y="{height * 0.12}" width="{width * 0.86}" height="{height * 0.7}" rx="28" fill="{palette['panel']}" opacity="{palette['panel_opacity']}" />
      <rect x="{width * 0.11}" y="{height * 0.2}" width="{width * 0.34}" height="{height * 0.26}" rx="22" fill="{palette['accent']}" opacity="0.9" />
      <rect x="{width * 0.49}" y="{height * 0.2}" width="{width * 0.36}" height="{height * 0.06}" rx="14" fill="{palette['accent_soft']}" opacity="0.95" />
      <rect x="{width * 0.49}" y="{height * 0.3}" width="{width * 0.26}" height="{height * 0.045}" rx="12" fill="{palette['accent_soft']}" opacity="0.7" />
      <rect x="{width * 0.49}" y="{height * 0.38}" width="{width * 0.3}" height="{height * 0.045}" rx="12" fill="{palette['accent_soft']}" opacity="0.55" />
      <rect x="{width * 0.11}" y="{height * 0.54}" width="{width * 0.74}" height="{height * 0.11}" rx="18" fill="{palette['panel']}" opacity="0.92" />
      <text x="11%" y="15%" fill="{palette['accent']}" font-family="Arial, sans-serif" font-size="{max(26, width // 28)}" font-weight="700">
        Mock Preview
      </text>
      <text x="11%" y="60%" fill="{palette['accent']}" font-family="Arial, sans-serif" font-size="{max(34, width // 22)}" font-weight="700">
        {title}
      </text>
      <text x="11%" y="69%" fill="#355C68" font-family="Arial, sans-serif" font-size="{max(18, width // 42)}">
        {subtitle}
      </text>
      <text x="11%" y="78%" fill="#54717A" font-family="Arial, sans-serif" font-size="{max(16, width // 48)}">
        {label}
      </text>
    </svg>
    """.strip()
    return f"data:image/svg+xml;charset=UTF-8,{quote(svg)}"


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
                "image_url": build_placeholder_image_url(
                    width,
                    height,
                    provider,
                    style_preset,
                    article_topic,
                    text_content,
                ),
                "width": width,
                "height": height,
                "text_language": text_language,
                "text_content": text_content,
            }
        )

    return plans
