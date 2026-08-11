from datetime import UTC, datetime, timedelta
from typing import Any

from jose import jwt
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

_jwt_secret_override: str | None = None
_jwt_loaded_from_vault: bool = False


def set_jwt_secret_override(secret: str, *, from_vault: bool = False) -> None:
    global _jwt_secret_override, _jwt_loaded_from_vault
    _jwt_secret_override = secret
    _jwt_loaded_from_vault = from_vault


def jwt_loaded_from_vault() -> bool:
    return _jwt_loaded_from_vault


def get_jwt_secret() -> str:
    return _jwt_secret_override or settings.jwt_secret_key


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(subject: str, tenant_id: str, role: str, expires_delta: timedelta | None = None) -> str:
    expire = datetime.now(UTC) + (expires_delta or timedelta(minutes=settings.jwt_access_token_expire_minutes))
    payload: dict[str, Any] = {
        "sub": subject,
        "tenant_id": tenant_id,
        "role": role,
        "exp": expire,
    }
    return jwt.encode(payload, get_jwt_secret(), algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, get_jwt_secret(), algorithms=[settings.jwt_algorithm])
