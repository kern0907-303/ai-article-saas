from datetime import datetime

import jwt
from fastapi import Depends, Header, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings as app_settings
from app.core.security import decode_access_token, hash_password
from app.models.user import User
from app.services.rate_limit_service import check_rate_limit
from app.services.subscription_service import get_active_subscription, normalize_utc_naive

bearer_scheme = HTTPBearer(auto_error=False)
DEFAULT_LOCAL_USER_EMAIL = "local@ai-article-saas.internal"


def get_or_create_local_user(db: Session) -> User:
    user = db.query(User).filter(User.email == DEFAULT_LOCAL_USER_EMAIL).first()
    if user:
        return user

    user = User(
        email=DEFAULT_LOCAL_USER_EMAIL,
        hashed_password=hash_password("auth-disabled-local-user"),
        token_version=1,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        user = db.query(User).filter(User.email == DEFAULT_LOCAL_USER_EMAIL).first()
        if not user:
            raise
        return user
    db.refresh(user)
    return user


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if not app_settings.auth_enabled:
        user = get_or_create_local_user(db)
        request.state.current_user = user
        request.state.jwt_payload = {"sub": str(user.id), "mode": "auth-disabled"}
        return user

    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="缺少或無效的 Token")

    token = credentials.credentials
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        token_version = payload.get("tv")
        if not user_id:
            raise HTTPException(status_code=401, detail="無效的 Token")
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="Token 驗證失敗") from exc

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(status_code=401, detail="使用者不存在")

    current_tv = int(user.token_version or 1)
    if token_version is None or int(token_version) != current_tv:
        raise HTTPException(status_code=401, detail="登入狀態已失效，請重新登入")

    check_rate_limit(f"global:{user.id}", limit=180, window_seconds=60)

    request.state.current_user = user
    request.state.jwt_payload = payload
    return user


def get_current_user_id(current_user: User = Depends(get_current_user)) -> str:
    return str(current_user.id)


def require_active_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    if not app_settings.auth_enabled:
        return current_user

    sub = get_active_subscription(db, current_user.id)
    if not sub:
        raise HTTPException(
            status_code=402,
            detail="目前未開通方案，可先啟用 7 天試用或升級年繳",
        )

    expires_at = normalize_utc_naive(sub.expires_at)
    if not expires_at or expires_at <= datetime.utcnow():
        raise HTTPException(status_code=402, detail="訂閱已到期，請續費後使用")

    return current_user


def require_admin_access(
    current_user: User = Depends(get_current_user),
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
) -> User:
    configured_key = (app_settings.admin_api_key or "").strip()
    if not configured_key or configured_key == "change-admin-key-in-production":
        raise HTTPException(status_code=503, detail="管理員功能尚未完成設定")
    if not x_admin_key or x_admin_key != configured_key:
        raise HTTPException(status_code=403, detail="管理員驗證失敗")
    return current_user
