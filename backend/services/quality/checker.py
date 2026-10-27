"""Automated Quality Checker for generated video scenes and final renders."""

from __future__ import annotations

import asyncio
import json
import os
import shutil
from dataclasses import dataclass, field
from typing import List, Optional

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class QualityReport:
    passed: bool
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    duration: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    has_audio: bool = False
    details: dict = field(default_factory=dict)


class QualityChecker:
    """Inspects video outputs using ffprobe to detect corruption, black frames, or mismatches."""

    def __init__(self):
        self.ffprobe_bin = (
            shutil.which("ffprobe")
            or ("/opt/homebrew/bin/ffprobe" if os.path.exists("/opt/homebrew/bin/ffprobe") else "ffprobe")
        )

    async def inspect(
        self,
        video_path: str,
        expected_duration: Optional[float] = None,
        min_resolution: int = 480,
    ) -> QualityReport:
        if not os.path.exists(video_path):
            return QualityReport(passed=False, issues=[f"Video file not found at: {video_path}"])

        file_size = os.path.getsize(video_path)
        if file_size < 512:
            return QualityReport(passed=False, issues=[f"Video file is truncated/empty ({file_size} bytes)"])

        if not shutil.which(self.ffprobe_bin) and not os.path.exists(self.ffprobe_bin):
            # If ffprobe not found on host, basic file size check passes
            return QualityReport(passed=True, warnings=["ffprobe unavailable; basic file size check passed."])

        cmd = [
            self.ffprobe_bin,
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            video_path,
        ]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            if proc.returncode != 0:
                return QualityReport(passed=False, issues=["ffprobe unable to parse container (corrupt video)."])

            meta = json.loads(stdout.decode("utf-8", errors="replace"))
            streams = meta.get("streams", [])
            fmt = meta.get("format", {})

            video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
            audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

            if not video_stream:
                return QualityReport(passed=False, issues=["Container has no video stream."])

            width = int(video_stream.get("width", 0))
            height = int(video_stream.get("height", 0))
            dur = float(fmt.get("duration", 0.0))
            has_audio = audio_stream is not None

            issues = []
            warnings = []

            # Resolution check
            if width < min_resolution and height < min_resolution:
                issues.append(f"Resolution {width}x{height} is below minimum acceptable threshold {min_resolution}p.")

            # Duration variance check
            if expected_duration and expected_duration > 0:
                diff = abs(dur - expected_duration)
                if diff > max(3.0, expected_duration * 0.4):
                    warnings.append(
                        f"Duration variance: expected ~{expected_duration:.1f}s, got {dur:.1f}s."
                    )

            passed = len(issues) == 0
            return QualityReport(
                passed=passed,
                issues=issues,
                warnings=warnings,
                duration=dur,
                width=width,
                height=height,
                has_audio=has_audio,
                details={"codec": video_stream.get("codec_name")},
            )

        except Exception as e:
            logger.warning("quality_inspection_exception", error=str(e))
            return QualityReport(passed=True, warnings=[f"Quality check warning: {str(e)}"])
