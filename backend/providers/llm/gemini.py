"""
Google Gemini LLM provider.

Uses the google-generativeai SDK.  API key is accepted at construction
time and NEVER logged anywhere in this module.
"""

import time
from typing import Optional

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

# Default models in order of preference
_DEFAULT_MODEL = "gemini-1.5-pro"
_FALLBACK_MODEL = "gemini-1.5-flash"

# Health-check model – cheapest possible call
_HEALTH_MODEL = "gemini-1.5-flash"


class GeminiProvider(BaseProvider):
    """Google Gemini provider for text generation."""

    name = "google_gemini"
    display_name = "Google Gemini"
    capabilities = [ProviderCapability.TEXT_GENERATION]
    is_local = False

    def __init__(self, api_key: str) -> None:
        # Store key privately; never surfaced in logs or repr
        self.__api_key = api_key
        self._client = None  # lazily initialised

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_client(self):
        """Lazily create the generativeai client."""
        if self._client is None:
            try:
                import google.generativeai as genai  # type: ignore

                genai.configure(api_key=self.__api_key)
                self._client = genai
            except ImportError as exc:
                raise RuntimeError(
                    "google-generativeai is not installed. Run: pip install google-generativeai"
                ) from exc
        return self._client

    def _classify_google_error(self, exc: Exception) -> ErrorType:
        """Translate google-api-core exceptions to ErrorType."""
        try:
            from google.api_core import exceptions as google_exc  # type: ignore

            if isinstance(exc, google_exc.Unauthenticated):
                return ErrorType.AUTH_ERROR
            if isinstance(exc, google_exc.PermissionDenied):
                return ErrorType.AUTH_ERROR
            if isinstance(exc, google_exc.ResourceExhausted):
                return ErrorType.RATE_LIMIT
            if isinstance(exc, google_exc.InvalidArgument):
                return ErrorType.INVALID_REQUEST
            if isinstance(exc, google_exc.NotFound):
                return ErrorType.MODEL_UNAVAILABLE
            if isinstance(exc, google_exc.ServiceUnavailable):
                return ErrorType.SERVER_ERROR
            if isinstance(exc, google_exc.DeadlineExceeded):
                return ErrorType.TIMEOUT
        except ImportError:
            pass

        # Fall through to generic heuristic
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
        """Generate text using Gemini.  Returns text in result.metadata['text']."""
        start_ms = int(time.monotonic() * 1000)
        model_id = model or _DEFAULT_MODEL

        try:
            genai = self._get_client()

            generation_config = {
                "temperature": temperature,
                "max_output_tokens": max_tokens,
            }

            model_obj = genai.GenerativeModel(
                model_name=model_id,
                system_instruction=system_prompt,
                generation_config=generation_config,
            )

            response = model_obj.generate_content(prompt)

            # Extract text safely
            text = ""
            if response.parts:
                text = "".join(part.text for part in response.parts if hasattr(part, "text"))
            elif hasattr(response, "text"):
                text = response.text

            elapsed = int(time.monotonic() * 1000) - start_ms
            logger.info("gemini_generate_text_success", model=model_id, duration_ms=elapsed)

            return GenerationResult(
                success=True,
                model_used=model_id,
                duration_ms=elapsed,
                metadata={"text": text},
            )

        except Exception as exc:
            elapsed = int(time.monotonic() * 1000) - start_ms
            error_type = self._classify_google_error(exc)
            # Log error class only, NOT the prompt (which may contain sensitive data)
            logger.warning(
                "gemini_generate_text_error",
                error_type=error_type.value,
                error_class=type(exc).__name__,
                model=model_id,
                duration_ms=elapsed,
            )

            # Retry with flash model if pro is unavailable
            if error_type == ErrorType.MODEL_UNAVAILABLE and model_id == _DEFAULT_MODEL:
                logger.info("gemini_fallback_to_flash", original_model=model_id)
                return await self.generate_text(
                    prompt,
                    system_prompt=system_prompt,
                    model=_FALLBACK_MODEL,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs,
                )

            return GenerationResult(
                success=False,
                error_type=error_type,
                error_message=str(exc),
                model_used=model_id,
                duration_ms=elapsed,
            )

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    async def health_check(self) -> ProviderHealth:
        """Verify the API key works by listing models (cheap call)."""
        start_ms = int(time.monotonic() * 1000)
        try:
            genai = self._get_client()
            # list_models() is a lightweight endpoint, no quota cost
            models = list(genai.list_models())
            latency = int(time.monotonic() * 1000) - start_ms
            has_expected = any(_HEALTH_MODEL in m.name for m in models)
            return ProviderHealth(
                is_available=True,
                latency_ms=latency,
                quota_status="healthy" if has_expected else "warning",
            )
        except Exception as exc:
            latency = int(time.monotonic() * 1000) - start_ms
            error_type = self._classify_google_error(exc)
            return ProviderHealth(
                is_available=False,
                latency_ms=latency,
                quota_status="exceeded" if error_type == ErrorType.RATE_LIMIT else "unknown",
                error_message=str(exc),
            )
