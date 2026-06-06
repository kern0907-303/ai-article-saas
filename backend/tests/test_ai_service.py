from app.services.ai_service import build_article_prompt, sanitize_generated_article


def test_build_article_prompt_prohibits_markdown_and_section_labels():
    prompt = build_article_prompt("熟齡健康", "免疫力與日常保養", [], None)

    assert "不要使用 Markdown" in prompt
    assert "不要輸出 `#`" in prompt
    assert "不要出現「引言」" in prompt
    assert "「結論：」" in prompt


def test_sanitize_generated_article_removes_markdown_and_section_labels():
    content = """
## 熟齡健康指南

引言：
**免疫力** 不是一天建立的。

內容
1. 睡眠要穩定

結論：每天一點調整，比一次大改更容易持續。
"""

    sanitized = sanitize_generated_article(content)

    assert "##" not in sanitized
    assert "**" not in sanitized
    assert "引言" not in sanitized
    assert "內容" not in sanitized
    assert "結論：" not in sanitized
    assert "免疫力 不是一天建立的。" in sanitized
    assert "睡眠要穩定" in sanitized
    assert "每天一點調整" in sanitized
