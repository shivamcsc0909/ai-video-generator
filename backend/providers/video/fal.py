"""Fal.ai video generation provider adapter."""

from __future__ import annotations

import asyncio
import os
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


class FalVideoProvider(BaseProvider):
    """Fal.ai video provider adapter (Kling, LTX-Video, Fast-SVD, Wan 2.1)."""

    name = "fal_video"
    display_name = "Fal.ai Video"
    capabilities = [
        ProviderCapability.VIDEO_GENERATION,
        ProviderCapability.IMAGE_TO_VIDEO,
    ]
    is_local = False

    DEFAULT_MODEL = "fal-ai/kling-video/v1/standard/text-to-video"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Key {self.api_key}",
            "Content-Type": "application/json",
        }

    async def generate_video(self, request: GenerationRequest) -> GenerationResult:
        model = request.model or self.DEFAULT_MODEL
        url = f"https://queue.fal.run/{model}"

        payload: dict = {
            "prompt": request.prompt,
            "duration": str(int(request.duration_seconds or 5)),
            "aspect_ratio": request.aspect_ratio or "16:9",
        }
        if request.negative_prompt:
            payload["negative_prompt"] = request.negative_prompt
        if request.reference_images and len(request.reference_images) > 0:
            payload["image_url"] = request.reference_images[0]

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(url, json=payload, headers=self.headers)

                if resp.status_code != 200 and resp.status_code != 201:
                    error_type = self.classify_error(Exception(resp.text), resp.status_code)
                    return GenerationResult(
                        success=False,
                        error_type=error_type,
                        error_message=f"Fal.ai error {resp.status_code}: {resp.text[:300]}",
                    )

                submit_data = resp.json()
                request_id = submit_data.get("request_id")
                if not request_id:
                    # Synchronous direct response
                    video_url = (
                        submit_data.get("video", {}).get("url")
                        or submit_data.get("output", {}).get("url")
                    )
                    return GenerationResult(
                        success=True,
                        output_url=video_url,
                        provider_job_id="sync",
                        model_used=model,
                    )

                # Poll status
                status_url = f"https://queue.fal.run/{model}/requests/{request_id}/status"
                result_url = f"https://queue.fal.run/{model}/requests/{request_id}"

                for _ in range(60):  # max 5 minutes
                    await asyncio.sleep(5)
                    poll_resp = await client.get(status_url, headers=self.headers)
                    if poll_resp.status_code != 200:
                        continue
                    status_data = poll_resp.json()
                    status = status_data.get("status")
                    if status == "COMPLETED":
                        final_resp = await client.get(result_url, headers=self.headers)
                        res_data = final_resp.json()
                        video_url = (
                            res_data.get("video", {}).get("url")
                            or res_data.get("output", {}).get("url")
                        )
                        return GenerationResult(
                            success=True,
                            output_url=video_url,
                            provider_job_id=request_id,
                            model_used=model,
                        )
                    elif status in ("FAILED", "CANCELLED"):
                        return GenerationResult(
                            success=False,
                            error_type=ErrorType.SERVER_ERROR,
                            error_message=f"Fal job {status}: {status_data.get('error', 'unknown error')}",
                            provider_job_id=request_id,
                        )

                return GenerationResult(
                    success=False,
                    error_type=ErrorType.TIMEOUT,
                    error_message="Fal.ai generation timed out after 5 minutes.",
                    provider_job_id=request_id,
                )

        except Exception as e:
            return GenerationResult(
                success=False,
                error_type=self.classify_error(e),
                error_message=str(e),
            )

    async def health_check(self) -> ProviderHealth:
        if not self.api_key or len(self.api_key) < 8:
            return ProviderHealth(is_available=False, error_message="API key missing or empty")
        try:
            # Check models or simple ping
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get("https://queue.fal.run/fal-ai/fast-svd", headers=self.headers)
                # 405 Method Not Allowed or 200 means endpoint reached and authorized
                if res.status_code in (200, 405, 404):
                    return ProviderHealth(is_available=True, quota_status="healthy")
                elif res.status_code in (401, 403):
                    return ProviderHealth(is_available=False, error_message="Invalid Fal.ai API key")
                return ProviderHealth(is_available=True, quota_status="unknown")
        except Exception as e:
            return ProviderHealth(is_available=False, error_message=str(e))
