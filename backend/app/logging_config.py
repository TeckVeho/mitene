"""Central logging setup for API and Cloud Run worker."""

from __future__ import annotations

import logging
import os

_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_DEFAULT_APP_LEVEL = "INFO"
_DEFAULT_NOTEBOOKLM_LEVEL = "WARNING"
_QUIET_HTTP_LOGGERS = ("httpx", "httpcore")


def _level_from_env(name: str, default: str) -> int:
    raw = os.environ.get(name, default).strip().upper() or default.upper()
    return getattr(logging, raw, getattr(logging, default.upper(), logging.INFO))


def configure_logging() -> None:
    """Configure root logging and quiet noisy third-party loggers."""
    logging.basicConfig(
        level=_level_from_env("LOG_LEVEL", _DEFAULT_APP_LEVEL),
        format=_LOG_FORMAT,
    )
    logging.getLogger("notebooklm").setLevel(
        _level_from_env("NOTEBOOKLM_LOG_LEVEL", _DEFAULT_NOTEBOOKLM_LEVEL)
    )
    for name in _QUIET_HTTP_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)
