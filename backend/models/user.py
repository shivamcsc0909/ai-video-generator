"""User model — single local admin account."""

from __future__ import annotations

from typing import Optional

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import BaseModel


class User(BaseModel):
    """Represents an application user (typically the single local admin)."""

    __tablename__ = "users"

    username: Mapped[str] = mapped_column(sa.String(100), unique=True, nullable=False, index=True)
    email: Mapped[Optional[str]] = mapped_column(sa.String(255), unique=True, nullable=True, index=True)
    hashed_password: Mapped[str] = mapped_column(sa.Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, default=True, nullable=False)
    is_admin: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)

    # ------------------------------------------------------------------ #
    # Relationships
    # ------------------------------------------------------------------ #
    projects: Mapped[list["Project"]] = relationship(  # noqa: F821
        "Project", back_populates="user", cascade="all, delete-orphan"
    )
    assets: Mapped[list["Asset"]] = relationship(  # noqa: F821
        "Asset", back_populates="user"
    )
    provider_accounts: Mapped[list["ProviderAccount"]] = relationship(  # noqa: F821
        "ProviderAccount", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User id={self.id} username={self.username!r}>"
