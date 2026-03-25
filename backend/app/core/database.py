import logging
import threading
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings
from app.core.migrations import run_startup_migrations

logger = logging.getLogger("uvicorn.error")


class Base(DeclarativeBase):
    pass


def _ensure_sqlite_parent_dir(database_url: str) -> None:
    if not database_url.startswith("sqlite:///"):
        return

    sqlite_path = database_url.removeprefix("sqlite:///")
    if sqlite_path == ":memory:":
        return
    Path(sqlite_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)


_ensure_sqlite_parent_dir(settings.database_url)
settings.storage_dir.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    settings.database_url,
    connect_args=(
        {"check_same_thread": False}
        if settings.database_url.startswith("sqlite")
        else {"connect_timeout": 5}
    ),
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

_db_init_lock = threading.Lock()
_db_init_started = False
_db_init_completed = False
_db_init_error: str | None = None


def initialize_database() -> None:
    global _db_init_started, _db_init_completed, _db_init_error
    if _db_init_completed:
        return

    with _db_init_lock:
        if _db_init_completed:
            return
        _db_init_started = True
        try:
            Base.metadata.create_all(bind=engine)
            run_startup_migrations(engine)
            _db_init_completed = True
            _db_init_error = None
        except Exception as exc:
            _db_init_error = str(exc)
            logger.exception("Database initialization failed")


def start_database_initialization_in_background() -> None:
    global _db_init_started
    if _db_init_started or _db_init_completed:
        return

    thread = threading.Thread(target=initialize_database, name="db-init", daemon=True)
    _db_init_started = True
    thread.start()


def get_database_init_status() -> dict[str, str | bool | None]:
    if _db_init_completed:
        state = "ready"
    elif _db_init_error:
        state = "failed"
    elif _db_init_started:
        state = "initializing"
    else:
        state = "pending"

    return {
        "state": state,
        "started": _db_init_started,
        "completed": _db_init_completed,
        "error": _db_init_error,
    }


def get_db():
    initialize_database()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
