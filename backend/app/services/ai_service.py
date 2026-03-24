import httpx
import re

from app.models.settings import Setting

SUPPORTED_TEXT_PROVIDERS = {"openai", "anthropic", "gemini", "github"}
PROVIDER_CONNECT_TIMEOUT_SECONDS = 15
PROVIDER_READ_TIMEOUT_SECONDS = 180
PROVIDER_WRITE_TIMEOUT_SECONDS = 30
PROVIDER_POOL_TIMEOUT_SECONDS = 30
PROVIDER_MAX_RETRIES = 2


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
4. 請輸出純文字格式，不要使用 Markdown。
5. 不要輸出 `#`、`##`、`###`、`**`、`__` 這類 Markdown 符號。
6. 標題與小節請直接用一般文字換行呈現。
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
    message = str(err).lower()
    if "timed out" in message or "timeout" in message:
        return RuntimeError(f"{provider_label} 回應逾時，請稍後再試，或改用較快的模型")
    return RuntimeError(str(err))


def _provider_timeout() -> httpx.Timeout:
    return httpx.Timeout(
        connect=PROVIDER_CONNECT_TIMEOUT_SECONDS,
        read=PROVIDER_READ_TIMEOUT_SECONDS,
        write=PROVIDER_WRITE_TIMEOUT_SECONDS,
        pool=PROVIDER_POOL_TIMEOUT_SECONDS,
    )


def _is_retryable_response(response: httpx.Response) -> bool:
    return response.status_code in {408, 429, 500, 502, 503, 504}


def _post_with_retry(
    *,
    provider_label: str,
    url: str,
    headers: dict[str, str],
    json: dict,
    params: dict[str, str] | None = None,
) -> httpx.Response:
    last_error: Exception | None = None

    for attempt in range(PROVIDER_MAX_RETRIES):
        try:
            response = httpx.post(
                url,
                headers=headers,
                json=json,
                params=params,
                timeout=_provider_timeout(),
            )
        except Exception as err:
            last_error = err
            if attempt == PROVIDER_MAX_RETRIES - 1:
                raise _provider_request_error(provider_label, err) from err
            continue

        if response.is_error and _is_retryable_response(response) and attempt < PROVIDER_MAX_RETRIES - 1:
            continue

        return response

    if last_error is not None:
        raise _provider_request_error(provider_label, last_error) from last_error
    raise RuntimeError(f"{provider_label} 暫時無法取得回應")


def _openai_generate(*, api_key: str, model: str, prompt: str) -> str:
    response = _post_with_retry(
        provider_label="OpenAI",
        url="https://api.openai.com/v1/responses",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "input": prompt,
        },
    )
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
    response = _post_with_retry(
        provider_label="Anthropic",
        url="https://api.anthropic.com/v1/messages",
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
    )
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
    response = _post_with_retry(
        provider_label="Gemini",
        url=f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
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
    )
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
    response = _post_with_retry(
        provider_label="GitHub Models",
        url="https://models.github.ai/inference/chat/completions",
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
    )
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
    generated = generate_text_with_provider(provider=provider, api_key=api_key, model=model, prompt=prompt)
    return sanitize_generated_article(generated)


def expand_prompt(
    user_setting: Setting,
    requirement: str,
    model: str,
) -> str:
    provider = normalize_text_provider(user_setting.ai_provider)
    api_key = _require_provider_key(user_setting, provider)
    prompt = build_prompt_expansion_prompt(requirement)
    return generate_text_with_provider(provider=provider, api_key=api_key, model=model, prompt=prompt)


def sanitize_generated_article(content: str) -> str:
    sanitized = content.replace("**", "").replace("__", "")
    sanitized = re.sub(r"(?m)^\s*#{1,6}\s*", "", sanitized)
    sanitized = re.sub(r"\n{3,}", "\n\n", sanitized)
    return sanitized.strip()
