from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import MetaData, Table, create_engine, inspect, select, text
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.core.migrations import run_startup_migrations
from app.core.security import hash_password
from app.models.user import User

DEFAULT_LOCAL_USER_EMAIL = "local@ai-article-saas.internal"


@dataclass
class TableMigrationResult:
    table: str
    copied: int = 0
    skipped: int = 0
    missing: bool = False


@dataclass
class MigrationResult:
    tables: list[TableMigrationResult] = field(default_factory=list)
    local_user_id: int | None = None

    @property
    def copied_total(self) -> int:
        return sum(table.copied for table in self.tables)

    @property
    def skipped_total(self) -> int:
        return sum(table.skipped for table in self.tables)


def import_model_modules() -> None:
    import app.models.article  # noqa: F401
    import app.models.article_image  # noqa: F401
    import app.models.audit_log  # noqa: F401
    import app.models.google_sheet_destination  # noqa: F401
    import app.models.image_setting  # noqa: F401
    import app.models.knowledge_file  # noqa: F401
    import app.models.password_reset_token  # noqa: F401
    import app.models.payment  # noqa: F401
    import app.models.plan  # noqa: F401
    import app.models.settings  # noqa: F401
    import app.models.subscription  # noqa: F401
    import app.models.usage_counter  # noqa: F401
    import app.models.user  # noqa: F401


def normalize_database_url(database_url: str) -> str:
    normalized = database_url.strip()
    if normalized.startswith("postgres://"):
        return normalized.replace("postgres://", "postgresql://", 1)
    return normalized


def ensure_target_schema(target_engine: Engine) -> None:
    import_model_modules()
    Base.metadata.create_all(bind=target_engine)
    run_startup_migrations(target_engine)


def ensure_sqlite_parent(database_url: str) -> None:
    if not database_url.startswith("sqlite:///"):
        return
    sqlite_path = database_url.removeprefix("sqlite:///")
    if sqlite_path == ":memory:":
        return
    Path(sqlite_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)


def get_or_create_local_user(target_engine: Engine) -> int:
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=target_engine)
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == DEFAULT_LOCAL_USER_EMAIL).first()
        if user:
            return int(user.id)

        user = User(
            email=DEFAULT_LOCAL_USER_EMAIL,
            hashed_password=hash_password("auth-disabled-local-user"),
            token_version=1,
        )
        db.add(user)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            user = db.query(User).filter(User.email == DEFAULT_LOCAL_USER_EMAIL).first()
            if not user:
                raise
        db.refresh(user)
        return int(user.id)
    finally:
        db.close()


def clear_target_tables(target_engine: Engine) -> None:
    with target_engine.begin() as conn:
        if target_engine.dialect.name == "sqlite":
            conn.execute(text("PRAGMA foreign_keys=OFF"))
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
        if target_engine.dialect.name == "sqlite":
            conn.execute(text("PRAGMA foreign_keys=ON"))


def _insert_row(target_engine: Engine, target_table: Table, row: dict) -> bool:
    try:
        with target_engine.begin() as conn:
            if target_engine.dialect.name == "sqlite":
                result = conn.execute(sqlite_insert(target_table).values(row).prefix_with("OR IGNORE"))
                return bool(result.rowcount)
            conn.execute(target_table.insert().values(row))
            return True
    except IntegrityError:
        return False


def migrate_database(
    *,
    source_url: str,
    target_url: str,
    remap_to_local_user: bool = False,
    replace_target: bool = False,
) -> MigrationResult:
    source_url = normalize_database_url(source_url)
    target_url = normalize_database_url(target_url)
    if source_url == target_url:
        raise ValueError("source_url and target_url must be different")

    ensure_sqlite_parent(target_url)
    source_engine = create_engine(source_url, pool_pre_ping=True)
    target_engine = create_engine(
        target_url,
        connect_args={"check_same_thread": False} if target_url.startswith("sqlite") else {"connect_timeout": 5},
        pool_pre_ping=True,
    )
    ensure_target_schema(target_engine)
    if replace_target:
        clear_target_tables(target_engine)

    result = MigrationResult()
    local_user_id = get_or_create_local_user(target_engine) if remap_to_local_user else None
    result.local_user_id = local_user_id

    source_metadata = MetaData()
    target_metadata = MetaData()
    source_inspector = inspect(source_engine)
    target_inspector = inspect(target_engine)
    source_tables = set(source_inspector.get_table_names())
    target_tables = set(target_inspector.get_table_names())

    with source_engine.connect() as source_conn:
        for model_table in Base.metadata.sorted_tables:
            table_name = model_table.name
            table_result = TableMigrationResult(table=table_name)
            result.tables.append(table_result)

            if table_name not in source_tables or table_name not in target_tables:
                table_result.missing = True
                continue
            if remap_to_local_user and table_name == "users":
                continue

            source_table = Table(table_name, source_metadata, autoload_with=source_engine)
            target_table = Table(table_name, target_metadata, autoload_with=target_engine)
            target_columns = {column.name for column in target_table.columns}
            common_columns = [column.name for column in source_table.columns if column.name in target_columns]

            for source_row in source_conn.execute(select(source_table)).mappings():
                row = {column: source_row[column] for column in common_columns}
                if local_user_id is not None and "user_id" in row:
                    row["user_id"] = str(local_user_id) if isinstance(row["user_id"], str) else local_user_id
                inserted = _insert_row(target_engine, target_table, row)
                if inserted:
                    table_result.copied += 1
                else:
                    table_result.skipped += 1

    return result
