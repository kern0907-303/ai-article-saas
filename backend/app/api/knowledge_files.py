import os

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.knowledge_file import KnowledgeFile
from app.models.workspace import Workspace
from app.schemas.knowledge_file import KnowledgeFileDefaultReferenceUpdate, KnowledgeFileOut
from app.services.audit_service import log_audit
from app.services.entitlement_service import require_feature_access
from app.services.file_service import extract_text_from_file, save_uploaded_file
from app.utils.deps import get_current_user_id, require_active_subscription

router = APIRouter(
    prefix="/knowledge-files",
    tags=["knowledge-files"],
    dependencies=[Depends(require_active_subscription)],
)


@router.get("", response_model=list[KnowledgeFileOut])
def list_knowledge_files(
    workspace_id: int | None = Query(default=None),
    category: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    query = db.query(KnowledgeFile).filter(KnowledgeFile.user_id == user_id, KnowledgeFile.is_active.is_(True))
    if workspace_id is not None:
        query = query.filter(KnowledgeFile.workspace_id == workspace_id)
    if category:
        query = query.filter(KnowledgeFile.category == category)
    return query.order_by(KnowledgeFile.created_at.desc()).all()


def _validate_workspace(db: Session, user_id: str, workspace_id: int | None) -> None:
    if workspace_id is None:
        return
    exists = (
        db.query(Workspace.id)
        .filter(Workspace.id == workspace_id, Workspace.user_id == user_id, Workspace.is_active.is_(True))
        .first()
    )
    if not exists:
        raise HTTPException(status_code=404, detail="找不到品牌/專案")


@router.post("", response_model=KnowledgeFileOut)
async def upload_knowledge_file(
    file: UploadFile = File(...),
    include_as_default_reference: bool = Form(True),
    workspace_id: int | None = Form(None),
    category: str = Form("reference_material"),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="請提供檔案")

    _validate_workspace(db, user_id, workspace_id)
    stored_path, size, extracted_text = await save_uploaded_file(user_id, file)
    try:
        require_feature_access(db, int(user_id), feature="knowledge_upload", extra_bytes=size)
    except HTTPException:
        if os.path.exists(stored_path):
            os.remove(stored_path)
        raise

    record = KnowledgeFile(
        user_id=user_id,
        file_name=file.filename,
        stored_path=stored_path,
        workspace_id=workspace_id,
        category=category,
        content_type=file.content_type,
        file_size=size,
        extracted_text=extracted_text,
        extracted_text_preview=extracted_text[:500],
        is_active=True,
        is_default_reference=include_as_default_reference,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    log_audit(
        db,
        action="knowledge.upload",
        user_id=user_id,
        metadata={"file_id": record.id, "file_name": file.filename, "workspace_id": workspace_id, "category": category},
    )
    return record


@router.get("/{file_id}/text")
def get_knowledge_file_text(
    file_id: int,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    record = (
        db.query(KnowledgeFile)
        .filter(
            KnowledgeFile.id == file_id,
            KnowledgeFile.user_id == user_id,
            KnowledgeFile.is_active.is_(True),
        )
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="找不到檔案")

    return {
        "id": record.id,
        "file_name": record.file_name,
        "text": extract_text_from_file(record.stored_path, record.extracted_text),
    }


@router.patch("/{file_id}/default-reference", response_model=KnowledgeFileOut)
def update_default_reference(
    file_id: int,
    payload: KnowledgeFileDefaultReferenceUpdate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    record = (
        db.query(KnowledgeFile)
        .filter(
            KnowledgeFile.id == file_id,
            KnowledgeFile.user_id == user_id,
            KnowledgeFile.is_active.is_(True),
        )
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="找不到檔案")

    record.is_default_reference = payload.is_default_reference
    db.commit()
    db.refresh(record)
    log_audit(
        db,
        action="knowledge.default_reference_update",
        user_id=user_id,
        metadata={"file_id": file_id, "is_default_reference": record.is_default_reference},
    )
    return record


@router.delete("/{file_id}")
def delete_knowledge_file(
    file_id: int,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    record = (
        db.query(KnowledgeFile)
        .filter(
            KnowledgeFile.id == file_id,
            KnowledgeFile.user_id == user_id,
            KnowledgeFile.is_active.is_(True),
        )
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="找不到檔案")

    record.is_active = False
    if record.stored_path and os.path.exists(record.stored_path):
        os.remove(record.stored_path)

    db.commit()
    log_audit(db, action="knowledge.delete", user_id=user_id, metadata={"file_id": file_id, "file_name": record.file_name})
    return {"success": True, "message": "檔案已刪除", "file_id": file_id}
