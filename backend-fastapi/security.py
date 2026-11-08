from datetime import datetime, timedelta, timezone
from typing import Any
import uuid

import jwt
from pwdlib import PasswordHash

from config import settings

# Initialize password hasher using pwdlib's recommended Argon2 configuration
password_hash = PasswordHash.recommended()

ALGORITHM = settings.JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS


def _get_secret_key() -> str:
    """Retrieve JWT_SECRET_KEY from settings, failing safely if not configured."""
    secret = settings.JWT_SECRET_KEY
    if not secret or not secret.strip():
        raise ValueError(
            "JWT_SECRET_KEY is not configured or is empty. Please set JWT_SECRET_KEY in your .env file."
        )
    return secret


def hash_password(password: str) -> str:
    """Hash a plaintext password using pwdlib's recommended Argon2 hasher."""
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against an Argon2 hash.

    Returns True if the password matches the hash, False otherwise.
    """
    try:
        return password_hash.verify(password, hashed_password)
    except Exception:
        return False


def create_access_token(user_id: int | str, expires_delta: timedelta | None = None) -> str:
    """Create an HS256-signed JWT access token containing the user ID in the 'sub' claim.

    Expires in 30 minutes by default unless a custom expires_delta is provided.
    """
    secret_key = _get_secret_key()
    expire_delta = expires_delta if expires_delta is not None else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = datetime.now(timezone.utc) + expire_delta

    payload: dict[str, Any] = {
        "sub": str(user_id),
        "exp": expire,
    }
    return jwt.encode(payload, secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate an HS256 JWT access token using PyJWT's built-in verification.

    Raises:
        jwt.ExpiredSignatureError: If the token has expired.
        jwt.InvalidTokenError: If the token is invalid, tampered, or malformed.
        ValueError: If JWT_SECRET_KEY is missing.
    """
    secret_key = _get_secret_key()
    return jwt.decode(token, secret_key, algorithms=[ALGORITHM])


def create_refresh_token(user_id: int | str, expires_delta: timedelta | None = None) -> str:
    """Create an HS256-signed JWT refresh token containing sub, user_id, token_type, and exp claims."""
    secret_key = _get_secret_key()
    expire_delta = (
        expires_delta
        if expires_delta is not None
        else timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    )
    expire = datetime.now(timezone.utc) + expire_delta

    payload: dict[str, Any] = {
        "sub": str(user_id),
        "user_id": int(user_id) if str(user_id).isdigit() else user_id,
        "token_type": "refresh",
        "type": "refresh",
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, secret_key, algorithm=ALGORITHM)


def decode_refresh_token(token: str) -> dict[str, Any]:
    """Decode and validate an HS256 JWT refresh token.

    Raises:
        jwt.ExpiredSignatureError: If the token has expired.
        jwt.InvalidTokenError: If the token is invalid or token_type != 'refresh'.
        ValueError: If JWT_SECRET_KEY is missing.
    """
    secret_key = _get_secret_key()
    payload = jwt.decode(token, secret_key, algorithms=[ALGORITHM])
    token_type = payload.get("token_type") or payload.get("type")
    if token_type != "refresh":
        raise jwt.InvalidTokenError("Token is not a refresh token")
    if not payload.get("sub") and not payload.get("user_id"):
        raise jwt.InvalidTokenError("Refresh token missing required claims")
    return payload

