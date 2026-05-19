"""Gemini / Vertex AI client abstraction."""

from app.services.gemini.client import create_genai_client, get_genai_client
from app.services.gemini.models import DEFAULT_LLM_MODEL, DEFAULT_TTS_MODEL
from app.services.gemini.settings import (
    GeminiBackend,
    GeminiConfigError,
    GeminiSettings,
    load_gemini_settings,
    resolve_gemini_backend,
)

__all__ = [
    "DEFAULT_LLM_MODEL",
    "DEFAULT_TTS_MODEL",
    "GeminiBackend",
    "GeminiConfigError",
    "GeminiSettings",
    "create_genai_client",
    "get_genai_client",
    "load_gemini_settings",
    "resolve_gemini_backend",
]
