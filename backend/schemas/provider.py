"""Provider and ProviderAccount schemas.

SECURITY: API keys are write-only on ingestion, encrypted immediately,
and never returned in responses. Only key_hint (last 4 chars) is exposed.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ProviderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    display_name: str
    provider_type: str
    description: Optional[str] = None
    website_url: Optional[str] = None
    is_enabled: bool
    supports_local: bool
    capabilities: Optional[List[str]] = None


class ProviderAccountCreate(BaseModel):
    provider_id: uuid.UUID
    account_name: str = Field(..., min_length=1, max_length=100)
    api_key: Optional[str] = None  # Write-only! Empty for local providers
    priority: int = 1
    allow_paid_usage: bool = False
    daily_spend_limit: Optional[float] = None
    monthly_spend_limit: Optional[float] = None
    custom_settings: Optional[Dict[str, Any]] = None


class ProviderAccountUpdate(BaseModel):
    account_name: Optional[str] = None
    api_key: Optional[str] = None  # If passed, replaces and re-encrypts
    priority: Optional[int] = None
    is_active: Optional[bool] = None
    allow_paid_usage: Optional[bool] = None
    daily_spend_limit: Optional[float] = None
    monthly_spend_limit: Optional[float] = None


class ProviderAccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    provider_id: uuid.UUID
    account_name: str
    key_hint: Optional[str] = None  # MASKED, e.g. ************ABCD. NEVER full key!
    is_active: bool
    is_healthy: bool
    priority: int
    allow_paid_usage: bool
    daily_spend_limit: Optional[float] = None
    monthly_spend_limit: Optional[float] = None
    daily_request_count: int
    success_count: int
    failure_count: int
    avg_latency_ms: Optional[float] = None
    last_used_at: Optional[datetime] = None
    last_success_at: Optional[datetime] = None
    last_error_at: Optional[datetime] = None
    last_error_message: Optional[str] = None
    cooldown_until: Optional[datetime] = None
    created_at: datetime


class ProviderTestResult(BaseModel):
    success: bool
    latency_ms: Optional[int] = None
    quota_status: str = "unknown"
    message: str


class ProviderUsageSummary(BaseModel):
    account_id: uuid.UUID
    account_name: str
    provider_name: str
    requests_today: int
    success_rate: float
    estimated_cost_today: float
    status: str
    cooldown_until: Optional[datetime] = None
