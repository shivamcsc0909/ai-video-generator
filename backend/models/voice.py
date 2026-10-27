"""Voice and VoiceProfile models."""

from __future__ import annotations

from typing import Any, Optional

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import BaseModel


class VoiceProfile(BaseModel):
    """A TTS voice profile available for narration."""

    __tablename__ = "voice_profiles"
    __table_args__ = (
        sa.Index("ix_voice_profiles_provider_language", "provider", "language"),
        sa.UniqueConstraint("provider", "voice_id", name="uq_voice_provider_voice_id"),
    )

    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    provider: Mapped[str] = mapped_column(sa.String(100), nullable=False, index=True)
    voice_id: Mapped[str] = mapped_column(sa.String(255), nullable=False)

    language: Mapped[Optional[str]] = mapped_column(sa.String(10), nullable=True, index=True)
    accent: Mapped[Optional[str]] = mapped_column(sa.String(100), nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(sa.String(20), nullable=True)
    age_style: Mapped[Optional[str]] = mapped_column(sa.String(50), nullable=True)
    sample_url: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)

    is_local: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)
    is_enabled: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)

    # Provider-specific metadata (e.g. ElevenLabs voice settings, Coqui model name)
    provider_metadata: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True, default=dict)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<VoiceProfile id={self.id} name={self.name!r} provider={self.provider!r}>"
