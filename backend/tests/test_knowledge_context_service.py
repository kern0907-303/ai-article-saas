from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.knowledge_file import KnowledgeFile
from app.services.knowledge_context_service import (
    build_generation_contexts,
    rank_knowledge_chunks,
    split_knowledge_text,
)


def make_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)()


def add_file(
    db,
    tmp_path: Path,
    *,
    user_id: str = "1",
    file_name: str,
    text: str,
    is_default_reference: bool = True,
    is_active: bool = True,
) -> KnowledgeFile:
    stored_path = tmp_path / file_name
    stored_path.write_text(text, encoding="utf-8")
    record = KnowledgeFile(
        user_id=user_id,
        file_name=file_name,
        stored_path=str(stored_path),
        content_type="text/markdown",
        file_size=len(text.encode("utf-8")),
        extracted_text_preview=text[:500],
        is_default_reference=is_default_reference,
        is_active=is_active,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def test_build_generation_contexts_uses_default_references_when_no_ids(tmp_path):
    db = make_session()
    default_file = add_file(
        db,
        tmp_path,
        file_name="writing-skill.md",
        text="# 寫作 Skill\n\n## 滑梯效應\n每一句都要讓人想讀下一句。",
        is_default_reference=True,
    )
    add_file(
        db,
        tmp_path,
        file_name="archive.md",
        text="# 舊資料\n\n這份不是預設參考。",
        is_default_reference=False,
    )

    contexts, used_ids = build_generation_contexts(
        db,
        user_id="1",
        selected_file_ids=[],
        topic="滑梯效應文章",
        outline="寫一篇廣告文案教學",
        user_prompt="請使用寫作 skill",
    )

    assert used_ids == [default_file.id]
    joined_context = "\n\n".join(contexts)
    assert "writing-skill.md" in joined_context
    assert "滑梯效應" in joined_context
    assert "舊資料" not in joined_context


def test_markdown_chunks_are_ranked_by_writing_request():
    text = """---
name: advertising-psychology
description: 廣告文案與心理觸發器
---

# 廣告心理學

## 社會認同
用他人的選擇降低決策焦慮。

## 滑梯效應
標題推動第一句，第一句推動第二句，讓讀者一路讀到 CTA。

## 稀缺性
真實限制能降低拖延。
"""

    chunks = split_knowledge_text("advertising-psychology.md", text, max_chunk_chars=120)
    ranked = rank_knowledge_chunks(chunks, query="我要寫滑梯效應 CTA 文案", max_chars=500)

    assert len(chunks) >= 3
    assert ranked[0].startswith("[參考資料: advertising-psychology.md")
    assert "滑梯效應" in ranked[0]
    assert "CTA" in ranked[0]


def test_rank_knowledge_chunks_respects_character_budget():
    chunks = split_knowledge_text(
        "skill.md",
        "# Skill\n\n## ABL 調頻\n" + ("調頻 " * 200) + "\n\n## 其他\n" + ("其他 " * 200),
        max_chunk_chars=1000,
    )

    ranked = rank_knowledge_chunks(chunks, query="ABL 調頻", max_chars=180)

    assert ranked
    assert sum(len(item) for item in ranked) <= 180
    assert "ABL" in ranked[0]
