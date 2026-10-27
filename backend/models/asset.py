"""Asset model — uploaded or generated media files."""

from __future__ import annotations

import enum
import uuid
from typing import Any, Optional

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import BaseModel


class AssetType(str, enum.Enum):
    reference_image = "reference_image"
    character_image = "character_image"
    product_image = "product_image"
    architecture_image = "architecture_image"
    style_image = "style_image"
    logo = "logo"
    audio = "audio"
    video = "video"
    output_video = "output_video"
    storyboard = "storyboard"


class AssetPurpose(str, enum.Enum):
    character_reference = "character_reference"
    product_reference = "product_reference"
    location_reference = "location_reference"
    architecture_reference = "architecture_reference"
    style_reference = "style_reference"
    composition_reference = "composition_reference"
    general = "general"


class Asset(BaseModel):
    """A media file associated with a project or user."""

    __tablename__ = "assets"
    __table_args__ = (
        sa.Index("ix_assets_project_id_type", "project_id", "asset_type"),
        sa.Index("ix_assets_user_id", "user_id"),
    )

    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # File metadata
    filename: Mapped[str] = mapped_column(sa.String(512), nullable=False)
    original_filename: Mapped[str] = mapped_column(sa.String(512), nullable=False)
    file_path: Mapped[str] = mapped_column(sa.Text, nullable=False)
    file_size: Mapped[int] = mapped_column(sa.BigInteger, nullable=False)
    mime_type: Mapped[str] = mapped_column(sa.String(100), nullable=False)

    # Classification
    asset_type: Mapped[AssetType] = mapped_column(
        sa.Enum(AssetType, name="assettype"),
        nullable=False,
        index=True,
    )
    purpose: Mapped[AssetPurpose] = mapped_column(
        sa.Enum(AssetPurpose, name="assetpurpose"),
        nullable=False,
        default=AssetPurpose.general,
    )

    # Media dimensions
    width: Mapped[Optional[int]] = mapped_column(sa.Integer, nullable=True)
    height: Mapped[Optional[int]] = mapped_column(sa.Integer, nullable=True)
    duration_seconds: Mapped[Optional[float]] = mapped_column(sa.Float, nullable=True)

    # Extra metadata (EXIF, tags, etc.)
    metadata: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True, default=dict)

    # ------------------------------------------------------------------ #
    # Relationships
    # ------------------------------------------------------------------ #
    project: Mapped[Optional["Project"]] = relationship("Project", back_populates="assets")
    user: Mapped["User"] = relationship("User", back_populates="assets")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Asset id={self.id} type={self.asset_type} name={self.filename!r}>"
