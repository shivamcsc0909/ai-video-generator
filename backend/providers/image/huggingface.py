"""Hugging Face image generation provider adapter."""

from __future__ import annotations

import tempfile
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


class HuggingFaceImageProvider(BaseProvider):
    """Hugging Face image generation (FLUX, SDXL, SD 1.5)."""

    name = "huggingface_image"
    display_name = "Hugging Face Image"
    capabilities = [ProviderCapability.IMAGE_GENERATION]
    is_local = False

    DEFAULT_MODEL = "black-forest-labs/FLUX.1-schnell"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def generate_image(self, request: GenerationRequest) -> GenerationResult:
        model = request.model or self.DEFAULT_MODEL
        url = f"https://api-inference.huggingface.co/models/{model}"

        payload = {
            "inputs": request.prompt,
            "parameters": {
                "width": request.width or 1024,
                "height": request.height or 768,
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
                        error_message=f"HF Image API {resp.status_code}: {resp.text[:250]}",
                    )

                temp_img = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
                temp_img.write(resp.content)
                temp_img.close()

                return GenerationResult(
                    success=True,
                    output_path=temp_img.name,
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
            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.get("https://huggingface.co/api/whoami-v2", headers=self.headers)
                return ProviderHealth(is_available=(res.status_code == 200), quota_status="healthy" if res.status_code == 200 else "unhealthy")
        except Exception as e:
            return ProviderHealth(is_available=False, error_message=str(e))
