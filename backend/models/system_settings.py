"""SystemSettings and ApiUsageLog models."""

from __future__ import annotations

import uuid
from typing import Optional

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import BaseModel


class SystemSetting(BaseModel):
    """Key-value system setting."""

    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(sa.String(128), unique=True, nullable=False, index=True)
    value: Mapped[str] = mapped_column(sa.Text, nullable=False)
    value_type: Mapped[str] = mapped_column(sa.String(32), default="string", nullable=False)
    description: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)

    def __repr__(self) -> str:
        return f"<SystemSetting {self.key}={self.value!r}>"


class ApiUsageLog(BaseModel):
    """Granular log of every outbound API / model invocation."""

    __tablename__ = "api_usage_logs"

    account_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        sa.ForeignKey("provider_accounts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    provider_name: Mapped[str] = mapped_column(sa.String(100), nullable=False, index=True)
    model_name: Mapped[Optional[str]] = mapped_column(sa.String(100), nullable=True)
    job_id: Mapped[Optional[str]] = mapped_column(sa.String(100), nullable=True, index=True)
    scene_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        sa.ForeignKey("scenes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    operation: Mapped[str] = mapped_column(sa.String(64), nullable=False)  # text_generation, video_generation, etc.
    input_tokens: Mapped[Optional[int]] = mapped_column(sa.Integer, nullable=True)
    output_tokens: Mapped[Optional[int]] = mapped_column(sa.Integer, nullable=True)
    duration_ms: Mapped[int] = mapped_column(sa.Integer, default=0, nullable=False)
    success: Mapped[bool] = mapped_column(sa.Boolean, default=True, nullable=False)
    error_type: Mapped[Optional[str]] = mapped_column(sa.String(64), nullable=True)
    estimated_cost: Mapped[Optional[float]] = mapped_column(sa.Float, nullable=True)

    def __repr__(self) -> str:
        return f"<ApiUsageLog provider={self.provider_name} op={self.operation} success={self.success}>"
