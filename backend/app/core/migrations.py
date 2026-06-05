from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def _table_exists(engine: Engine, table_name: str) -> bool:
    return inspect(engine).has_table(table_name)


def _column_exists(engine: Engine, table_name: str, column_name: str) -> bool:
    cols = inspect(engine).get_columns(table_name)
    return any(c["name"] == column_name for c in cols)


def _add_column_if_missing(engine: Engine, table: str, column_sql: str, col_name: str) -> None:
    if not _column_exists(engine, table, col_name):
        with engine.begin() as conn:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column_sql}"))


def run_startup_migrations(engine: Engine) -> None:
    if _table_exists(engine, "users"):
        _add_column_if_missing(engine, "users", "token_version INTEGER DEFAULT 1", "token_version")

    if _table_exists(engine, "settings"):
        _add_column_if_missing(engine, "settings", "ai_provider VARCHAR(50) DEFAULT 'openai'", "ai_provider")
        _add_column_if_missing(engine, "settings", "openai_api_key_encrypted TEXT", "openai_api_key_encrypted")
        _add_column_if_missing(engine, "settings", "anthropic_api_key VARCHAR(255)", "anthropic_api_key")
        _add_column_if_missing(engine, "settings", "gemini_api_key VARCHAR(255)", "gemini_api_key")
        _add_column_if_missing(engine, "settings", "github_api_key VARCHAR(255)", "github_api_key")
        _add_column_if_missing(engine, "settings", "anthropic_api_key_encrypted TEXT", "anthropic_api_key_encrypted")
        _add_column_if_missing(engine, "settings", "gemini_api_key_encrypted TEXT", "gemini_api_key_encrypted")
        _add_column_if_missing(engine, "settings", "github_api_key_encrypted TEXT", "github_api_key_encrypted")
        _add_column_if_missing(engine, "settings", "website_api_key_encrypted TEXT", "website_api_key_encrypted")
        _add_column_if_missing(engine, "settings", "social_api_key_encrypted TEXT", "social_api_key_encrypted")
        _add_column_if_missing(engine, "settings", "article_model VARCHAR(100) DEFAULT 'gpt-5.4-mini'", "article_model")
        _add_column_if_missing(engine, "settings", "prompt_model VARCHAR(100) DEFAULT 'gpt-5.4-mini'", "prompt_model")
        _add_column_if_missing(engine, "settings", "image_model VARCHAR(100) DEFAULT 'gpt-image-1.5'", "image_model")
        with engine.begin() as conn:
            conn.execute(text("UPDATE settings SET image_model='gpt-image-1.5' WHERE image_model='gpt-image-2'"))

    if _table_exists(engine, "articles"):
        _add_column_if_missing(engine, "articles", "generation_error TEXT", "generation_error")

    if _table_exists(engine, "article_images"):
        _add_column_if_missing(engine, "article_images", "generation_error TEXT", "generation_error")

    if _table_exists(engine, "image_settings"):
        with engine.begin() as conn:
            conn.execute(text("UPDATE image_settings SET openai_image_model='gpt-image-1.5' WHERE openai_image_model='gpt-image-2'"))

    if _table_exists(engine, "knowledge_files"):
        _add_column_if_missing(
            engine,
            "knowledge_files",
            "is_default_reference BOOLEAN DEFAULT 1",
            "is_default_reference",
        )

    if _table_exists(engine, "plans"):
        _add_column_if_missing(engine, "plans", "is_trial INTEGER DEFAULT 0", "is_trial")
        with engine.begin() as conn:
            existing = conn.execute(text("SELECT id FROM plans WHERE code='pro-yearly' LIMIT 1")).fetchone()
            if not existing:
                conn.execute(
                    text(
                        """
                        INSERT INTO plans (code, name, description, duration_days, price_cents, currency, is_active, is_trial, created_at, updated_at)
                        VALUES (:code, :name, :description, :duration_days, :price_cents, :currency, :is_active, :is_trial, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                        """
                    ),
                    {
                        "code": "pro-yearly",
                        "name": "Pro 年繳",
                        "description": "一年期完整權限",
                        "duration_days": 365,
                        "price_cents": 299900,
                        "currency": "TWD",
                        "is_active": 1,
                        "is_trial": 0,
                    },
                )

            trial = conn.execute(text("SELECT id FROM plans WHERE code='trial-7d' LIMIT 1")).fetchone()
            if not trial:
                conn.execute(
                    text(
                        """
                        INSERT INTO plans (code, name, description, duration_days, price_cents, currency, is_active, is_trial, created_at, updated_at)
                        VALUES (:code, :name, :description, :duration_days, :price_cents, :currency, :is_active, :is_trial, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                        """
                    ),
                    {
                        "code": "trial-7d",
                        "name": "免費試用 7 天",
                        "description": "可體驗核心功能，含每日使用額度",
                        "duration_days": 7,
                        "price_cents": 0,
                        "currency": "TWD",
                        "is_active": 1,
                        "is_trial": 1,
                    },
                )

    if _table_exists(engine, "subscriptions"):
        _add_column_if_missing(engine, "subscriptions", "access_tier VARCHAR(30) DEFAULT 'inactive'", "access_tier")
        _add_column_if_missing(engine, "subscriptions", "trial_used INTEGER DEFAULT 0", "trial_used")
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    UPDATE subscriptions
                    SET access_tier = CASE WHEN status='active' THEN 'paid' ELSE 'inactive' END
                    WHERE access_tier IS NULL OR access_tier=''
                    """
                )
            )
            conn.execute(text("UPDATE subscriptions SET trial_used = 0 WHERE trial_used IS NULL"))
