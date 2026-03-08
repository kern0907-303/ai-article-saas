import base64
import hashlib
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


def _derive_fernet_key(secret: str) -> bytes:
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def _get_fernet() -> Fernet:
    return Fernet(_derive_fernet_key(settings.encryption_secret))


def encrypt_text(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    return _get_fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_text(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    try:
        return _get_fernet().decrypt(value.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        return None
