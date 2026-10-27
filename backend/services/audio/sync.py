"""Audio-Video Synchronization Engine.

Calculates speech narration duration vs planned visual scene durations,
handles dynamic scene pacing, and prevents aggressive speech speeding.
"""

from __future__ import annotations

import os
from typing import List, Tuple

import structlog

logger = structlog.get_logger(__name__)


class AudioSyncEngine:
    """Synchronizes audio tracks with visual scene timings."""

    @staticmethod
    def estimate_speech_duration(text: str, words_per_minute: int = 150) -> float:
        """Estimates spoken audio duration in seconds based on word count."""
        words = len(text.strip().split())
        if words == 0:
            return 0.0
        return max(2.0, (words / float(words_per_minute)) * 60.0)

    @staticmethod
    def balance_scene_durations(
        scene_durations: List[float],
        audio_duration: float,
    ) -> List[float]:
        """Adjusts visual scene durations so the video timeline naturally accommodates narration.

        Never speeds up speech aggressively; instead, proportionately pads scene runtimes.
        """
        if not scene_durations:
            return [max(5.0, audio_duration)]

        total_video = sum(scene_durations)
        if total_video <= 0:
            return [max(5.0, audio_duration)]

        # If audio is longer than planned video, gently expand scenes
        if audio_duration > total_video:
            scale_factor = (audio_duration + 2.0) / total_video  # 2s safety buffer
            # Cap scale factor to avoid absurdly long static scenes
            scale_factor = min(scale_factor, 1.8)
            return [round(d * scale_factor, 1) for d in scene_durations]

        return scene_durations
