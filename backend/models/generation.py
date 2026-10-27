"""Generation model — tracks a full pipeline run for a project."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any, Optional

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import BaseModel


class GenerationStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    ANALYZING = "ANALYZING"
    STORYBOARDING = "STORYBOARDING"
    GENERATING_IMAGES = "GENERATING_IMAGES"
    GENERATING_VIDEO = "GENERATING_VIDEO"
    GENERATING_VOICE = "GENERATING_VOICE"
    SYNCING = "SYNCING"
    COMPOSITING = "COMPOSITING"
    ADDING_SUBTITLES = "ADDING_SUBTITLES"
    QUALITY_CHECK = "QUALITY_CHECK"
    EXPORTING = "EXPORTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class Generation(BaseModel):
    """Represents one full pipeline execution for a project."""

    __tablename__ = "generations"
    __table_args__ = (
        sa.Index("ix_generations_project_id_status", "project_id", "status"),
        sa.Index("ix_generations_user_id", "user_id"),
        sa.Index("ix_generations_created_at", "created_at"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Celery task tracking
    celery_task_id: Mapped[Optional[str]] = mapped_column(sa.String(255), nullable=True, index=True)

    # Status & progress
    status: Mapped[GenerationStatus] = mapped_column(
        sa.Enum(GenerationStatus, name="generationstatus"),
        nullable=False,
        default=GenerationStatus.QUEUED,
        index=True,
    )
    current_step: Mapped[Optional[str]] = mapped_column(sa.String(255), nullable=True)
    progress_percent: Mapped[float] = mapped_column(sa.Float, nullable=False, default=0.0)

    # Scene counters
    total_scenes: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    completed_scenes: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    failed_scenes: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)

    # Error info
    error_message: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)

    # Cost tracking
    estimated_cost: Mapped[Optional[float]] = mapped_column(sa.Float, nullable=True)
    actual_cost: Mapped[Optional[float]] = mapped_column(sa.Float, nullable=True)

    # Output
    output_path: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    duration_seconds: Mapped[Optional[float]] = mapped_column(sa.Float, nullable=True)

    # Pipeline plan (provider selections, scene plan, etc.)
    generation_plan: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True, default=dict)

    # Timing
    started_at: Mapped[Optional[datetime]] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(sa.DateTime(timezone=True), nullable=True)

    # ------------------------------------------------------------------ #
    # Relationships
    # ------------------------------------------------------------------ #
    project: Mapped["Project"] = relationship("Project", back_populates="generations")
    scenes: Mapped[list["Scene"]] = relationship(  # noqa: F821
        "Scene", back_populates="generation"
    )
    render_history: Mapped[list["RenderHistory"]] = relationship(  # noqa: F821
        "RenderHistory", back_populates="generation", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Generation id={self.id} status={self.status} progress={self.progress_percent:.1f}%>"
