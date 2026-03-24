import httpx

from app.models.settings import Setting

SUPPORTED_TEXT_PROVIDERS = {"openai", "anthropic", "gemini", "github"}
PROVIDER_TIMEOUT_SECONDS = 75


def build_article_prompt(topic: str, outline: str, contexts: list[str], user_prompt: str | None = None) -> str:
    context_text = "\n\n".join(contexts) if contexts else "（未提供參考檔案）"
    custom_instruction = user_prompt.strip() if user_prompt else ""

    return f"""
你是一位專業繁體中文內容編輯。請依照以下資訊產生一篇可直接發布的文章：

主題：{topic}
大綱：
{outline}

提示詞要求：
{custom_instruction or '（未提供額外提示詞）'}

參考資料：
{context_text}

請遵守：
1. 全文使用繁體中文。
2. 內容結構完整，需有標題、小節標題、結論。
3. 避免捏造無根據數據，如引用請以中性描述處理。
4. 請輸出 Markdown 格式。
""".strip()


def build_prompt_expansion_prompt(requirement: str) -> str:
    return f"""
你是一位提示詞工程師。請把使用者的一句話需求，擴寫成可直接交給文章生成模型使用的高品質結構化提示詞。

使用者需求：{requirement}

輸出要求：
1. 使用繁體中文。
2. 包含：角色設定、目標讀者、語氣風格、結構要求、限制條件、輸出格式。
3. 請直接輸出完整提示詞，不要加前言。
""".strip()


def normalize_text_provider(provider: str | None) -> str:
    normalized = (provider or "openai").strip().lower()
    if normalized not in SUPPORTED_TEXT_PROVIDERS:
        raise ValueError(f"目前不支援的文字模型供應商：{provider}")
    return normalized


def resolve_text_provider_api_key(setting: Setting, provider: str) -> str | None:
    if provider == "openai":
        return setting.openai_api_key
    if provider == "anthropic":
        return setting.anthropic_api_key
    if provider == "gemini":
        return setting.gemini_api_key
    if provider == "github":
        return setting.github_api_key
    return None


def _extract_error_message(response: httpx.Response) -> str:
    payload = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict) and isinstance(error.get("message"), str):
            return error["message"]
        if isinstance(error, str):
            return error
        if isinstance(payload.get("message"), str):
            return payload["message"]
    return response.text.strip() or f"HTTP {response.status_code}"


def _provider_request_error(provider_label: str, err: Exception) -> RuntimeError:
    if isinstance(err, httpx.TimeoutException):
        return RuntimeError(f"{provider_label} 回應逾時，請稍後再試，或改用較快的模型")
    if isinstance(err, httpx.HTTPError):
        return RuntimeError(f"{provider_label} 連線失敗，請稍後再試")
    return RuntimeError(str(err))


def _openai_generate(*, api_key: str, model: str, prompt: str) -> str:
    try:
        response = httpx.post(
            "https://api.openai.com/v1/responses",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "input": prompt,
            },
            timeout=PROVIDER_TIMEOUT_SECONDS,
        )
    except Exception as err:
        raise _provider_request_error("OpenAI", err) from err
    if response.is_error:
        raise RuntimeError(_extract_error_message(response))

    data = response.json()
    output_text = data.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    for item in data.get("output", []):
        if not isinstance(item, dict):
            continue
        for content in item.get("content", []):
            if isinstance(content, dict) and content.get("type") == "output_text":
                text = content.get("text")
                if isinstance(text, str) and text.strip():
                    return text.strip()

    raise RuntimeError("OpenAI 未回傳可用文字內容")


