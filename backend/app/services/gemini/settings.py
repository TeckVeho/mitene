"""Gemini / Vertex AI runtime settings resolved from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal, Mapping, overload

GeminiBackend = Literal["vertex", "api_key"]

_DEFAULT_VERTEX_LOCATION = "asia-northeast1"


class GeminiConfigError(ValueError):
    """Raised when required Gemini / Vertex configuration is missing or invalid."""


def _get(environ: Mapping[str, str], key: str, default: str = "") -> str:
    v = environ.get(key, default)
    if v is None:
        return default
    return v if isinstance(v, str) else str(v)


def _truthy(value: str) -> bool:
    return value.strip().lower() in ("1", "true", "yes", "on")


def resolve_gemini_backend(environ: Mapping[str, str]) -> GeminiBackend:
    if _truthy(_get(environ, "VERTEX_AI")):
        return "vertex"
    return "api_key"


@dataclass(frozen=True)
class GeminiSettings:
    backend: GeminiBackend
    api_key: str | None
    project_id: str | None
    location: str

    @property
    def uses_vertex(self) -> bool:
        return self.backend == "vertex"

    def validate_for_client(self) -> None:
        if self.uses_vertex:
            if not (self.project_id or "").strip():
                raise GeminiConfigError(
                    "VERTEX_AI is enabled but GCP_PROJECT_ID (or GOOGLE_CLOUD_PROJECT) is not set."
                )
            return
        key = (self.api_key or "").strip()
        if not key or key == "your-gemini-api-key-here":
            raise GeminiConfigError(
                "GEMINI_API_KEY is required when VERTEX_AI is not enabled. "
                "Set it in backend/.env for local development."
            )


@overload
def load_gemini_settings(environ: None = None) -> GeminiSettings: ...


@overload
def load_gemini_settings(environ: Mapping[str, str]) -> GeminiSettings: ...


def load_gemini_settings(environ: Mapping[str, str] | None = None) -> GeminiSettings:
    env = os.environ if environ is None else environ
    backend = resolve_gemini_backend(env)
    project_id = (
        _get(env, "GCP_PROJECT_ID").strip()
        or _get(env, "GOOGLE_CLOUD_PROJECT").strip()
        or None
    )
    location = (
        _get(env, "VERTEX_AI_LOCATION").strip()
        or _get(env, "GOOGLE_CLOUD_LOCATION").strip()
        or _DEFAULT_VERTEX_LOCATION
    )
    api_key_raw = _get(env, "GEMINI_API_KEY").strip()
    api_key = api_key_raw or None

    return GeminiSettings(
        backend=backend,
        api_key=api_key,
        project_id=project_id,
        location=location,
    )
