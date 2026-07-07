from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api import public_articles
from app.core.database import Base
from app.models.article import Article


def make_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)()


def add_article(db, **overrides) -> Article:
    values = {
        "user_id": "1",
        "workspace_id": None,
        "topic": "公開文章",
        "outline": "公開摘要",
        "content": "公開內容",
        "generation_model": "gpt-test",
        "generation_status": "generated",
        "published_to_website": True,
        "published_to_social": False,
        "selected_file_ids": "10,11",
        "knowledge_categories": "writing_skill",
        "publish_website_result": "internal",
    }
    values.update(overrides)
    record = Article(**values)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def test_public_article_feed_is_scoped_to_owner_and_published_content_only():
    db = make_session()
    visible = add_article(db, user_id="1", topic="A")
    add_article(db, user_id="2", topic="Other user")
    add_article(db, user_id="1", topic="Draft", published_to_website=False)
    add_article(db, user_id="1", topic="No content", content=None)

    rows = public_articles.list_public_articles(owner_id="1", db=db)

    assert [row.id for row in rows] == [visible.id]
    assert rows[0].topic == "A"


def test_public_article_feed_can_filter_by_workspace():
    db = make_session()
    workspace_article = add_article(db, workspace_id=7, topic="Workspace")
    add_article(db, workspace_id=8, topic="Other workspace")

    rows = public_articles.list_public_articles(owner_id="1", workspace_id=7, db=db)

    assert [row.id for row in rows] == [workspace_article.id]


def test_public_article_schema_does_not_expose_private_generation_fields():
    db = make_session()
    record = add_article(db)

    rows = public_articles.list_public_articles(owner_id="1", db=db)
    payload = rows[0].model_dump()

    assert payload["id"] == record.id
    assert payload["content"] == "公開內容"
    assert "user_id" not in payload
    assert "selected_file_ids" not in payload
    assert "knowledge_categories" not in payload
    assert "generation_model" not in payload
