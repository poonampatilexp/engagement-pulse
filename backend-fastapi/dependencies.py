import os
import sys

# Ensure backend-fastapi directory is in Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
import models
from security import decode_access_token

http_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    auth: HTTPAuthorizationCredentials | None = Depends(http_bearer),
    db: Session = Depends(get_db),
) -> models.User:
    """FastAPI dependency to extract and validate the JWT Bearer token,

    resolving the authenticated user from PostgreSQL.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if auth is None or not auth.credentials or auth.scheme.lower() != "bearer":
        raise credentials_exception

    try:
        payload = decode_access_token(auth.credentials)
    except (jwt.PyJWTError, ValueError):
        raise credentials_exception

    sub = payload.get("sub")
    if sub is None:
        raise credentials_exception

    try:
        user_id = int(sub)
    except (ValueError, TypeError):
        raise credentials_exception

    user = db.execute(
        select(models.User).where(models.User.id == user_id)
    ).scalar_one_or_none()

    if user is None or not user.is_active:
        raise credentials_exception

    return user

