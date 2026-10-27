"""
Groq LLM + Whisper provider.

Uses the official groq Python SDK for:
  - Chat completions  (TEXT_GENERATION)
  - Audio transcriptions  (SPEECH_TO_TEXT)

API key stored privately and never logged.
"""

import time
from typing import Optional
from pathlib import Path

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

_CHAT_MODELS = [
    "llama-3.1-70b-versatile",
    "mixtral-8x7b-32768",
    "llama-3.1-8b-instant",
]

_WHISPER_MODEL = "whisper-large-v3"


class GroqProvider(BaseProvider):
    """Groq cloud provider – ultra-fast inference via Groq LPU."""

    name = "groq"
    display_name = "Groq"
    capabilities = [
        ProviderCapability.TEXT_GENERATION,
        ProviderCapability.SPEECH_TO_TEXT,
    ]
    is_local = False

    def __init__(self, api_key: str) -> None:
        self.__api_key = api_key
        self._client = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_client(self):
        if self._client is None:
            try:
                from groq import Groq  # type: ignore

                self._client = Groq(api_key=self.__api_key)
            except ImportError as exc:
                raise RuntimeError(
                    "groq SDK not installed. Run: pip install groq"
                ) from exc
        return self._client

    def _classify_groq_error(self, exc: Exception) -> ErrorType:
        """Map groq-specific errors to ErrorType."""
        try:
            from groq import (  # type: ignore
                AuthenticationError,
                RateLimitError,
                BadRequestError,
                NotFoundError,
                APIStatusError,
            )

            if isinstance(exc, AuthenticationError):
                return ErrorType.AUTH_ERROR
            if isinstance(exc, RateLimitError):
                return ErrorType.RATE_LIMIT
            if isinstance(exc, BadRequestError):
                return ErrorType.INVALID_REQUEST
            if isinstance(exc, NotFoundError):
                return ErrorType.MODEL_UNAVAILABLE
            if isinstance(exc, APIStatusError):
                return self.classify_error(exc, http_status=exc.status_code)
        except ImportError:
            pass

        return self.classify_error(exc)

    # ------------------------------------------------------------------
    # Text generation
    # ------------------------------------------------------------------

    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs,
    ) -> GenerationResult:
        """Chat completion via Groq.  Text returned in metadata['text']."""
        start_ms = int(time.monotonic() * 1000)
        model_id = model or _CHAT_MODELS[0]

        try:
            client = self._get_client()

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = client.chat.completions.create(
                model=model_id,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            text = response.choices[0].message.content or ""
            elapsed = int(time.monotonic() * 1000) - start_ms

            logger.info("groq_generate_text_success", model=model_id, duration_ms=elapsed)

            return GenerationResult(
                success=True,
                model_used=model_id,
                duration_ms=elapsed,
                metadata={
                    "text": text,
                    "usage": {
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                    } if response.usage else {},
                },
            )

        except Exception as exc:
            elapsed = int(time.monotonic() * 1000) - start_ms
            error_type = self._classify_groq_error(exc)
            logger.warning(
                "groq_generate_text_error",
                error_type=error_type.value,
                error_class=type(exc).__name__,
                model=model_id,
                duration_ms=elapsed,
            )

            # Try next available model on MODEL_UNAVAILABLE
            if error_type == ErrorType.MODEL_UNAVAILABLE:
                current_idx = _CHAT_MODELS.index(model_id) if model_id in _CHAT_MODELS else -1
                next_idx = current_idx + 1
                if next_idx < len(_CHAT_MODELS):
                    logger.info(
                        "groq_model_fallback",
                        from_model=model_id,
                        to_model=_CHAT_MODELS[next_idx],
                    )
                    return await self.generate_text(
                        prompt,
                        system_prompt=system_prompt,
                        model=_CHAT_MODELS[next_idx],
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )

            return GenerationResult(
                success=False,
                error_type=error_type,
                error_message=str(exc),
                model_used=model_id,
                duration_ms=elapsed,
            )

    # ------------------------------------------------------------------
    # Speech-to-text (Whisper via Groq)
    # ------------------------------------------------------------------

    async def transcribe(
        self, audio_path: str, language: Optional[str] = None
    ) -> GenerationResult:
        """Transcribe audio using Groq's whisper-large-v3 endpoint."""
        start_ms = int(time.monotonic() * 1000)
        path = Path(audio_path)

        if not path.exists():
            return GenerationResult(
                success=False,
                error_type=ErrorType.INVALID_REQUEST,
                error_message=f"Audio file not found: {audio_path}",
            )

        try:
            client = self._get_client()

            with open(path, "rb") as audio_file:
                kwargs: dict = {
                    "file": (path.name, audio_file),
                    "model": _WHISPER_MODEL,
                    "response_format": "verbose_json",
                }
                if language:
                    kwargs["language"] = language

                transcription = client.audio.transcriptions.create(**kwargs)

            elapsed = int(time.monotonic() * 1000) - start_ms
            text = transcription.text or ""
            segments = []

            if hasattr(transcription, "segments") and transcription.segments:
                segments = [
                    {"start": s.get("start", 0), "end": s.get("end", 0), "text": s.get("text", "")}
                    for s in transcription.segments
                ]

            logger.info(
                "groq_transcribe_success",
                audio_file=path.name,
                duration_ms=elapsed,
                chars=len(text),
            )

            return GenerationResult(
                success=True,
                model_used=_WHISPER_MODEL,
                duration_ms=elapsed,
                metadata={
                    "text": text,
                    "segments": segments,
                    "language": getattr(transcription, "language", language or "unknown"),
                },
            )

        except Exception as exc:
            elapsed = int(time.monotonic() * 1000) - start_ms
            error_type = self._classify_groq_error(exc)
            logger.warning(
                "groq_transcribe_error",
                error_type=error_type.value,
                error_class=type(exc).__name__,
                duration_ms=elapsed,
            )
            return GenerationResult(
                success=False,
                error_type=error_type,
                error_message=str(exc),
                model_used=_WHISPER_MODEL,
                duration_ms=elapsed,
            )

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    async def health_check(self) -> ProviderHealth:
        """Verify connectivity by listing available models."""
        start_ms = int(time.monotonic() * 1000)
        try:
            client = self._get_client()
            models = client.models.list()
            latency = int(time.monotonic() * 1000) - start_ms
            model_names = [m.id for m in models.data] if hasattr(models, "data") else []
            has_llama = any("llama" in n for n in model_names)
            return ProviderHealth(
                is_available=True,
                latency_ms=latency,
                quota_status="healthy" if has_llama else "warning",
            )
        except Exception as exc:
            latency = int(time.monotonic() * 1000) - start_ms
            error_type = self._classify_groq_error(exc)
            return ProviderHealth(
                is_available=False,
                latency_ms=latency,
                quota_status="exceeded" if error_type == ErrorType.RATE_LIMIT else "unknown",
                error_message=str(exc),
            )
