from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.knowledge_file import KnowledgeFile
from app.models.workspace import Workspace
from app.services.knowledge_context_service import build_generation_contexts


def make_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)()


def add_file(db, tmp_path: Path, *, user_id: str, workspace_id: int, category: str, file_name: str, text: str):
    path = tmp_path / file_name
    path.write_text(text, encoding="utf-8")
    record = KnowledgeFile(
        user_id=user_id,
        workspace_id=workspace_id,
        category=category,
        file_name=file_name,
        stored_path=str(path),
        content_type="text/markdown",
        file_size=len(text.encode("utf-8")),
        is_active=True,
        is_default_reference=True,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def test_generation_context_is_limited_to_workspace_and_categories(tmp_path):
    db = make_session()
    workspace_a = Workspace(user_id="1", name="Client A")
    workspace_b = Workspace(user_id="1", name="Client B")
    db.add_all([workspace_a, workspace_b])
    db.commit()
    db.refresh(workspace_a)
    db.refresh(workspace_b)
    used = add_file(
        db,
        tmp_path,
        user_id="1",
        workspace_id=workspace_a.id,
        category="writing_skill",
        file_name="client-a-skill.md",
        text="# Skill A\n\n## CTA\nClient A CTA rule.",
    )
    add_file(
        db,
        tmp_path,
        user_id="1",
        workspace_id=workspace_b.id,
        category="writing_skill",
        file_name="client-b-skill.md",
        text="# Skill B\n\nClient B private rule.",
    )
    add_file(
        db,
        tmp_path,
        user_id="1",
        workspace_id=workspace_a.id,
        category="forbidden_rules",
        file_name="client-a-forbidden.md",
        text="# Forbidden\n\nDo not use this category unless requested.",
    )

    contexts, used_ids = build_generation_contexts(
        db,
        user_id="1",
        selected_file_ids=[],
        topic="CTA article",
        outline="Write CTA",
        user_prompt="Use writing skill",
        workspace_id=workspace_a.id,
        categories=["writing_skill"],
    )

    joined = "\n".join(contexts)
    assert used_ids == [used.id]
    assert "client-a-skill.md" in joined
    assert "Client A CTA rule" in joined
    assert "Client B private rule" not in joined
    assert "Do not use this category" not in joined
