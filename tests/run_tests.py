"""Comprehensive test runner using Python standard library unittest.

Executes:
- Fernet Credential Encryption & Key Masking (At-Rest Security)
- Provider Scorer & Quality Mode Calculations
- Rate Limit & Cooldown Protection
- AI Storyboard Engine & Heuristic Scene Generation
- Media Pipeline Fallback Synthetic Clip Generation
"""

import sys
import os
import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tests.test_encryption import (
    test_encryption_decryption_cycle,
    test_key_hint_masking,
    test_cannot_encrypt_empty,
)
from tests.test_router import (
    test_error_classification,
    test_scorer_quality_modes,
    test_scorer_cooldown_rejection,
)
from backend.services.storyboard.engine import StoryboardEngine
from backend.services.ffmpeg.pipeline import FFmpegPipeline


class TestAIVideoStudio(unittest.TestCase):
    def test_encryption_cycle(self):
        test_encryption_decryption_cycle()

    def test_key_hint(self):
        test_key_hint_masking()

    def test_empty_encryption(self):
        test_cannot_encrypt_empty()

    def test_errors(self):
        test_error_classification()

    def test_scores(self):
        test_scorer_quality_modes()

    def test_cooldown(self):
        test_scorer_cooldown_rejection()

    def test_storyboard_generation(self):
        async def _run():
            mock_router = MagicMock()
            mock_router.route_text_generation = AsyncMock(
                return_value=MagicMock(success=False, error_message="LLM simulated offline")
            )
            engine = StoryboardEngine(mock_router)
            sb = await engine.generate_storyboard(
                prompt="Create a cinematic ad for a penthouse suite",
                project_type="advertisement",
                target_duration=60,
            )
            self.assertIsNotNone(sb)
            self.assertGreaterEqual(len(sb.scenes), 3)
            self.assertGreater(sb.total_duration, 0)
            for sc in sb.scenes:
                self.assertGreater(sc.duration_seconds, 0)
                self.assertTrue(bool(sc.shot_type))
                self.assertTrue(bool(sc.camera_movement))
                self.assertTrue(bool(sc.image_prompt))

        asyncio.run(_run())

    def test_media_pipeline_clip(self):
        async def _run():
            import tempfile
            pipeline = FFmpegPipeline()
            temp_out = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
            temp_out.close()
            try:
                res = await pipeline.create_color_clip(temp_out.name, duration=1.0, width=320, height=240)
                self.assertTrue(os.path.exists(res))
                self.assertGreater(os.path.getsize(res), 0)
            finally:
                if os.path.exists(temp_out.name):
                    os.remove(temp_out.name)

        asyncio.run(_run())


if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestAIVideoStudio)
    runner = unittest.TextTestRunner(verbosity=2)
    res = runner.run(suite)
    sys.exit(0 if res.wasSuccessful() else 1)
