from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api import articles
from app.core.database import Base
from app.models.article import Article
from app.models.audit_log import AuditLog  # noqa: F401
from app.models.knowledge_file import KnowledgeFile
from app.models.settings import Setting


def make_session_factory():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def add_knowledge_file(db, tmp_path: Path, text: str) -> KnowledgeFile:
    stored_path = tmp_path / "writing-skill.md"
    stored_path.write_text(text, encoding="utf-8")
    record = KnowledgeFile(
        user_id="1",
        file_name="writing-skill.md",
        stored_path=str(stored_path),
        content_type="text/markdown",
        file_size=len(text.encode("utf-8")),
        extracted_text_preview=text[:500],
        is_active=True,
        is_default_reference=True,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def test_background_generation_uses_default_knowledge_files_when_none_selected(monkeypatch, tmp_path):
    SessionLocal = make_session_factory()
    db = SessionLocal()
    try:
        article = Article(
            user_id="1",
            topic="滑梯效應文章",
            outline="寫出讓讀者一路讀到 CTA 的文案",
            generation_model="gpt-5.4-mini",
            generation_status="queued",
        )
        db.add(article)
        db.add(
            Setting(
                user_id="1",
                ai_provider="openai",
                openai_api_key="sk-test",
                article_model="gpt-5.4-mini",
                prompt_model="gpt-5.4-mini",
                image_model="gpt-image-1.5",
            )
        )
        skill_file = add_knowledge_file(
            db,
            tmp_path,
            "# 寫作 Skill\n\n## 滑梯效應\n標題推動第一句，第一句推動第二句。",
        )
        article_id = article.id
        skill_file_id = skill_file.id
    finally:
        db.close()

    captured = {}

    def fake_generate_article(**kwargs):
        captured["contexts"] = kwargs["contexts"]
        return "生成完成"

    monkeypatch.setattr(articles, "SessionLocal", SessionLocal)
    monkeypatch.setattr(articles, "generate_article_with_provider", fake_generate_article)

    articles._generate_article_in_background(
        article_id=article_id,
        user_id="1",
        topic="滑梯效應文章",
        outline="寫出讓讀者一路讀到 CTA 的文案",
        selected_file_ids=[],
        prompt="請套用寫作 skill",
        model="gpt-5.4-mini",
    )

    db = SessionLocal()
    try:
        updated = db.query(Article).filter(Article.id == article_id).one()
        assert updated.generation_status == "generated"
        assert updated.content == "生成完成"
        assert updated.selected_file_ids == str(skill_file_id)
        assert captured["contexts"]
        assert "writing-skill.md" in captured["contexts"][0]
        assert "滑梯效應" in "\n".join(captured["contexts"])
    finally:
        db.close()
