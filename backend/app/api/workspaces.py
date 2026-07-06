from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.workspace import Workspace
from app.schemas.workspace import WorkspaceCreateRequest, WorkspaceOut, WorkspaceUpdateRequest
from app.services.audit_service import log_audit
from app.utils.deps import get_current_user_id, require_active_subscription

router = APIRouter(
    prefix="/workspaces",
    tags=["workspaces"],
    dependencies=[Depends(require_active_subscription)],
)


def _clear_default_workspace(db: Session, user_id: str) -> None:
    db.query(Workspace).filter(Workspace.user_id == user_id, Workspace.is_active.is_(True)).update(
        {"is_default": False},
        synchronize_session=False,
    )


def _get_workspace_or_404(db: Session, user_id: str, workspace_id: int) -> Workspace:
    record = (
        db.query(Workspace)
        .filter(Workspace.id == workspace_id, Workspace.user_id == user_id, Workspace.is_active.is_(True))
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="找不到品牌/專案")
    return record


@router.get("", response_model=list[WorkspaceOut])
def list_workspaces(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    return (
        db.query(Workspace)
        .filter(Workspace.user_id == user_id, Workspace.is_active.is_(True))
        .order_by(Workspace.is_default.desc(), Workspace.updated_at.desc())
        .all()
    )


@router.post("", response_model=WorkspaceOut)
def create_workspace(
    payload: WorkspaceCreateRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    if payload.is_default:
        _clear_default_workspace(db, user_id)

    record = Workspace(
        user_id=user_id,
        name=payload.name.strip(),
        description=payload.description,
        tone=payload.tone,
        audience=payload.audience,
        notes=payload.notes,
        is_default=payload.is_default,
        is_active=True,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    log_audit(db, action="workspaces.create", user_id=user_id, metadata={"workspace_id": record.id})
    return record


@router.put("/{workspace_id}", response_model=WorkspaceOut)
def update_workspace(
    workspace_id: int,
    payload: WorkspaceUpdateRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    record = _get_workspace_or_404(db, user_id, workspace_id)
    if payload.is_default is True:
        _clear_default_workspace(db, user_id)
        record.is_default = True
    elif payload.is_default is False:
        record.is_default = False

    if payload.name is not None:
        record.name = payload.name.strip()
    if payload.description is not None:
        record.description = payload.description
    if payload.tone is not None:
        record.tone = payload.tone
    if payload.audience is not None:
        record.audience = payload.audience
    if payload.notes is not None:
        record.notes = payload.notes

    db.commit()
    db.refresh(record)
    log_audit(db, action="workspaces.update", user_id=user_id, metadata={"workspace_id": record.id})
    return record


@router.delete("/{workspace_id}")
def delete_workspace(
    workspace_id: int,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    record = _get_workspace_or_404(db, user_id, workspace_id)
    record.is_active = False
    record.is_default = False
    db.commit()
    log_audit(db, action="workspaces.delete", user_id=user_id, metadata={"workspace_id": record.id})
    return {"success": True, "message": "品牌/專案已刪除", "workspace_id": workspace_id}
