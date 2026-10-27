"""
Abstract base class and shared types for all AI providers.

All providers inherit from BaseProvider and implement the relevant
capability methods. Error classification drives retry/rotation policy.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional, AsyncGenerator
from dataclasses import dataclass, field


class ProviderCapability(str, Enum):
    TEXT_GENERATION = "text_generation"
    IMAGE_GENERATION = "image_generation"
    VIDEO_GENERATION = "video_generation"
    IMAGE_TO_VIDEO = "image_to_video"
    TEXT_TO_SPEECH = "text_to_speech"
    SPEECH_TO_TEXT = "speech_to_text"
    LIP_SYNC = "lip_sync"


class ErrorType(str, Enum):
    TRANSIENT = "transient"            # retry immediately
    RATE_LIMIT = "rate_limit"          # wait / switch account
    QUOTA_EXCEEDED = "quota_exceeded"  # switch account
    AUTH_ERROR = "auth_error"          # disable account, notify user
    INVALID_REQUEST = "invalid_request"  # do NOT retry
    MODEL_UNAVAILABLE = "model_unavailable"  # switch model/provider
    SERVER_ERROR = "server_error"      # retry with backoff
    TIMEOUT = "timeout"                # retry per policy
    UNKNOWN = "unknown"


@dataclass
class GenerationRequest:
    prompt: str
    negative_prompt: Optional[str] = None
    reference_images: list = field(default_factory=list)  # file paths or URLs
    model: Optional[str] = None
    seed: Optional[int] = None
    steps: Optional[int] = None
    cfg_scale: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    duration_seconds: Optional[float] = None
    fps: Optional[int] = None
    aspect_ratio: Optional[str] = "16:9"
    extra_params: dict = field(default_factory=dict)


@dataclass
class GenerationResult:
    success: bool
    output_path: Optional[str] = None
    output_url: Optional[str] = None
    error_type: Optional[ErrorType] = None
    error_message: Optional[str] = None
    provider_job_id: Optional[str] = None
    model_used: Optional[str] = None
    duration_ms: Optional[int] = None
    estimated_cost: Optional[float] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class ProviderHealth:
    is_available: bool
    latency_ms: Optional[int] = None
    quota_status: str = "unknown"  # healthy / warning / exceeded / unknown
    error_message: Optional[str] = None


class BaseProvider(ABC):
    """Abstract base for all AI provider integrations."""

    name: str = "base"
    display_name: str = "Base Provider"
    capabilities: list = []
    is_local: bool = False

    # ------------------------------------------------------------------
    # Capability methods – subclasses implement what they support
    # ------------------------------------------------------------------

    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs,
    ) -> GenerationResult:
        raise NotImplementedError(f"{self.name} does not support text generation")

    async def generate_image(self, request: GenerationRequest) -> GenerationResult:
        raise NotImplementedError(f"{self.name} does not support image generation")

    async def generate_video(self, request: GenerationRequest) -> GenerationResult:
        raise NotImplementedError(f"{self.name} does not support video generation")

    async def generate_audio(
        self, text: str, voice_settings: dict, output_path: str
    ) -> GenerationResult:
        raise NotImplementedError(f"{self.name} does not support TTS")

    async def transcribe(
        self, audio_path: str, language: Optional[str] = None
    ) -> GenerationResult:
        raise NotImplementedError(f"{self.name} does not support STT")

    async def check_job_status(self, job_id: str) -> dict:
        raise NotImplementedError(f"{self.name} does not support job status polling")

    async def estimate_cost(self, request: GenerationRequest) -> Optional[float]:
        """Override if the provider exposes pricing. Returns USD float."""
        return None

    # ------------------------------------------------------------------
    # Health check – every provider must implement this
    # ------------------------------------------------------------------

    @abstractmethod
    async def health_check(self) -> ProviderHealth:
        """Return current health/availability of this provider account."""

    # ------------------------------------------------------------------
    # Error classification – shared logic, providers may override
    # ------------------------------------------------------------------

    def classify_error(
        self, error: Exception, http_status: Optional[int] = None
    ) -> ErrorType:
        """Map an exception (and optional HTTP status code) to an ErrorType.

        This drives retry, rotation, and cooldown policy in the router.
        """
        if http_status is not None:
            if http_status in (401, 403):
                return ErrorType.AUTH_ERROR
            if http_status == 429:
                return ErrorType.RATE_LIMIT
            if http_status == 400:
                return ErrorType.INVALID_REQUEST
            if http_status in (502, 503):
                return ErrorType.SERVER_ERROR
            if http_status >= 500:
                return ErrorType.SERVER_ERROR
            if http_status == 408 or http_status == 504:
                return ErrorType.TIMEOUT

        error_str = str(error).lower()

        if "quota" in error_str or "limit exceeded" in error_str:
            return ErrorType.QUOTA_EXCEEDED
        if "rate" in error_str and "limit" in error_str:
            return ErrorType.RATE_LIMIT
        if "timeout" in error_str or "timed out" in error_str:
            return ErrorType.TIMEOUT
        if "unauthorized" in error_str or "invalid key" in error_str or "invalid api key" in error_str:
            return ErrorType.AUTH_ERROR
        if "unavailable" in error_str or "503" in error_str:
            return ErrorType.SERVER_ERROR
        if "not found" in error_str or "model" in error_str and "unavailable" in error_str:
            return ErrorType.MODEL_UNAVAILABLE

        return ErrorType.TRANSIENT
