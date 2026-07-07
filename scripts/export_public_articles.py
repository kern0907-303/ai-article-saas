#!/usr/bin/env python3
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.core.database import SessionLocal, initialize_database  # noqa: E402
from app.models.article import Article  # noqa: E402


def serialize_article(article: Article) -> dict:
    return {
        "id": article.id,
        "workspace_id": article.workspace_id,
        "topic": article.topic,
        "outline": article.outline,
        "content": article.content or "",
        "published_to_website": article.published_to_website,
        "created_at": article.created_at.isoformat() if article.created_at else "",
        "updated_at": article.updated_at.isoformat() if article.updated_at else "",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Export safe public articles to the frontend GitHub JSON fallback.")
    parser.add_argument("--owner-id", required=True, help="Account user_id to export. Required to avoid cross-account data mixing.")
    parser.add_argument("--workspace-id", type=int, default=None, help="Optional workspace/brand id to export.")
    parser.add_argument(
        "--output",
        default=str(ROOT_DIR / "frontend" / "public" / "published-articles.json"),
        help="Output JSON path.",
    )
    args = parser.parse_args()

    initialize_database()
    db = SessionLocal()
    try:
        query = (
            db.query(Article)
            .filter(
                Article.user_id == args.owner_id,
                Article.published_to_website.is_(True),
                Article.content.isnot(None),
            )
            .order_by(Article.updated_at.desc(), Article.id.desc())
        )
        if args.workspace_id is not None:
            query = query.filter(Article.workspace_id == args.workspace_id)

        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "owner_id": args.owner_id,
            "workspace_id": args.workspace_id,
            "articles": [serialize_article(article) for article in query.all()],
        }
    finally:
        db.close()

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Exported {len(payload['articles'])} public articles to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