def _anthropic_generate(*, api_key: str, model: str, prompt: str) -> str:
    try:
        response = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": model,
                "max_tokens": 4096,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=PROVIDER_TIMEOUT_SECONDS,
        )
    except Exception as err:
        raise _provider_request_error("Anthropic", err) from err
    if response.is_error:
        raise RuntimeError(_extract_error_message(response))

    data = response.json()
    for item in data.get("content", []):
        if isinstance(item, dict) and item.get("type") == "text":
            text = item.get("text")
            if isinstance(text, str) and text.strip():
                return text.strip()

    raise RuntimeError("Anthropic 未回傳可用文字內容")


def _gemini_generate(*, api_key: str, model: str, prompt: str) -> str:
    try:
        response = httpx.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            params={"key": api_key},
            headers={"Content-Type": "application/json"},
            json={
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": prompt}],
                    }
                ],
            },
            timeout=PROVIDER_TIMEOUT_SECONDS,
        )
    except Exception as err:
        raise _provider_request_error("Gemini", err) from err
    if response.is_error:
        raise RuntimeError(_extract_error_message(response))

    data = response.json()
    for candidate in data.get("candidates", []):
        if not isinstance(candidate, dict):
            continue
        content = candidate.get("content", {})
        if not isinstance(content, dict):
            continue
        for part in content.get("parts", []):
            if isinstance(part, dict):
                text = part.get("text")
                if isinstance(text, str) and text.strip():
                    return text.strip()

    raise RuntimeError("Gemini 未回傳可用文字內容")


def _github_generate(*, api_key: str, model: str, prompt: str) -> str:
    try:
        response = httpx.post(
            "https://models.github.ai/inference/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
            },
            timeout=PROVIDER_TIMEOUT_SECONDS,
        )
    except Exception as err:
        raise _provider_request_error("GitHub Models", err) from err
    if response.is_error:
        raise RuntimeError(_extract_error_message(response))

    data = response.json()
    for choice in data.get("choices", []):
        if not isinstance(choice, dict):
            continue
        message = choice.get("message", {})
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            return content.strip()

    raise RuntimeError("GitHub Models 未回傳可用文字內容")


def generate_text_with_provider(*, provider: str, api_key: str, model: str, prompt: str) -> str:
    normalized_provider = normalize_text_provider(provider)
    if normalized_provider == "openai":
        return _openai_generate(api_key=api_key, model=model, prompt=prompt)
    if normalized_provider == "anthropic":
        return _anthropic_generate(api_key=api_key, model=model, prompt=prompt)
    if normalized_provider == "gemini":
        return _gemini_generate(api_key=api_key, model=model, prompt=prompt)
    if normalized_provider == "github":
        return _github_generate(api_key=api_key, model=model, prompt=prompt)
    raise ValueError(f"目前不支援的文字模型供應商：{provider}")


def _require_provider_key(user_setting: Setting, provider: str) -> str:
    normalized_provider = normalize_text_provider(provider)
    api_key = resolve_text_provider_api_key(user_setting, normalized_provider)
    if api_key:
        return api_key

    provider_label = {
        "openai": "OpenAI",
        "anthropic": "Anthropic",
        "gemini": "Gemini",
        "github": "GitHub Models",
    }[normalized_provider]
    raise ValueError(f"尚未設定 {provider_label} API Key，無法使用目前選擇的供應商。")


def generate_article(
    user_setting: Setting,
    topic: str,
    outline: str,
    contexts: list[str],
    model: str,
    user_prompt: str | None = None,
) -> str:
    provider = normalize_text_provider(user_setting.ai_provider)
    api_key = _require_provider_key(user_setting, provider)
    prompt = build_article_prompt(topic, outline, contexts, user_prompt)
    return generate_text_with_provider(provider=provider, api_key=api_key, model=model, prompt=prompt)


def expand_prompt(
    user_setting: Setting,
    requirement: str,
    model: str,
) -> str:
    provider = normalize_text_provider(user_setting.ai_provider)
    api_key = _require_provider_key(user_setting, provider)
    prompt = build_prompt_expansion_prompt(requirement)
    return generate_text_with_provider(provider=provider, api_key=api_key, model=model, prompt=prompt)
