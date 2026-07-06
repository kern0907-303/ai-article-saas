from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api import knowledge_files, workspaces
from app.core.database import Base
from app.models.knowledge_file import KnowledgeFile
from app.models.workspace import Workspace
from app.schemas.workspace import WorkspaceCreateRequest, WorkspaceUpdateRequest


def make_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)()


def test_workspace_list_is_scoped_to_current_user():
    db = make_session()
    db.add(Workspace(user_id="1", name="Client A", is_default=True))
    db.add(Workspace(user_id="2", name="Other User Brand", is_default=True))
    db.commit()

    rows = workspaces.list_workspaces(db=db, user_id="1")

    assert [row.name for row in rows] == ["Client A"]


def test_setting_workspace_default_unsets_other_defaults():
    db = make_session()
    first = workspaces.create_workspace(
        WorkspaceCreateRequest(name="Brand 1", is_default=True),
        db=db,
        user_id="1",
    )
    second = workspaces.create_workspace(
        WorkspaceCreateRequest(name="Brand 2", is_default=True),
        db=db,
        user_id="1",
    )

    rows = workspaces.list_workspaces(db=db, user_id="1")

    assert first.id != second.id
    assert [(row.name, row.is_default) for row in rows] == [("Brand 2", True), ("Brand 1", False)]


def test_update_workspace_cannot_cross_user_boundary():
    db = make_session()
    other = Workspace(user_id="2", name="Other User Brand")
    db.add(other)
    db.commit()
    db.refresh(other)

    try:
        workspaces.update_workspace(
            other.id,
            WorkspaceUpdateRequest(name="Stolen"),
            db=db,
            user_id="1",
        )
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 404
    else:  # pragma: no cover - if this happens, user isolation is broken
        raise AssertionError("cross-user workspace update should fail")


def test_knowledge_files_filter_by_workspace_and_category():
    db = make_session()
    workspace_a = Workspace(user_id="1", name="Client A")
    workspace_b = Workspace(user_id="1", name="Client B")
    db.add_all([workspace_a, workspace_b])
    db.flush()
    db.add_all(
        [
            KnowledgeFile(
                user_id="1",
                workspace_id=workspace_a.id,
                category="writing_skill",
                file_name="skill-a.md",
                stored_path="/tmp/skill-a.md",
                file_size=10,
                is_active=True,
                is_default_reference=True,
            ),
            KnowledgeFile(
                user_id="1",
                workspace_id=workspace_b.id,
                category="writing_skill",
                file_name="skill-b.md",
                stored_path="/tmp/skill-b.md",
                file_size=10,
                is_active=True,
                is_default_reference=True,
            ),
            KnowledgeFile(
                user_id="2",
                workspace_id=workspace_a.id,
                category="writing_skill",
                file_name="other-user.md",
                stored_path="/tmp/other-user.md",
                file_size=10,
                is_active=True,
                is_default_reference=True,
            ),
        ]
    )
    db.commit()

    rows = knowledge_files.list_knowledge_files(
        workspace_id=workspace_a.id,
        category="writing_skill",
        db=db,
        user_id="1",
    )

    assert [row.file_name for row in rows] == ["skill-a.md"]
