import threading

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from starlette.requests import Request

from app.core.database import Base
from app.models.user import User
from app.services.entitlement_service import require_feature_access
from app.utils import deps


def make_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)()


def make_request() -> Request:
    return Request({"type": "http", "method": "GET", "path": "/", "headers": []})


def test_auth_disabled_mode_uses_local_default_user_without_token(monkeypatch):
    db = make_session()
    monkeypatch.setattr(deps.app_settings, "auth_enabled", False, raising=False)

    user = deps.get_current_user(make_request(), credentials=None, db=db)

    assert user.email == deps.DEFAULT_LOCAL_USER_EMAIL
    assert db.query(User).filter(User.email == deps.DEFAULT_LOCAL_USER_EMAIL).count() == 1


def test_auth_disabled_mode_bypasses_subscription_feature_gate(monkeypatch):
    db = make_session()
    monkeypatch.setattr(deps.app_settings, "auth_enabled", False, raising=False)

    require_feature_access(db, user_id=1, feature="article_generate")


def test_local_default_user_creation_is_safe_for_parallel_requests(monkeypatch, tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'auth-disabled.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    barrier = threading.Barrier(2)
    original_hash_password = deps.hash_password

    def synchronized_hash_password(password: str) -> str:
        barrier.wait(timeout=5)
        return original_hash_password(password)

    monkeypatch.setattr(deps, "hash_password", synchronized_hash_password)
    errors = []
    user_ids = []

    def worker():
        db = SessionLocal()
        try:
            user_ids.append(deps.get_or_create_local_user(db).id)
        except Exception as exc:  # pragma: no cover - assertion reports the actual error
            errors.append(exc)
        finally:
            db.close()

    threads = [threading.Thread(target=worker), threading.Thread(target=worker)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    db = SessionLocal()
    try:
        assert errors == []
        assert len(set(user_ids)) == 1
        assert db.query(User).filter(User.email == deps.DEFAULT_LOCAL_USER_EMAIL).count() == 1
    finally:
        db.close()
