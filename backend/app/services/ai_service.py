from openai import OpenAI

from app.models.settings import Setting


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


def generate_article_with_openai(
    user_setting: Setting,
    topic: str,
    outline: str,
    contexts: list[str],
    model: str,
    user_prompt: str | None = None,
) -> str:
    if not user_setting.openai_api_key:
        raise ValueError("尚未設定 OpenAI API Key，無法生成文章。")

    prompt = build_article_prompt(topic, outline, contexts, user_prompt)
    client = OpenAI(api_key=user_setting.openai_api_key)
    response = client.responses.create(
        model=model,
        input=prompt,
    )
    return response.output_text.strip()


def expand_prompt_with_openai(
    user_setting: Setting,
    requirement: str,
    model: str,
) -> str:
    if not user_setting.openai_api_key:
        raise ValueError("尚未設定 OpenAI API Key，無法生成提示詞。")

    input_prompt = f"""
你是一位提示詞工程師。請把使用者的一句話需求，擴寫成可直接交給文章生成模型使用的高品質結構化提示詞。

使用者需求：{requirement}

輸出要求：
1. 使用繁體中文。
2. 包含：角色設定、目標讀者、語氣風格、結構要求、限制條件、輸出格式。
3. 請直接輸出完整提示詞，不要加前言。
""".strip()

    client = OpenAI(api_key=user_setting.openai_api_key)
    response = client.responses.create(
        model=model,
        input=input_prompt,
    )
    return response.output_text.strip()
