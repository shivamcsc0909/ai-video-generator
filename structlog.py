"""Compatibility fallback shim for structlog using standard Python library logging.

Allows the application to run smoothly both before and after full virtualenv package installation.
"""

from __future__ import annotations

import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


class _BoundLogger:
    def __init__(self, logger: logging.Logger):
        self._logger = logger

    def info(self, event: str, **kwargs):
        extra_str = " ".join(f"{k}={v}" for k, v in kwargs.items()) if kwargs else ""
        self._logger.info(f"{event} {extra_str}".strip())

    def debug(self, event: str, **kwargs):
        extra_str = " ".join(f"{k}={v}" for k, v in kwargs.items()) if kwargs else ""
        self._logger.debug(f"{event} {extra_str}".strip())

    def warning(self, event: str, **kwargs):
        extra_str = " ".join(f"{k}={v}" for k, v in kwargs.items()) if kwargs else ""
        self._logger.warning(f"{event} {extra_str}".strip())

    def error(self, event: str, **kwargs):
        extra_str = " ".join(f"{k}={v}" for k, v in kwargs.items()) if kwargs else ""
        self._logger.error(f"{event} {extra_str}".strip())


def get_logger(name: str = "ai_video_studio") -> _BoundLogger:
    return _BoundLogger(logging.getLogger(name))


def configure(*args, **kwargs):
    pass
