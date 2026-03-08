from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    generate_reset_token,
    hash_password,
    hash_reset_token,
    verify_password,
)
from app.models.password_reset_token import PasswordResetToken
from app.models.user import User
from app.schemas.auth import (
    AuthResponse,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
)
from app.services.audit_service import log_audit
from app.services.subscription_service import normalize_utc_naive

router = APIRouter(tags=["auth"])


@router.post("/register", response_model=AuthResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="此 Email 已被註冊")

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        token_version=1,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(subject=str(user.id), token_version=int(user.token_version or 1))
    log_audit(db, action="auth.register", user_id=str(user.id), metadata={"email": user.email})
    return AuthResponse(
        access_token=token,
        user=user,
    )


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Email 或密碼錯誤")

    token = create_access_token(subject=str(user.id), token_version=int(user.token_version or 1))
    log_audit(db, action="auth.login", user_id=str(user.id), metadata={"email": user.email})
    return AuthResponse(
        access_token=token,
        user=user,
    )


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()

    # 為避免帳號探測，無論使用者是否存在都回固定訊息
    if not user:
        return ForgotPasswordResponse(message="若該帳號存在，重設連結已寄出")

    token = generate_reset_token()
    token_hash = hash_reset_token(token)
    expires_at = datetime.utcnow() + timedelta(minutes=30)

    record = PasswordResetToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at,
        used_at=None,
    )
    db.add(record)
    db.commit()

    # MVP: 僅回傳 token 模擬寄信。正式版請改成 Email Provider。
    log_audit(db, action="auth.forgot_password", user_id=str(user.id), metadata={"email": user.email})
    if settings.expose_reset_token_in_response:
        return ForgotPasswordResponse(message="若該帳號存在，重設連結已寄出", reset_token=token)

    return ForgotPasswordResponse(message="若該帳號存在，重設連結已寄出")


@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    token_hash = hash_reset_token(payload.token)
    record = db.query(PasswordResetToken).filter(PasswordResetToken.token_hash == token_hash).first()
    if not record:
        raise HTTPException(status_code=400, detail="重設連結無效")

    now = datetime.utcnow()
    if record.used_at is not None:
        raise HTTPException(status_code=400, detail="重設連結已被使用")
    expires_at = normalize_utc_naive(record.expires_at)
    if not expires_at or expires_at <= now:
        raise HTTPException(status_code=400, detail="重設連結已過期")

    user = db.query(User).filter(User.id == record.user_id).first()
    if not user:
        raise HTTPException(status_code=400, detail="使用者不存在")

    user.hashed_password = hash_password(payload.new_password)
    user.token_version = int(user.token_version or 1) + 1
    record.used_at = now

    db.commit()
    log_audit(db, action="auth.reset_password", user_id=str(user.id), metadata={"email": user.email})
    return {"success": True, "message": "密碼重設成功，請重新登入"}
