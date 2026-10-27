"""
Ollama-based local LLM provider.

Talks to the Ollama REST API at http://localhost:11434 (configurable).
No API key required – runs entirely on local hardware.
"""

import time
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

_DEFAULT_BASE_URL = "http://localhost:11434"
_DEFAULT_MODEL = "llama3.1"
_REQUEST_TIMEOUT = 120.0  # LLM inference can be slow on CPU


class LocalLLMProvider(BaseProvider):
    """Local Ollama LLM provider – zero cost, runs on device."""

    name = "local_llm"
    display_name = "Local LLM (Ollama)"
    capabilities = [ProviderCapability.TEXT_GENERATION]
    is_local = True

    def __init__(
        self,
        base_url: str = _DEFAULT_BASE_URL,
        model: str = _DEFAULT_MODEL,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.default_model = model

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
        """Chat completion via Ollama /api/chat endpoint."""
        start_ms = int(time.monotonic() * 1000)
        model_id = model or self.default_model

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model_id,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT) as client:
                response = await client.post(
                    f"{self.base_url}/api/chat", json=payload
                )
                response.raise_for_status()
                data = response.json()

            text = data.get("message", {}).get("content", "")
            elapsed = int(time.monotonic() * 1000) - start_ms

            logger.info("local_llm_success", model=model_id, duration_ms=elapsed)

            return GenerationResult(
                success=True,
                model_used=model_id,
                duration_ms=elapsed,
                metadata={
                    "text": text,
                    "eval_count": data.get("eval_count"),
                    "prompt_eval_count": data.get("prompt_eval_count"),
                },
            )

        except httpx.TimeoutException as exc:
            elapsed = int(time.monotonic() * 1000) - start_ms
            logger.warning("local_llm_timeout", model=model_id, duration_ms=elapsed)
            return GenerationResult(
                success=False,
                error_type=ErrorType.TIMEOUT,
                error_message=f"Ollama request timed out after {_REQUEST_TIMEOUT}s. "
                "The model may be loading or the prompt is too long.",
                model_used=model_id,
                duration_ms=elapsed,
            )

        except httpx.ConnectError as exc:
            elapsed = int(time.monotonic() * 1000) - start_ms
            logger.warning("local_llm_connect_error", base_url=self.base_url)
            return GenerationResult(
                success=False,
                error_type=ErrorType.SERVER_ERROR,
                error_message=f"Cannot connect to Ollama at {self.base_url}. "
                "Make sure Ollama is running: `ollama serve`",
                model_used=model_id,
                duration_ms=elapsed,
            )

        except httpx.HTTPStatusError as exc:
            elapsed = int(time.monotonic() * 1000) - start_ms
            if exc.response.status_code == 404:
                error_type = ErrorType.MODEL_UNAVAILABLE
                msg = (
                    f"Model '{model_id}' not found in Ollama. "
                    f"Pull it with: `ollama pull {model_id}`"
                )
            else:
                error_type = self.classify_error(exc, http_status=exc.response.status_code)
                msg = str(exc)
            logger.warning("local_llm_http_error", status=exc.response.status_code, model=model_id)
            return GenerationResult(
                success=False,
                error_type=error_type,
                error_message=msg,
                model_used=model_id,
                duration_ms=elapsed,
            )

        except Exception as exc:
            elapsed = int(time.monotonic() * 1000) - start_ms
            logger.warning("local_llm_error", error_class=type(exc).__name__, duration_ms=elapsed)
            return GenerationResult(
                success=False,
                error_type=ErrorType.TRANSIENT,
                error_message=str(exc),
                model_used=model_id,
                duration_ms=elapsed,
            )

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    async def health_check(self) -> ProviderHealth:
        """Check Ollama is running and return list of local models."""
        start_ms = int(time.monotonic() * 1000)
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                data = response.json()

            latency = int(time.monotonic() * 1000) - start_ms
            models = [m.get("name", "") for m in data.get("models", [])]
            has_model = any(self.default_model.split(":")[0] in m for m in models)

            return ProviderHealth(
                is_available=True,
                latency_ms=latency,
                quota_status="healthy",
                error_message=None if has_model else (
                    f"Default model '{self.default_model}' not pulled yet. "
                    f"Available: {', '.join(models) or 'none'}"
                ),
            )

        except httpx.ConnectError:
            latency = int(time.monotonic() * 1000) - start_ms
            return ProviderHealth(
                is_available=False,
                latency_ms=latency,
                quota_status="unknown",
                error_message=f"Ollama not reachable at {self.base_url}. Start with: `ollama serve`",
            )

        except Exception as exc:
            latency = int(time.monotonic() * 1000) - start_ms
            return ProviderHealth(
                is_available=False,
                latency_ms=latency,
                quota_status="unknown",
                error_message=str(exc),
            )
