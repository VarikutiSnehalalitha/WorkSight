from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from cryptography.fernet import Fernet, InvalidToken
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(
    subject: str,
    role: str,
    extra_claims: Optional[Dict[str, Any]] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload: Dict[str, Any] = {
        "sub": subject,
        "role": role,
        "type": "access",
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_stream_token(user_id: int, camera_id: int, role: str) -> str:
    """Short-lived signed token exclusively for authorized MJPEG live video streaming."""
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.STREAM_TOKEN_EXPIRE_MINUTES
    )
    payload: Dict[str, Any] = {
        "sub": str(user_id),
        "camera_id": camera_id,
        "role": role,
        "type": "stream",
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    settings = get_settings()
    try:
        return jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
    except JWTError:
        return None


def _get_fernet() -> Fernet:
    settings = get_settings()
    return Fernet(settings.resolved_fernet_key)


def encrypt_secret(plaintext: Optional[str]) -> Optional[str]:
    """Encrypt sensitive camera credentials / RTSP URIs at rest using Fernet (AES-128-CBC + HMAC-SHA256)."""
    if not plaintext:
        return None
    token = _get_fernet().encrypt(plaintext.encode("utf-8"))
    return token.decode("utf-8")


def decrypt_secret(ciphertext: Optional[str]) -> Optional[str]:
    """Decrypt camera credentials in-memory only inside backend CCTV worker."""
    if not ciphertext:
        return None
    try:
        return _get_fernet().decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        return None


def mask_stream_endpoint(raw_url: Optional[str], is_simulated: bool = False) -> str:
    """Return a safe, credential-free endpoint label for API responses.

    NEVER exposes usernames, passwords, query tokens, or full RTSP connection strings.
    """
    if is_simulated:
        return "simulated://local-dev-generator (SIMULATED)"
    if not raw_url:
        return "unconfigured"
    try:
        parsed = urlparse(raw_url)
        scheme = parsed.scheme or "rtsp"
        host = parsed.hostname or "camera-host"
        port = f":{parsed.port}" if parsed.port else ""
        return f"{scheme}://***@{host}{port}/***"
    except Exception:
        return "rtsp://***@redacted/***"
