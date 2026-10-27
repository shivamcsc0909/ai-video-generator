"""ModelRegistry — tracks AI models available through each provider."""

from __future__ import annotations

import enum
import uuid
from typing import Any, Optional

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import BaseModel


class CostType(str, enum.Enum):
    free = "free"
    per_request = "per_request"
    per_token = "per_token"
    per_second = "per_second"
    subscription = "subscription"


class ModelRegistry(BaseModel):
    """Catalogues an AI model and its capabilities within a provider."""

    __tablename__ = "model_registry"
    __table_args__ = (
        sa.UniqueConstraint("provider_id", "model_id", name="uq_model_registry_provider_model"),
        sa.Index("ix_model_registry_provider_enabled", "provider_id", "is_enabled"),
    )

    provider_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("providers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    model_id: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    model_name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    version: Mapped[Optional[str]] = mapped_column(sa.String(100), nullable=True)

    # Capability list: ["text_to_video", "image_to_video", "text_generation", ...]
    capabilities: Mapped[Optional[list[str]]] = mapped_column(JSONB, nullable=True, default=list)

    # Media constraints
    max_video_duration: Mapped[Optional[float]] = mapped_column(sa.Float, nullable=True)
    max_resolution: Mapped[Optional[str]] = mapped_column(sa.String(20), nullable=True)
    supports_image_to_video: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)
    supports_text_to_video: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)

    # Hardware & performance
    hardware_requirements: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True, default=dict)
    estimated_speed: Mapped[Optional[str]] = mapped_column(
        sa.Enum("fast", "medium", "slow", name="modelspeed"),
        nullable=True,
    )

    # Quality & cost
    quality_rating: Mapped[Optional[float]] = mapped_column(sa.Float, nullable=True)  # 1.0 – 5.0
    cost_type: Mapped[CostType] = mapped_column(
        sa.Enum(CostType, name="costtype"),
        nullable=False,
        default=CostType.free,
    )
    cost_per_unit: Mapped[Optional[float]] = mapped_column(sa.Float, nullable=True)

    is_enabled: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)
    is_local: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)
    notes: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)

    # ------------------------------------------------------------------ #
    # Relationships
    # ------------------------------------------------------------------ #
    provider: Mapped["Provider"] = relationship("Provider", back_populates="model_registry")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ModelRegistry id={self.id} model_id={self.model_id!r}>"
