"""
Structured logging configuration using structlog.

In production (APP_ENV != 'development') logs are emitted as JSON.
In development a coloured console renderer is used instead.

Sensitive field names are scrubbed before any log record is emitted.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Any, MutableMapping

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from backend.core.config import get_settings

settings = get_settings()

# ------------------------------------------------------------------ #
# Sensitive field scrubbing
# ------------------------------------------------------------------ #
_SENSITIVE_KEYS = frozenset(
    {
        "api_key",
        "password",
        "token",
        "secret",
        "credential",
        "credentials",
        "encryption_key",
        "hashed_password",
        "access_token",
        "refresh_token",
        "authorization",
        "x-api-key",
    }
)


def _scrub_sensitive(
    logger: Any,  # noqa: ARG001
    method: str,  # noqa: ARG001
    event_dict: MutableMapping[str, Any],
) -> MutableMapping[str, Any]:
    """structlog processor that redacts sensitive fields."""
    for key in list(event_dict.keys()):
        if key.lower() in _SENSITIVE_KEYS:
            event_dict[key] = "***REDACTED***"
    return event_dict


# ------------------------------------------------------------------ #
# structlog configuration
# ------------------------------------------------------------------ #
def _build_processors(is_production: bool) -> list:
    shared = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        _scrub_sensitive,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    if is_production:
        shared.append(structlog.processors.JSONRenderer())
    else:
        shared.append(
            structlog.dev.ConsoleRenderer(
                colors=True,
                exception_formatter=structlog.dev.plain_traceback,
            )
        )
    return shared


def configure_logging() -> None:
    """Configure structlog and stdlib logging.  Call once at startup."""
    is_prod = settings.APP_ENV != "development"
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    logging.basicConfig(
        level=log_level,
        format="%(message)s",
    )
    # Silence noisy third-party loggers
    for noisy in ("uvicorn.access", "sqlalchemy.engine", "httpx", "httpcore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    structlog.configure(
        processors=_build_processors(is_prod),
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Return a structlog logger bound to *name*."""
    return structlog.get_logger(name)


# ------------------------------------------------------------------ #
# Request logging middleware
# ------------------------------------------------------------------ #
class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log every HTTP request with method, path, status, and duration.

    Authorization and cookie headers are **never** logged.
    """

    _SKIP_HEADERS = frozenset({"authorization", "cookie", "x-api-key", "x-auth-token"})

    def __init__(self, app: ASGIApp, *, exclude_paths: list[str] | None = None) -> None:
        super().__init__(app)
        self._logger = get_logger("http.access")
        self._exclude_paths: set[str] = set(exclude_paths or ["/health", "/metrics"])

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path in self._exclude_paths:
            return await call_next(request)

        start = time.perf_counter()
        response: Response | None = None
        try:
            response = await call_next(request)
            return response
        finally:
            elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
            status_code = response.status_code if response is not None else 500
            self._logger.info(
                "http_request",
                method=request.method,
                path=request.url.path,
                query=str(request.url.query) or None,
                status=status_code,
                duration_ms=elapsed_ms,
                client_host=request.client.host if request.client else None,
            )
