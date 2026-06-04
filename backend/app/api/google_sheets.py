from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.article import Article
from app.models.google_sheet_destination import GoogleSheetDestination
from app.schemas.google_sheets import (
    ExportArticleToSheetRequest,
    ExportArticleToSheetResponse,
    GoogleSheetDestinationCreate,
    GoogleSheetDestinationOut,
    GoogleSheetDestinationUpdate,
)
from app.services.audit_service import log_audit
from app.services.crypto_service import decrypt_text, encrypt_text
from app.services.google_sheets_service import (
    append_article_row_to_sheet,
    build_article_sheet_row,
    normalize_sheet_destination_payload,
)
from app.utils.deps import get_current_user_id, require_active_subscription

router = APIRouter(tags=["google-sheets"])


def _set_single_default(db: Session, user_id: str, destination: GoogleSheetDestination) -> None:
    if not destination.is_default:
        return
    (
        db.query(GoogleSheetDestination)
        .filter(GoogleSheetDestination.user_id == user_id, GoogleSheetDestination.id != destination.id)
        .update({"is_default": False})
    )


def _out(destination: GoogleSheetDestination) -> GoogleSheetDestinationOut:
    return GoogleSheetDestinationOut.model_validate(destination)


@router.get("/google-sheets/destinations", response_model=list[GoogleSheetDestinationOut])
def list_destinations(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    return (
        db.query(GoogleSheetDestination)
        .filter(GoogleSheetDestination.user_id == user_id)
        .order_by(GoogleSheetDestination.is_default.desc(), GoogleSheetDestination.updated_at.desc())
        .all()
    )


@router.post("/google-sheets/destinations", response_model=GoogleSheetDestinationOut)
def create_destination(
    payload: GoogleSheetDestinationCreate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    try:
        data = normalize_sheet_destination_payload(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    destination = GoogleSheetDestination(
        user_id=user_id,
        label=data["label"],
        spreadsheet_id=data["spreadsheet_id"],
        sheet_name=data["sheet_name"],
        service_account_email=data["service_account_email"],
        service_account_json_encrypted=encrypt_text(data["service_account_json"]) or "",
        is_default=data["is_default"],
    )
    db.add(destination)
    try:
        db.flush()
        _set_single_default(db, user_id, destination)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail="同一使用者下已有相同目的地名稱") from exc

    db.refresh(destination)
    log_audit(db, action="google_sheets.destination_create", user_id=user_id, metadata={"destination_id": destination.id})
    return _out(destination)


@router.put("/google-sheets/destinations/{destination_id}", response_model=GoogleSheetDestinationOut)
def update_destination(
    destination_id: int,
    payload: GoogleSheetDestinationUpdate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    destination = (
        db.query(GoogleSheetDestination)
        .filter(GoogleSheetDestination.id == destination_id, GoogleSheetDestination.user_id == user_id)
        .first()
    )
    if not destination:
        raise HTTPException(status_code=404, detail="找不到 Google Sheets 目的地")

    raw = payload.model_dump()
    if raw.get("service_account_json"):
        try:
            data = normalize_sheet_destination_payload(raw)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        destination.service_account_email = data["service_account_email"]
        destination.service_account_json_encrypted = encrypt_text(data["service_account_json"]) or ""
    else:
        data = {
            "label": raw["label"].strip(),
            "spreadsheet_id": raw["spreadsheet_id"].strip(),
            "sheet_name": raw["sheet_name"].strip(),
            "is_default": raw["is_default"],
        }

    destination.label = data["label"]
    destination.spreadsheet_id = data["spreadsheet_id"]
    destination.sheet_name = data["sheet_name"]
    destination.is_default = bool(data["is_default"])
    _set_single_default(db, user_id, destination)
    db.commit()
    db.refresh(destination)
    log_audit(db, action="google_sheets.destination_update", user_id=user_id, metadata={"destination_id": destination.id})
    return _out(destination)


@router.delete("/google-sheets/destinations/{destination_id}")
def delete_destination(
    destination_id: int,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    destination = (
        db.query(GoogleSheetDestination)
        .filter(GoogleSheetDestination.id == destination_id, GoogleSheetDestination.user_id == user_id)
        .first()
    )
    if not destination:
        raise HTTPException(status_code=404, detail="找不到 Google Sheets 目的地")
    db.delete(destination)
    db.commit()
    log_audit(db, action="google_sheets.destination_delete", user_id=user_id, metadata={"destination_id": destination_id})
    return {"success": True, "message": "Google Sheets 目的地已刪除", "destination_id": destination_id}


@router.post(
    "/articles/{article_id}/export/google-sheets",
    response_model=ExportArticleToSheetResponse,
    dependencies=[Depends(require_active_subscription)],
)
def export_article_to_google_sheets(
    article_id: int,
    payload: ExportArticleToSheetRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    article = db.query(Article).filter(Article.id == article_id, Article.user_id == user_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="找不到文章")
    if not article.content:
        raise HTTPException(status_code=400, detail="文章內容為空，無法上傳到 Google Sheets")

    query = db.query(GoogleSheetDestination).filter(GoogleSheetDestination.user_id == user_id)
    if payload.destination_id:
        destination = query.filter(GoogleSheetDestination.id == payload.destination_id).first()
    else:
        destination = query.filter(GoogleSheetDestination.is_default.is_(True)).first() or query.order_by(
            GoogleSheetDestination.updated_at.desc()
        ).first()
    if not destination:
        raise HTTPException(status_code=400, detail="請先建立 Google Sheets 目的地")

    service_account_json = decrypt_text(destination.service_account_json_encrypted)
    if not service_account_json:
        raise HTTPException(status_code=400, detail="Google Sheets Service Account JSON 無法解密，請重新儲存目的地")

    row = build_article_sheet_row(article, destination_label=destination.label)
    try:
        result = append_article_row_to_sheet(
            service_account_json=service_account_json,
            spreadsheet_id=destination.spreadsheet_id,
            sheet_name=destination.sheet_name,
            row=row,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    log_audit(
        db,
        action="google_sheets.article_export",
        user_id=user_id,
        metadata={"article_id": article.id, "destination_id": destination.id, "updated_range": result.updated_range},
    )
    return ExportArticleToSheetResponse(
        success=True,
        article_id=article.id,
        destination_id=destination.id,
        destination_label=destination.label,
        spreadsheet_id=result.spreadsheet_id,
        sheet_name=result.sheet_name,
        updated_range=result.updated_range,
        updated_rows=result.updated_rows,
        message="文章已上傳到 Google Sheets",
    )
