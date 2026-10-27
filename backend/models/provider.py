"""Provider, ProviderAccount, ProviderUsage, and ProviderFailure models."""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from typing import Any, Optional

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import BaseModel


class ProviderType(str, enum.Enum):
    llm = "llm"
    video = "video"
    image = "image"
    tts = "tts"
    stt = "stt"


class Provider(BaseModel):
    """An AI service provider (e.g. Google Gemini, Replicate)."""

    __tablename__ = "providers"

    name: Mapped[str] = mapped_column(sa.String(100), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    provider_type: Mapped[ProviderType] = mapped_column(
        sa.Enum(ProviderType, name="providertype"),
        nullable=False,
        index=True,
    )
    description: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    website_url: Mapped[Optional[str]] = mapped_column(sa.String(512), nullable=True)

    is_enabled: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)
    supports_local: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)

    # List of capability strings, e.g. ["text_generation", "image_to_video"]
    capabilities: Mapped[Optional[list[str]]] = mapped_column(JSONB, nullable=True, default=list)

    # ------------------------------------------------------------------ #
    # Relationships
    # ------------------------------------------------------------------ #
    accounts: Mapped[list["ProviderAccount"]] = relationship(
        "ProviderAccount", back_populates="provider", cascade="all, delete-orphan"
    )
    model_registry: Mapped[list["ModelRegistry"]] = relationship(  # noqa: F821
        "ModelRegistry", back_populates="provider", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Provider id={self.id} name={self.name!r}>"


class ProviderAccount(BaseModel):
    """A user-configured API credential for a provider.

    The actual API key is stored encrypted via Fernet.  Only the last 4
    characters are stored as ``key_hint`` for display purposes.
    """

    __tablename__ = "provider_accounts"
    __table_args__ = (
        sa.Index("ix_provider_accounts_provider_user", "provider_id", "user_id"),
        sa.Index("ix_provider_accounts_is_active_healthy", "is_active", "is_healthy"),
    )

    provider_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("providers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    account_name: Mapped[str] = mapped_column(sa.String(255), nullable=False)

    # --- SECURITY NOTE --------------------------------------------------
    # The raw API key is NEVER stored.  ``encrypted_api_key`` holds the
    # Fernet-encrypted ciphertext.  ``key_hint`` is the last 4 plaintext
    # characters only, for UX display.
    # --------------------------------------------------------------------
    encrypted_api_key: Mapped[str] = mapped_column(sa.Text, nullable=False)
    key_hint: Mapped[Optional[str]] = mapped_column(sa.String(4), nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)
    is_healthy: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)
    priority: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=1)

    # Spending limits
    max_daily_spend: Mapped[Optional[float]] = mapped_column(sa.Float, nullable=True)
    max_monthly_spend: Mapped[Optional[float]] = mapped_column(sa.Float, nullable=True)
    daily_spend_limit: Mapped[Optional[float]] = mapped_column(sa.Float, nullable=True)
    monthly_spend_limit: Mapped[Optional[float]] = mapped_column(sa.Float, nullable=True)
    allow_paid_usage: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)

    # Usage counters (reset by periodic task)
    daily_request_count: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    monthly_request_count: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    daily_token_count: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    monthly_token_count: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)

    # Health tracking timestamps
    last_used_at: Mapped[Optional[datetime]] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    last_success_at: Mapped[Optional[datetime]] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    last_error_at: Mapped[Optional[datetime]] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    last_error_message: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    cooldown_until: Mapped[Optional[datetime]] = mapped_column(sa.DateTime(timezone=True), nullable=True, index=True)

    # Aggregate stats
    success_count: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    failure_count: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    avg_latency_ms: Mapped[Optional[float]] = mapped_column(sa.Float, nullable=True)

    # Provider-specific custom settings (rate limits, model overrides, etc.)
    custom_settings: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True, default=dict)

    # ------------------------------------------------------------------ #
    # Relationships
    # ------------------------------------------------------------------ #
    provider: Mapped["Provider"] = relationship("Provider", back_populates="accounts")
    user: Mapped["User"] = relationship("User", back_populates="provider_accounts")
    usage_records: Mapped[list["ProviderUsage"]] = relationship(
        "ProviderUsage", back_populates="account", cascade="all, delete-orphan"
    )
    failures: Mapped[list["ProviderFailure"]] = relationship(
        "ProviderFailure", back_populates="account", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ProviderAccount id={self.id} name={self.account_name!r}>"


class ProviderUsage(BaseModel):
    """Daily aggregated usage record for a provider account."""

    __tablename__ = "provider_usage"
    __table_args__ = (
        sa.UniqueConstraint("account_id", "date", name="uq_provider_usage_account_date"),
        sa.Index("ix_provider_usage_date", "date"),
    )

    account_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("provider_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    date: Mapped[date] = mapped_column(sa.Date, nullable=False)

    request_count: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    token_count: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    image_count: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    video_seconds: Mapped[float] = mapped_column(sa.Float, nullable=False, default=0.0)
    audio_characters: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)

    estimated_cost: Mapped[float] = mapped_column(sa.Float, nullable=False, default=0.0)
    actual_cost: Mapped[Optional[float]] = mapped_column(sa.Float, nullable=True)

    error_count: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)

    # ------------------------------------------------------------------ #
    # Relationships
    # ------------------------------------------------------------------ #
    account: Mapped["ProviderAccount"] = relationship("ProviderAccount", back_populates="usage_records")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ProviderUsage account={self.account_id} date={self.date}>"


class ProviderFailure(BaseModel):
    """Records an individual provider API failure event."""

    __tablename__ = "provider_failures"
    __table_args__ = (
        sa.Index("ix_provider_failures_account_id", "account_id"),
        sa.Index("ix_provider_failures_created_at", "created_at"),
    )

    account_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("provider_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    error_type: Mapped[str] = mapped_column(sa.String(100), nullable=False, index=True)
    error_message: Mapped[str] = mapped_column(sa.Text, nullable=False)
    http_status: Mapped[Optional[int]] = mapped_column(sa.Integer, nullable=True)
    retry_count: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    was_rotated: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)
    job_id: Mapped[Optional[str]] = mapped_column(sa.String(255), nullable=True, index=True)
    scene_id: Mapped[Optional[uuid.UUID]] = mapped_column(sa.UUID(as_uuid=True), nullable=True)

    # ------------------------------------------------------------------ #
    # Relationships
    # ------------------------------------------------------------------ #
    account: Mapped["ProviderAccount"] = relationship("ProviderAccount", back_populates="failures")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ProviderFailure id={self.id} type={self.error_type}>"
