from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api import publish
from app.core.database import Base
from app.models.article import Article
from app.models.audit_log import AuditLog  # noqa: F401
from app.models.settings import Setting


def make_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)()


def test_publish_to_website_without_external_endpoint_marks_article_public():
    db = make_session()
    article = Article(
        user_id="1",
        topic="內建公開文章",
        outline="摘要",
        content="內容",
        generation_status="generated",
    )
    db.add(article)
    db.add(Setting(user_id="1", ai_provider="openai"))
    db.commit()
    db.refresh(article)

    response = publish.publish_to_website(article.id, db=db, user_id="1")

    db.refresh(article)
    assert response.success is True
    assert article.published_to_website is True
    assert article.publish_website_result == "已發布到公開文章資料庫"


def test_publish_to_website_requires_content_before_publication():
    db = make_session()
    article = Article(
        user_id="1",
        topic="空文章",
        outline="摘要",
        content=None,
        generation_status="queued",
    )
    db.add(article)
    db.add(Setting(user_id="1", ai_provider="openai"))
    db.commit()
    db.refresh(article)

    try:
        publish.publish_to_website(article.id, db=db, user_id="1")
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 400
        assert "文章內容" in str(getattr(exc, "detail", ""))
    else:  # pragma: no cover
        raise AssertionError("empty article should not be published")
