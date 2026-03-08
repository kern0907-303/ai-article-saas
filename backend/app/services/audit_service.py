import json

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def log_audit(db: Session, action: str, user_id: str | None = None, metadata: dict | None = None) -> None:
    record = AuditLog(
        user_id=user_id,
        action=action,
        metadata_json=json.dumps(metadata or {}, ensure_ascii=False),
    )
    db.add(record)
    db.commit()
