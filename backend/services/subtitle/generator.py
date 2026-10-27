"""Subtitle generator for SRT and WebVTT formats from STT segments."""

from __future__ import annotations

import os
from typing import List, Optional


class SubtitleGenerator:
    """Generates valid SRT and WebVTT subtitle files from timed transcript segments."""

    def generate_srt(self, segments: List[dict], output_path: str) -> str:
        """Writes standard SubRip (.srt) subtitle file."""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        lines = []
        for i, seg in enumerate(segments, start=1):
            start = float(seg.get("start", 0.0))
            end = float(seg.get("end", start + 2.5))
            text = str(seg.get("text", "")).strip()
            if not text:
                continue

            lines.append(str(i))
            lines.append(f"{self._format_timestamp(start, ',')} --> {self._format_timestamp(end, ',')}")
            lines.append(text)
            lines.append("")

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        return output_path

    def generate_vtt(self, segments: List[dict], output_path: str) -> str:
        """Writes WebVTT (.vtt) file for browser HTML5 <video> tracks."""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        lines = ["WEBVTT", ""]
        for seg in segments:
            start = float(seg.get("start", 0.0))
            end = float(seg.get("end", start + 2.5))
            text = str(seg.get("text", "")).strip()
            if not text:
                continue

            lines.append(f"{self._format_timestamp(start, '.')} --> {self._format_timestamp(end, '.')}")
            lines.append(text)
            lines.append("")

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        return output_path

    @staticmethod
    def _format_timestamp(seconds: float, millisecond_sep: str = ",") -> str:
        sec = max(0.0, float(seconds))
        hours = int(sec // 3600)
        minutes = int((sec % 3600) // 60)
        secs = int(sec % 60)
        millis = int((sec - int(sec)) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}{millisecond_sep}{millis:03d}"
