"""Project model."""

from __future__ import annotations

import enum
import uuid
from typing import Any, Optional

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import BaseModel


class ProjectType(str, enum.Enum):
    advertisement = "advertisement"
    cartoon = "cartoon"
    architecture = "architecture"
    product = "product"
    engineering = "engineering"
    educational = "educational"
    documentary = "documentary"
    story = "story"
    social_media = "social_media"
    explainer = "explainer"
    custom = "custom"


class ProjectStatus(str, enum.Enum):
    draft = "draft"
    in_progress = "in_progress"
    completed = "completed"
    failed = "failed"
    archived = "archived"


class Project(BaseModel):
    """A video production project."""

    __tablename__ = "projects"
    __table_args__ = (
        sa.Index("ix_projects_user_id_status", "user_id", "status"),
        sa.Index("ix_projects_created_at", "created_at"),
    )

    # Owner
    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Identity
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    project_type: Mapped[ProjectType] = mapped_column(
        sa.Enum(ProjectType, name="projecttype"),
        nullable=False,
        default=ProjectType.custom,
        index=True,
    )
    status: Mapped[ProjectStatus] = mapped_column(
        sa.Enum(ProjectStatus, name="projectstatus"),
        nullable=False,
        default=ProjectStatus.draft,
        index=True,
    )

    # Creative content
    prompt: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    script: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    target_duration: Mapped[Optional[int]] = mapped_column(sa.Integer, nullable=True)  # seconds

    # Video settings
    aspect_ratio: Mapped[str] = mapped_column(sa.String(10), nullable=False, default="16:9")
    quality_mode: Mapped[str] = mapped_column(sa.String(50), nullable=False, default="balanced")

    # Voice settings
    voice_language: Mapped[Optional[str]] = mapped_column(sa.String(10), nullable=True)
    voice_accent: Mapped[Optional[str]] = mapped_column(sa.String(50), nullable=True)
    voice_name: Mapped[Optional[str]] = mapped_column(sa.String(100), nullable=True)
    voice_emotion: Mapped[Optional[str]] = mapped_column(sa.String(50), nullable=True)
    voice_speed: Mapped[float] = mapped_column(sa.Float, nullable=False, default=1.0)

    # Feature flags
    include_subtitles: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)
    include_music: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)
    include_sfx: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)

    # Output
    output_path: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    thumbnail_path: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)

    # Flexible data
    settings: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True, default=dict)
    scene_bible: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True, default=dict)

    # ------------------------------------------------------------------ #
    # Relationships
    # ------------------------------------------------------------------ #
    user: Mapped["User"] = relationship("User", back_populates="projects")
    generations: Mapped[list["Generation"]] = relationship(  # noqa: F821
        "Generation", back_populates="project", cascade="all, delete-orphan"
    )
    scenes: Mapped[list["Scene"]] = relationship(  # noqa: F821
        "Scene", back_populates="project", cascade="all, delete-orphan"
    )
    assets: Mapped[list["Asset"]] = relationship(  # noqa: F821
        "Asset", back_populates="project"
    )
    render_history: Mapped[list["RenderHistory"]] = relationship(  # noqa: F821
        "RenderHistory", back_populates="project", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Project id={self.id} name={self.name!r} status={self.status}>"
