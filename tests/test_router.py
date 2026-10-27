"""Tests for Provider Scorer, Error Classification, and Account Rotation."""

import datetime
from unittest.mock import MagicMock

from backend.providers.base.provider_interface import BaseProvider, ErrorType
from backend.services.provider_router.scorer import ProviderScorer


def test_error_classification():
    class DummyProvider(BaseProvider):
        name = "dummy"
        display_name = "Dummy"
        capabilities = []
        async def health_check(self):
            pass

    provider = DummyProvider()

    # HTTP 401/403 -> AUTH_ERROR
    assert provider.classify_error(Exception("unauthorized"), http_status=401) == ErrorType.AUTH_ERROR
    assert provider.classify_error(Exception("forbidden"), http_status=403) == ErrorType.AUTH_ERROR

    # HTTP 429 -> RATE_LIMIT
    assert provider.classify_error(Exception("rate limited"), http_status=429) == ErrorType.RATE_LIMIT

    # Quota string -> QUOTA_EXCEEDED
    assert provider.classify_error(Exception("Resource has been exhausted: quota exceeded")) == ErrorType.QUOTA_EXCEEDED

    # Timeout string -> TIMEOUT
    assert provider.classify_error(Exception("Connection timed out")) == ErrorType.TIMEOUT


def test_scorer_quality_modes():
    scorer = ProviderScorer()

    mock_account = MagicMock()
    mock_account.id = "test-acc-1"
    mock_account.is_active = True
    mock_account.is_healthy = True
    mock_account.cooldown_until = None
    mock_account.allow_paid_usage = True
    mock_account.daily_spend_limit = 100.0
    mock_account.success_count = 10
    mock_account.failure_count = 0
    mock_account.priority = 1
    mock_account.last_error_at = None

    local_provider = MagicMock()
    local_provider.name = "local_comfyui"
    local_provider.supports_local = True

    cloud_provider = MagicMock()
    cloud_provider.name = "fal_video"
    cloud_provider.supports_local = False

    # In 'local' mode, local provider score must dominate cloud provider
    score_local = scorer.score_account(mock_account, local_provider, quality_mode="local")
    score_cloud = scorer.score_account(mock_account, cloud_provider, quality_mode="local")

    assert score_local.is_eligible
    assert score_cloud.is_eligible
    assert score_local.total_score > score_cloud.total_score


def test_scorer_cooldown_rejection():
    scorer = ProviderScorer()

    mock_account = MagicMock()
    mock_account.id = "test-acc-cooldown"
    mock_account.is_active = True
    mock_account.is_healthy = True
    # In future cooldown
    mock_account.cooldown_until = datetime.datetime.utcnow() + datetime.timedelta(minutes=15)

    mock_provider = MagicMock()
    mock_provider.name = "google_gemini"

    score = scorer.score_account(mock_account, mock_provider)
    assert not score.is_eligible
    assert "cooldown" in score.ineligible_reason.lower()
