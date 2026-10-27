"""Secure AI Provider and Multi-Account Credential Management API.

SECURITY MANDATES:
- NEVER return raw API keys in any API response.
- Encrypt API keys with Fernet before persisting to PostgreSQL.
- Only return masked `key_hint` (e.g. ************ABCD) for identification.
- Never log plain credentials.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from backend.core.database import get_db
from backend.core.security import get_current_user
from backend.models.provider import (
    Provider,
    ProviderAccount,
    ProviderFailure,
    ProviderType,
    ProviderUsage,
)
from backend.models.user import User
from backend.schemas.provider import (
    ProviderAccountCreate,
    ProviderAccountResponse,
    ProviderAccountUpdate,
    ProviderResponse,
    ProviderTestResult,
    ProviderUsageSummary,
)
from backend.services.credentials.encryption import get_encryption_service

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.get("/", response_model=List[ProviderResponse])
async def list_providers(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all supported AI providers and their capabilities."""
    stmt = select(Provider).order_by(Provider.name)
    res = await db.execute(stmt)
    providers = res.scalars().all()
    return providers


@router.get("/accounts", response_model=List[ProviderAccountResponse])
async def list_provider_accounts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all configured provider accounts.

    SECURITY: Returns `key_hint` (masked), NEVER the raw secret.
    """
    stmt = (
        select(ProviderAccount)
        .where(ProviderAccount.user_id == current_user.id)
        .order_by(ProviderAccount.priority, ProviderAccount.account_name)
    )
    res = await db.execute(stmt)
    accounts = res.scalars().all()
    return accounts


@router.post("/accounts", response_model=ProviderAccountResponse, status_code=status.HTTP_201_CREATED)
async def create_provider_account(
    data: ProviderAccountCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a new provider credential.

    Encrypts the key server-side immediately and generates a safe masked hint.
    """
    provider = await db.get(Provider, data.provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    encrypted_key = None
    key_hint = None

    if data.api_key and data.api_key.strip():
        encryption = get_encryption_service()
        encrypted_key = encryption.encrypt(data.api_key.strip())
        key_hint = encryption.get_key_hint(data.api_key.strip())
    elif not provider.supports_local:
        raise HTTPException(
            status_code=400,
            detail=f"Provider '{provider.display_name}' requires an API key.",
        )
    else:
        key_hint = "LOCAL-ENGINE"

    account = ProviderAccount(
        provider_id=provider.id,
        user_id=current_user.id,
        account_name=data.account_name.strip(),
        encrypted_api_key=encrypted_key,
        key_hint=key_hint,
        priority=data.priority,
        allow_paid_usage=data.allow_paid_usage,
        daily_spend_limit=data.daily_spend_limit,
        monthly_spend_limit=data.monthly_spend_limit,
        custom_settings=data.custom_settings or {},
        is_active=True,
        is_healthy=True,
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)

    logger.info(
        "provider_account_added",
        account_name=account.account_name,
        provider=provider.name,
        key_hint=key_hint,
    )
    return account


@router.put("/accounts/{account_id}", response_model=ProviderAccountResponse)
async def update_provider_account(
    account_id: uuid.UUID,
    data: ProviderAccountUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update settings for an account. If `api_key` is provided, rotates and re-encrypts it."""
    account = await db.get(ProviderAccount, account_id)
    if not account or account.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Provider account not found")

    if data.account_name is not None:
        account.account_name = data.account_name.strip()
    if data.priority is not None:
        account.priority = data.priority
    if data.is_active is not None:
        account.is_active = data.is_active
    if data.allow_paid_usage is not None:
        account.allow_paid_usage = data.allow_paid_usage
    if data.daily_spend_limit is not None:
        account.daily_spend_limit = data.daily_spend_limit
    if data.monthly_spend_limit is not None:
        account.monthly_spend_limit = data.monthly_spend_limit

    # Key rotation
    if data.api_key and data.api_key.strip():
        encryption = get_encryption_service()
        account.encrypted_api_key = encryption.encrypt(data.api_key.strip())
        account.key_hint = encryption.get_key_hint(data.api_key.strip())
        account.is_healthy = True
        account.last_error_message = None
        account.cooldown_until = None
        logger.info("provider_key_rotated", account=account.account_name)

    await db.commit()
    await db.refresh(account)
    return account


@router.delete("/accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_provider_account(
    account_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a provider account."""
    account = await db.get(ProviderAccount, account_id)
    if not account or account.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Provider account not found")

    await db.delete(account)
    await db.commit()


@router.post("/accounts/{account_id}/test", response_model=ProviderTestResult)
async def test_provider_connection(
    account_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Live connection and authentication check with external or local provider."""
    account = await db.get(ProviderAccount, account_id)
    if not account or account.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Provider account not found")

    provider = await db.get(Provider, account.provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider definition not found")

    # Decrypt credential
    raw_key = ""
    if not provider.supports_local:
        if not account.encrypted_api_key:
            return ProviderTestResult(success=False, message="No API key configured for account.")
        encryption = get_encryption_service()
        try:
            raw_key = encryption.decrypt(account.encrypted_api_key)
        except Exception as e:
            return ProviderTestResult(success=False, message=f"Decryption failed: {str(e)}")

    # Instantiate provider adapter
    start_time = datetime.utcnow()
    try:
        from backend.services.provider_router.router import ProviderRouter

        router_svc = ProviderRouter(db)
        instance = router_svc._create_remote_provider(provider, raw_key) if not provider.supports_local else router_svc._create_local_provider(provider)

        if not instance:
            return ProviderTestResult(success=False, message=f"Provider adapter '{provider.name}' not ready.")

        health = await instance.health_check()
        lat_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        # Update account health in DB
        account.is_healthy = health.is_available
        if health.is_available:
            account.last_success_at = datetime.utcnow()
            account.last_error_message = None
            account.cooldown_until = None
        else:
            account.last_error_at = datetime.utcnow()
            account.last_error_message = health.error_message
        await db.commit()

        return ProviderTestResult(
            success=health.is_available,
            latency_ms=lat_ms,
            quota_status=health.quota_status,
            message="Connection successful!" if health.is_available else (health.error_message or "Connection failed"),
        )

    except Exception as e:
        account.is_healthy = False
        account.last_error_at = datetime.utcnow()
        account.last_error_message = str(e)[:300]
        await db.commit()
        return ProviderTestResult(
            success=False,
            message=f"Test failed with exception: {str(e)}",
        )


@router.get("/usage-summary", response_model=List[ProviderUsageSummary])
async def get_provider_usage_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns dashboard metrics across all user accounts: requests today, success rate, cost, status."""
    stmt = (
        select(ProviderAccount, Provider)
        .join(Provider, ProviderAccount.provider_id == Provider.id)
        .where(ProviderAccount.user_id == current_user.id)
    )
    res = await db.execute(stmt)
    rows = res.all()

    summaries = []
    for acc, prov in rows:
        total = acc.success_count + acc.failure_count
        rate = round((acc.success_count / total) * 100.0, 1) if total > 0 else 100.0

        status_label = "HEALTHY"
        if not acc.is_active:
            status_label = "DISABLED"
        elif not acc.is_healthy:
            status_label = "ERROR"
        elif acc.cooldown_until and acc.cooldown_until > datetime.utcnow():
            status_label = "COOLDOWN"

        summaries.append(
            ProviderUsageSummary(
                account_id=acc.id,
                account_name=acc.account_name,
                provider_name=prov.display_name,
                requests_today=acc.daily_request_count,
                success_rate=rate,
                estimated_cost_today=0.0,
                status=status_label,
                cooldown_until=acc.cooldown_until,
            )
        )

    return summaries
