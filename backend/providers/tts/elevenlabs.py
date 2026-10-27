"""ElevenLabs text-to-speech provider adapter."""

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


class ElevenLabsProvider(BaseProvider):
    """ElevenLabs voice synthesis provider adapter."""

    name = "elevenlabs"
    display_name = "ElevenLabs"
    capabilities = [ProviderCapability.TEXT_TO_SPEECH]
    is_local = False

    DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"  # Rachel

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        }

    async def generate_audio(
        self,
        text: str,
        voice_settings: dict,
        output_path: str,
    ) -> GenerationResult:
        voice_id = voice_settings.get("voice_id") or self.DEFAULT_VOICE_ID
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

        payload = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
                "speed": float(voice_settings.get("speed", 1.0)),
            },
        }

        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                resp = await client.post(url, json=payload, headers=self.headers)
                if resp.status_code != 200:
                    error_type = self.classify_error(Exception(resp.text), resp.status_code)
                    return GenerationResult(
                        success=False,
                        error_type=error_type,
                        error_message=f"ElevenLabs error {resp.status_code}: {resp.text[:300]}",
                    )

                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path, "wb") as f:
                    f.write(resp.content)

                # Estimate cost: ~$0.30 per 1000 characters
                cost = (len(text) / 1000.0) * 0.30

                return GenerationResult(
                    success=True,
                    output_path=output_path,
                    estimated_cost=cost,
                    model_used="eleven_multilingual_v2",
                )
        except Exception as e:
            return GenerationResult(
                success=False,
                error_type=self.classify_error(e),
                error_message=str(e),
            )

    async def health_check(self) -> ProviderHealth:
        if not self.api_key:
            return ProviderHealth(is_available=False, error_message="ElevenLabs API key missing")
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.get(
                    "https://api.elevenlabs.io/v1/user",
                    headers={"xi-api-key": self.api_key},
                )
                if res.status_code == 200:
                    user_data = res.json()
                    tier = user_data.get("subscription", {}).get("tier", "unknown")
                    return ProviderHealth(is_available=True, quota_status=tier)
                elif res.status_code in (401, 403):
                    return ProviderHealth(is_available=False, error_message="Invalid ElevenLabs API key")
                return ProviderHealth(is_available=False, error_message=f"Status {res.status_code}")
        except Exception as e:
            return ProviderHealth(is_available=False, error_message=str(e))
