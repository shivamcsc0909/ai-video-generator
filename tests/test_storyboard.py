"""Tests for AI Storyboard Engine."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from backend.services.storyboard.engine import StoryboardEngine


@pytest.mark.asyncio
async def test_heuristic_storyboard_generation():
    mock_router = MagicMock()
    # Mock LLM failure to force heuristic fallback
    mock_router.route_text_generation = AsyncMock(return_value=MagicMock(success=False, error_message="LLM unavailable"))

    engine = StoryboardEngine(mock_router)
    storyboard = await engine.generate_storyboard(
        prompt="Create a commercial advertisement for a luxury smartwatch",
        project_type="advertisement",
        target_duration=60,
    )

    assert storyboard is not None
    assert len(storyboard.scenes) >= 3
    assert storyboard.total_duration > 0
    assert "smartwatch" in storyboard.title.lower() or "advertisement" in storyboard.title.lower()
    for sc in storyboard.scenes:
        assert sc.duration_seconds > 0
        assert sc.shot_type is not None
        assert sc.camera_movement is not None
