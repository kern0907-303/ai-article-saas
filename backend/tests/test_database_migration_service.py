from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.google_sheet_destination import GoogleSheetDestination
from app.models.settings import Setting
from app.models.user import User
from app.services.database_migration_service import (
    DEFAULT_LOCAL_USER_EMAIL,
    import_model_modules,
    migrate_database,
)


def create_source_database(path):
    import_model_modules()
    engine = create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        user = User(id=42, email="old-owner@example.com", hashed_password="hashed", token_version=1)
        db.add(user)
        db.add(
            Setting(
                id=7,
                user_id="42",
                ai_provider="openai",
                openai_api_key_encrypted="encrypted-openai-key",
                article_model="gpt-5.4-mini",
                prompt_model="gpt-5.4-mini",
                image_model="gpt-image-1.5",
            )
        )
        db.add(
            GoogleSheetDestination(
                id=9,
                user_id="42",
                label="客戶A 內容準備",
                spreadsheet_id="sheet-id-123",
                sheet_name="文章準備",
                service_account_email="svc@example.iam.gserviceaccount.com",
                service_account_json_encrypted="encrypted-service-account-json",
                is_default=True,
                created_at=datetime(2026, 6, 5, 8, 0, 0),
                updated_at=datetime(2026, 6, 5, 8, 30, 0),
            )
        )
        db.commit()
    finally:
        db.close()


def test_migrate_database_copies_google_sheet_settings_to_local_user(tmp_path):
    source_path = tmp_path / "source.db"
    target_path = tmp_path / "target.db"
    create_source_database(source_path)

    result = migrate_database(
        source_url=f"sqlite:///{source_path}",
        target_url=f"sqlite:///{target_path}",
        remap_to_local_user=True,
    )

    engine = create_engine(f"sqlite:///{target_path}", connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        local_user = db.query(User).filter(User.email == DEFAULT_LOCAL_USER_EMAIL).one()
        destination = db.query(GoogleSheetDestination).one()
        setting = db.query(Setting).one()

        assert result.local_user_id == local_user.id
        assert destination.user_id == str(local_user.id)
        assert destination.label == "客戶A 內容準備"
        assert destination.service_account_json_encrypted == "encrypted-service-account-json"
        assert setting.user_id == str(local_user.id)
        assert setting.openai_api_key_encrypted == "encrypted-openai-key"
    finally:
        db.close()
