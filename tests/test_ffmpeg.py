"""Tests for FFmpeg pipeline and synthetic media fallback."""

import os
import tempfile
import pytest
from backend.services.ffmpeg.pipeline import FFmpegPipeline


@pytest.mark.asyncio
async def test_color_clip_generation():
    pipeline = FFmpegPipeline()
    temp_clip = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
    temp_clip.close()

    try:
        res = await pipeline.create_color_clip(
            output_path=temp_clip.name,
            duration=1.0,
            width=320,
            height=240,
        )
        assert os.path.exists(res)
        assert os.path.getsize(res) > 0
    finally:
        if os.path.exists(temp_clip.name):
            os.remove(temp_clip.name)
