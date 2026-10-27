"""
Base mixin providing common columns for all ORM models.

All models should inherit from both ``Base`` and ``TimestampMixin`` (or
just subclass ``BaseModel`` which combines both).

Example::

    class MyModel(BaseModel):
        __tablename__ = "my_models"
        name: Mapped[str] = mapped_column(String(255))
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    """Adds ``created_at`` and ``updated_at`` columns."""

    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        default=_utcnow,
        nullable=False,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        default=_utcnow,
        onupdate=_utcnow,
        nullable=False,
    )


class BaseModel(Base, TimestampMixin):
    """Abstract base class combining the declarative base with common columns.

    Subclasses must define ``__tablename__``.
    """

    __abstract__ = True

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
