#!/usr/bin/env python3
import argparse
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.database_migration_service import migrate_database


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Copy existing SaaS data into the persistent-disk SQLite database without decrypting secrets.",
    )
    parser.add_argument("--source-url", default=os.getenv("SOURCE_DATABASE_URL", ""), help="Old database URL, usually the old Render Postgres external connection string.")
    parser.add_argument("--target-url", default=os.getenv("DATABASE_URL", "sqlite:////var/data/ai-article-saas/app.db"), help="New persistent-disk database URL.")
    parser.add_argument("--remap-to-local-user", action="store_true", help="Move user-owned rows to the auth-disabled local user so the hidden-login site can see them.")
    parser.add_argument("--replace-target", action="store_true", help="Clear target tables before copying. Use only after confirming the target has no data you need.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.source_url:
        print("Missing --source-url or SOURCE_DATABASE_URL", file=sys.stderr)
        return 2

    result = migrate_database(
        source_url=args.source_url,
        target_url=args.target_url,
        remap_to_local_user=args.remap_to_local_user,
        replace_target=args.replace_target,
    )
    print(f"Copied rows: {result.copied_total}")
    print(f"Skipped rows: {result.skipped_total}")
    if result.local_user_id is not None:
        print(f"Remapped user-owned rows to local user id: {result.local_user_id}")
    for table in result.tables:
        status = "missing" if table.missing else f"copied={table.copied} skipped={table.skipped}"
        print(f"- {table.table}: {status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
