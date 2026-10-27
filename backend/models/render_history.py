"""RenderHistory model — records each completed render output."""

from __future__ import annotations

import uuid
from typing import Optional

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import BaseModel


class RenderHistory(BaseModel):
    """Immutable record of a completed video render."""

    __tablename__ = "render_history"
    __table_args__ = (
        sa.Index("ix_render_history_project_id", "project_id"),
        sa.Index("ix_render_history_generation_id", "generation_id"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    generation_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("generations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    output_path: Mapped[str] = mapped_column(sa.Text, nullable=False)
    output_format: Mapped[str] = mapped_column(sa.String(20), nullable=False)  # e.g. "mp4"
    resolution: Mapped[str] = mapped_column(sa.String(20), nullable=False)    # e.g. "1920x1080"
    fps: Mapped[float] = mapped_column(sa.Float, nullable=False)
    duration_seconds: Mapped[float] = mapped_column(sa.Float, nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(sa.BigInteger, nullable=False)
    codec: Mapped[Optional[str]] = mapped_column(sa.String(50), nullable=True)
    bitrate: Mapped[Optional[int]] = mapped_column(sa.Integer, nullable=True)

    # ------------------------------------------------------------------ #
    # Relationships
    # ------------------------------------------------------------------ #
    project: Mapped["Project"] = relationship("Project", back_populates="render_history")
    generation: Mapped["Generation"] = relationship("Generation", back_populates="render_history")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<RenderHistory id={self.id} project={self.project_id}>"
