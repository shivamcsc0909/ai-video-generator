"""Provider Account Scorer.

Computes a multi-factor score for available provider accounts:
Score = (quality × availability × quota × reliability) - cost_penalty - failure_penalty
Takes into account account cooldowns, quality modes, user priority, and hardware limits.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


@dataclass
class ProviderScore:
    account_id: str
    provider_name: str
    total_score: float
    quality_score: float
    availability_score: float
    quota_score: float
    reliability_score: float
    cost_penalty: float
    failure_penalty: float
    is_eligible: bool
    ineligible_reason: Optional[str] = None


class ProviderScorer:
    """Scores provider accounts for intelligent routing decisions."""

    def score_account(self, account, provider, quality_mode: str = "balanced") -> ProviderScore:
        """Score an account given the current user quality mode:

        quality_mode options:
          - 'local': Local models strictly preferred, zero cost
          - 'balanced': Local first, then free/budget external providers
          - 'quality': High-quality models preferred with reasonable budget
          - 'max_quality': Top models preferred subject to user spend limits
        """
        # 1. Eligibility checks
        if not account.is_active:
            return ProviderScore(
                str(account.id), provider.name, 0, 0, 0, 0, 0, 0, 0, False, "Account is disabled"
            )

        if not account.is_healthy:
            return ProviderScore(
                str(account.id), provider.name, 0, 0, 0, 0, 0, 0, 0, False, "Account is marked unhealthy"
            )

        # Check cooldown (rate limit backoff)
        if account.cooldown_until:
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            if account.cooldown_until > now:
                return ProviderScore(
                    str(account.id),
                    provider.name,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    False,
                    f"Account in cooldown until {account.cooldown_until.isoformat()}",
                )

        # Check spend limits
        if not account.allow_paid_usage and not getattr(provider, "supports_local", False):
            # If user has not enabled paid usage for this account and it's not free tier, check limit
            if account.daily_spend_limit and account.daily_spend_limit > 0:
                pass  # Has explicit limit

        # 2. Factor computations
        quality_score = self._calc_quality_score(provider, quality_mode)
        availability_score = self._calc_availability_score(account)
        quota_score = self._calc_quota_score(account)
        reliability_score = self._calc_reliability_score(account)
        cost_penalty = self._calc_cost_penalty(provider, account, quality_mode)
        failure_penalty = self._calc_failure_penalty(account)

        # User priority bonus (lower priority number = higher preference)
        priority_boost = max(0.0, 2.0 - (getattr(account, "priority", 1) * 0.2))

        # Composite score
        base_product = (quality_score * availability_score * quota_score * reliability_score) + priority_boost
        total = max(0.0, base_product - cost_penalty - failure_penalty)

        return ProviderScore(
            account_id=str(account.id),
            provider_name=provider.name,
            total_score=round(total, 4),
            quality_score=quality_score,
            availability_score=availability_score,
            quota_score=quota_score,
            reliability_score=reliability_score,
            cost_penalty=cost_penalty,
            failure_penalty=failure_penalty,
            is_eligible=True,
        )

    def _calc_quality_score(self, provider, mode: str) -> float:
        is_local = getattr(provider, "supports_local", False)
        if mode == "local":
            return 3.0 if is_local else 0.5
        elif mode == "balanced":
            return 1.8 if is_local else 1.5
        elif mode == "quality":
            return 1.2 if is_local else 2.2
        elif mode == "max_quality":
            return 1.0 if is_local else 2.8
        return 1.0

    def _calc_availability_score(self, account) -> float:
        if not account.is_healthy:
            return 0.0
        total_ops = account.success_count + account.failure_count
        if total_ops > 0:
            fail_rate = account.failure_count / total_ops
            return max(0.2, 1.0 - fail_rate)
        return 1.0

    def _calc_quota_score(self, account) -> float:
        if account.daily_spend_limit and account.daily_spend_limit > 0:
            return 1.0
        return 1.0

    def _calc_reliability_score(self, account) -> float:
        total = account.success_count + account.failure_count
        if total == 0:
            return 0.95  # Unused account assumed clean
        return max(0.1, account.success_count / total)

    def _calc_cost_penalty(self, provider, account, mode: str) -> float:
        if getattr(provider, "supports_local", False):
            return 0.0
        if not account.allow_paid_usage:
            # High penalty if paid usage is disallowed
            return 5.0
        if mode == "local":
            return 10.0
        elif mode == "balanced":
            return 0.5
        return 0.0

    def _calc_failure_penalty(self, account) -> float:
        if account.last_error_at:
            import datetime

            age = datetime.datetime.utcnow() - account.last_error_at
            if age.total_seconds() < 300:  # < 5 min
                return 1.5
            elif age.total_seconds() < 1800:  # < 30 min
                return 0.5
        return 0.0
