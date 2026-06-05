from datetime import datetime, timedelta
import os
import subprocess
import sys

from app.api.admin import build_account_storage_status, build_admin_account_rows


class UserStub:
    def __init__(self, user_id: int, email: str):
        self.id = user_id
        self.email = email
        self.created_at = datetime(2026, 6, 4, 8, 0, 0)
        self.updated_at = datetime(2026, 6, 4, 9, 0, 0)


class SubscriptionStub:
    status = "active"
    access_tier = "paid"
    expires_at = datetime(2027, 6, 4, 8, 0, 0)


def test_storage_status_flags_sqlite_without_persistent_storage_as_unsafe():
    status = build_account_storage_status(
        database_url="sqlite:////tmp/app.db",
        persistent_storage_enabled=False,
        storage_dir="/tmp/storage",
        require_persistent_database=True,
    )

    assert status.database_backend == "sqlite"
    assert status.account_data_safe is False
    assert "持久化資料庫" in status.warning


def test_storage_status_marks_postgres_as_safe():
    status = build_account_storage_status(
        database_url="postgresql://user:pass@db.example.com/app",
        persistent_storage_enabled=True,
        storage_dir="/var/data/storage",
        require_persistent_database=True,
    )

    assert status.database_backend == "server"
    assert status.account_data_safe is True
    assert status.warning is None


def test_admin_account_rows_include_account_subscription_and_content_counts():
    row = build_admin_account_rows(
        users=[UserStub(7, "owner@example.com")],
        subscriptions={7: SubscriptionStub()},
        article_counts={7: 3},
        knowledge_counts={7: 2},
        payment_counts={7: 1},
    )[0]

    assert row.id == 7
    assert row.email == "owner@example.com"
    assert row.subscription_status == "active"
    assert row.access_tier == "paid"
    assert row.article_count == 3
    assert row.knowledge_file_count == 2
    assert row.payment_count == 1


def test_require_persistent_database_flag_does_not_crash_app_import():
    env = {
        **os.environ,
        "PYTHONPATH": "backend",
        "REQUIRE_PERSISTENT_DATABASE": "true",
        "DATABASE_URL": "",
    }
    result = subprocess.run(
        [sys.executable, "-c", "import app.main; print('ok')"],
        cwd=os.getcwd(),
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert "ok" in result.stdout
