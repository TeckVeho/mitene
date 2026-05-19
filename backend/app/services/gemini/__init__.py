"""Gemini / Vertex AI client abstraction."""

from app.services.gemini.client import (
    create_genai_client,
    create_genai_tts_client,
    get_genai_client,
    get_genai_tts_client,
)
from app.services.gemini.models import (
    DEFAULT_LLM_MODEL,
    DEFAULT_TTS_MODEL,
    TTS_VERTEX_LOCATION,
)
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
    "TTS_VERTEX_LOCATION",
    "GeminiBackend",
    "GeminiConfigError",
    "GeminiSettings",
    "create_genai_client",
    "create_genai_tts_client",
    "get_genai_client",
    "get_genai_tts_client",
    "load_gemini_settings",
    "resolve_gemini_backend",
]
