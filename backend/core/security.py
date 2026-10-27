"""
JWT-based authentication and password hashing utilities.

Password hashing uses bcrypt via passlib.
Token signing uses HS256 via python-jose.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import get_settings
from backend.core.database import get_db

settings = get_settings()

# ------------------------------------------------------------------ #
# Password hashing
# ------------------------------------------------------------------ #
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Return a bcrypt hash of *password*."""
    return _pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Return ``True`` if *plain* matches *hashed*."""
    return _pwd_context.verify(plain, hashed)


# ------------------------------------------------------------------ #
# JWT
# ------------------------------------------------------------------ #
_ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Encode *data* as a signed JWT.

    Args:
        data: Payload to embed in the token.  ``sub`` should be the user id.
        expires_delta: Custom expiry.  Defaults to ``JWT_EXPIRE_MINUTES``.

    Returns:
        Signed JWT string.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=_ALGORITHM)


def verify_token(token: str) -> Optional[dict]:
    """Decode and verify *token*.

    Returns:
        The decoded payload dict, or ``None`` if the token is invalid or
        expired.
    """
    try:
        payload: dict = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[_ALGORITHM],
        )
        return payload
    except JWTError:
        return None


# ------------------------------------------------------------------ #
# FastAPI dependency
# ------------------------------------------------------------------ #
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):
    """FastAPI dependency that resolves the current authenticated user.

    Raises ``HTTP 401`` if the token is missing, expired, or refers to a
    non-existent / inactive user.
    """
    # Inline import avoids circular import at module load time.
    from backend.models.user import User  # noqa: PLC0415

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = verify_token(token)
    if payload is None:
        raise credentials_exception

    user_id: Optional[str] = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )
    return user
