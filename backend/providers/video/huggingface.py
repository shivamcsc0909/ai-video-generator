"""Hugging Face video generation provider adapter."""

from __future__ import annotations

import asyncio
from typing import Optional

import httpx
import structlog

from backend.providers.base.provider_interface import (
    BaseProvider,
    ErrorType,
    GenerationRequest,
    GenerationResult,
    ProviderCapability,
    ProviderHealth,
)

logger = structlog.get_logger(__name__)


class HuggingFaceVideoProvider(BaseProvider):
    """Hugging Face Serverless Inference / Endpoint video generation."""

    name = "huggingface_video"
    display_name = "Hugging Face Video"
    capabilities = [
        ProviderCapability.VIDEO_GENERATION,
        ProviderCapability.IMAGE_TO_VIDEO,
    ]
    is_local = False

    DEFAULT_MODEL = "ali-vilab/i2vgen-xl"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def generate_video(self, request: GenerationRequest) -> GenerationResult:
        model = request.model or self.DEFAULT_MODEL
        url = f"https://api-inference.huggingface.co/models/{model}"

        payload = {
            "inputs": request.prompt,
            "parameters": {
                "num_frames": int((request.duration_seconds or 4) * (request.fps or 16)),
            },
        }

        try:
            async with httpx.AsyncClient(timeout=90.0) as client:
                resp = await client.post(url, json=payload, headers=self.headers)
                if resp.status_code == 503:
                    # Model loading on HF
                    wait_sec = 20
                    try:
                        wait_sec = resp.json().get("estimated_time", 20)
                    except Exception:
                        pass
                    await asyncio.sleep(min(wait_sec, 30))
                    resp = await client.post(url, json=payload, headers=self.headers)

                if resp.status_code != 200:
                    error_type = self.classify_error(Exception(resp.text), resp.status_code)
                    return GenerationResult(
                        success=False,
                        error_type=error_type,
                        error_message=f"Hugging Face error {resp.status_code}: {resp.text[:300]}",
                    )

                # Binary video stream or JSON
                if "video" in resp.headers.get("content-type", "") or "application/octet-stream" in resp.headers.get("content-type", ""):
                    import tempfile
                    temp_vid = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
                    temp_vid.write(resp.content)
                    temp_vid.close()
                    return GenerationResult(
                        success=True,
                        output_path=temp_vid.name,
                        model_used=model,
                    )

                return GenerationResult(
                    success=True,
                    metadata={"response": resp.json() if "application/json" in resp.headers.get("content-type", "") else None},
                    model_used=model,
                )

        except Exception as e:
            return GenerationResult(
                success=False,
                error_type=self.classify_error(e),
                error_message=str(e),
            )

    async def health_check(self) -> ProviderHealth:
        if not self.api_key:
            return ProviderHealth(is_available=False, error_message="Hugging Face token missing")
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get("https://huggingface.co/api/whoami-v2", headers=self.headers)
                if res.status_code == 200:
                    return ProviderHealth(is_available=True, quota_status="healthy")
                return ProviderHealth(is_available=False, error_message="Invalid Hugging Face token")
        except Exception as e:
            return ProviderHealth(is_available=False, error_message=str(e))
