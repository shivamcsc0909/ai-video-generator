"""Replicate video generation provider adapter."""

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


class ReplicateVideoProvider(BaseProvider):
    """Replicate video generation provider adapter (Wan 2.1, LTX-Video, SVD)."""

    name = "replicate_video"
    display_name = "Replicate Video"
    capabilities = [
        ProviderCapability.VIDEO_GENERATION,
        ProviderCapability.IMAGE_TO_VIDEO,
    ]
    is_local = False

    DEFAULT_MODEL = "wan-video/wan-2.1-1.3b"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Prefer": "wait=5",
        }

    async def generate_video(self, request: GenerationRequest) -> GenerationResult:
        model = request.model or self.DEFAULT_MODEL
        url = "https://api.replicate.com/v1/predictions"

        input_data: dict = {
            "prompt": request.prompt,
        }
        if request.negative_prompt:
            input_data["negative_prompt"] = request.negative_prompt
        if request.reference_images and len(request.reference_images) > 0:
            input_data["image"] = request.reference_images[0]
        if request.aspect_ratio:
            input_data["aspect_ratio"] = request.aspect_ratio

        payload = {
            "version": model if "/" not in model or ":" in model else None,
            "model": model if ":" not in model else None,
            "input": input_data,
        }
        # Clean payload
        payload = {k: v for k, v in payload.items() if v is not None}

        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                resp = await client.post(url, json=payload, headers=self.headers)
                if resp.status_code not in (200, 201):
                    error_type = self.classify_error(Exception(resp.text), resp.status_code)
                    return GenerationResult(
                        success=False,
                        error_type=error_type,
                        error_message=f"Replicate API {resp.status_code}: {resp.text[:300]}",
                    )

                pred = resp.json()
                pred_id = pred.get("id")
                status = pred.get("status")

                if status == "succeeded":
                    output = pred.get("output")
                    out_url = output if isinstance(output, str) else (output[0] if output else None)
                    return GenerationResult(
                        success=True,
                        output_url=out_url,
                        provider_job_id=pred_id,
                        model_used=model,
                    )

                # Poll prediction
                poll_url = f"https://api.replicate.com/v1/predictions/{pred_id}"
                for _ in range(60):  # max 5 mins
                    await asyncio.sleep(5)
                    poll_res = await client.get(poll_url, headers=self.headers)
                    if poll_res.status_code != 200:
                        continue
                    p_data = poll_res.json()
                    p_status = p_data.get("status")
                    if p_status == "succeeded":
                        output = p_data.get("output")
                        out_url = output if isinstance(output, str) else (output[0] if output else None)
                        return GenerationResult(
                            success=True,
                            output_url=out_url,
                            provider_job_id=pred_id,
                            model_used=model,
                        )
                    elif p_status in ("failed", "canceled"):
                        return GenerationResult(
                            success=False,
                            error_type=ErrorType.SERVER_ERROR,
                            error_message=f"Replicate job {p_status}: {p_data.get('error')}",
                            provider_job_id=pred_id,
                        )

                return GenerationResult(
                    success=False,
                    error_type=ErrorType.TIMEOUT,
                    error_message="Replicate generation timed out.",
                    provider_job_id=pred_id,
                )

        except Exception as e:
            return GenerationResult(
                success=False,
                error_type=self.classify_error(e),
                error_message=str(e),
            )

    async def health_check(self) -> ProviderHealth:
        if not self.api_key or len(self.api_key) < 8:
            return ProviderHealth(is_available=False, error_message="Replicate token missing")
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get("https://api.replicate.com/v1/models/wan-video/wan-2.1-1.3b", headers=self.headers)
                if res.status_code == 200:
                    return ProviderHealth(is_available=True, quota_status="healthy")
                elif res.status_code in (401, 403):
                    return ProviderHealth(is_available=False, error_message="Invalid Replicate token")
                return ProviderHealth(is_available=True, quota_status="unknown")
        except Exception as e:
            return ProviderHealth(is_available=False, error_message=str(e))
