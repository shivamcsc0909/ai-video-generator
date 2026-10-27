"""Authentication and local user management endpoints."""

from __future__ import annotations

from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import get_settings
from backend.core.database import get_db
from backend.core.security import create_access_token, get_current_user, hash_password, verify_password
from backend.models.user import User
from backend.schemas.auth import Token, UserCreate, UserResponse

router = APIRouter()
settings = get_settings()


@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """Authenticate with username and password, returns JWT."""
    stmt = select(User).where(User.username == form_data.username)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    expires = timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    token = create_access_token(
        data={"sub": user.username, "user_id": str(user.id)},
        expires_delta=expires,
    )
    return Token(access_token=token, token_type="bearer")


@router.post("/register", response_model=UserResponse)
async def register_first_user(
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create local admin account if no user exists."""
    stmt = select(User)
    res = await db.execute(stmt)
    existing_users = res.scalars().all()

    # If users already exist, only existing admin can create new accounts
    if existing_users:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin user already configured. Please log in.",
        )

    user = User(
        username=data.username,
        email=data.email,
        hashed_password=hash_password(data.password),
        is_active=True,
        is_admin=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
):
    """Returns profile of currently authenticated user."""
    return current_user
