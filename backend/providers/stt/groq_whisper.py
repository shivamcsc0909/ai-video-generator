"""Groq Whisper high-speed speech-to-text provider adapter."""

from __future__ import annotations

import os
from typing import Optional

import httpx
import structlog

from backend.providers.base.provider_interface import (
    BaseProvider,
    ErrorType,
    GenerationResult,
    ProviderCapability,
    ProviderHealth,
)

logger = structlog.get_logger(__name__)


class GroqWhisperProvider(BaseProvider):
    """Groq Whisper STT adapter (whisper-large-v3)."""

    name = "groq_whisper"
    display_name = "Groq Whisper STT"
    capabilities = [ProviderCapability.SPEECH_TO_TEXT]
    is_local = False

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {"Authorization": f"Bearer {self.api_key}"}

    async def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None,
    ) -> GenerationResult:
        if not os.path.exists(audio_path):
            return GenerationResult(
                success=False,
                error_type=ErrorType.INVALID_REQUEST,
                error_message=f"Audio file not found: {audio_path}",
            )

        url = "https://api.groq.com/openai/v1/audio/transcriptions"

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                with open(audio_path, "rb") as f:
                    files = {"file": (os.path.basename(audio_path), f, "audio/mpeg")}
                    data = {
                        "model": "whisper-large-v3",
                        "response_format": "verbose_json",
                    }
                    if language:
                        data["language"] = language

                    resp = await client.post(
                        url,
                        files=files,
                        data=data,
                        headers=self.headers,
                    )

                if resp.status_code != 200:
                    error_type = self.classify_error(Exception(resp.text), resp.status_code)
                    return GenerationResult(
                        success=False,
                        error_type=error_type,
                        error_message=f"Groq Whisper error {resp.status_code}: {resp.text[:300]}",
                    )

                result_json = resp.json()
                segments = []
                for s in result_json.get("segments", []):
                    segments.append({
                        "start": float(s.get("start", 0)),
                        "end": float(s.get("end", 0)),
                        "text": s.get("text", "").strip(),
                    })

                return GenerationResult(
                    success=True,
                    metadata={
                        "text": result_json.get("text", ""),
                        "language": result_json.get("language", language or "en"),
                        "segments": segments,
                    },
                    model_used="whisper-large-v3",
                )

        except Exception as e:
            return GenerationResult(
                success=False,
                error_type=self.classify_error(e),
                error_message=str(e),
            )

    async def health_check(self) -> ProviderHealth:
        if not self.api_key:
            return ProviderHealth(is_available=False, error_message="Groq API key missing")
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.get(
                    "https://api.groq.com/openai/v1/models",
                    headers=self.headers,
                )
                return ProviderHealth(is_available=(res.status_code == 200), quota_status="healthy" if res.status_code == 200 else "unhealthy")
        except Exception as e:
            return ProviderHealth(is_available=False, error_message=str(e))
