"""Scene model — one unit of a generation pipeline."""

from __future__ import annotations

import enum
import uuid
from typing import Any, Optional

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import BaseModel


class SceneStatus(str, enum.Enum):
    pending = "pending"
    generating = "generating"
    completed = "completed"
    failed = "failed"


class Scene(BaseModel):
    """A single scene within a project / generation run."""

    __tablename__ = "scenes"
    __table_args__ = (
        sa.Index("ix_scenes_project_id_number", "project_id", "scene_number"),
        sa.Index("ix_scenes_generation_id", "generation_id"),
        sa.Index("ix_scenes_status", "status"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    generation_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("generations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Scene metadata
    scene_number: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    title: Mapped[Optional[str]] = mapped_column(sa.String(255), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    duration_seconds: Mapped[float] = mapped_column(sa.Float, nullable=False, default=5.0)
    status: Mapped[SceneStatus] = mapped_column(
        sa.Enum(SceneStatus, name="scenestatus"),
        nullable=False,
        default=SceneStatus.pending,
        index=True,
    )

    # Cinematography
    shot_type: Mapped[Optional[str]] = mapped_column(sa.String(100), nullable=True)
    camera_movement: Mapped[Optional[str]] = mapped_column(sa.String(100), nullable=True)
    environment: Mapped[Optional[str]] = mapped_column(sa.String(255), nullable=True)
    lighting: Mapped[Optional[str]] = mapped_column(sa.String(255), nullable=True)

    # Creative content
    voice_over: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    music_mood: Mapped[Optional[str]] = mapped_column(sa.String(100), nullable=True)
    sfx_description: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    transition_in: Mapped[Optional[str]] = mapped_column(sa.String(100), nullable=True)
    transition_out: Mapped[Optional[str]] = mapped_column(sa.String(100), nullable=True)
    continuity_notes: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)

    # Prompts
    image_prompt: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    video_prompt: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    negative_prompt: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)

    # Provider / model tracking
    provider_used: Mapped[Optional[str]] = mapped_column(sa.String(100), nullable=True)
    model_used: Mapped[Optional[str]] = mapped_column(sa.String(100), nullable=True)

    # Output paths
    image_path: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    video_path: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    audio_path: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)

    # Error handling
    retry_count: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)

    # Generation parameters (seed, steps, cfg, etc.)
    generation_params: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True, default=dict)

    # ------------------------------------------------------------------ #
    # Relationships
    # ------------------------------------------------------------------ #
    project: Mapped["Project"] = relationship("Project", back_populates="scenes")
    generation: Mapped[Optional["Generation"]] = relationship("Generation", back_populates="scenes")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Scene id={self.id} number={self.scene_number} status={self.status}>"
