"""Factory for google-genai Client (Developer API or Vertex AI)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Mapping

from app.services.gemini.settings import GeminiConfigError, GeminiSettings, load_gemini_settings

if TYPE_CHECKING:
    from google import genai


def create_genai_client(settings: GeminiSettings) -> genai.Client:
    """Build a google-genai Client from resolved settings."""
    settings.validate_for_client()

    from google import genai

    if settings.uses_vertex:
        return genai.Client(
            vertexai=True,
            project=settings.project_id,
            location=settings.location,
        )
    return genai.Client(api_key=settings.api_key)


def get_genai_client(environ: Mapping[str, str] | None = None) -> genai.Client:
    """Load settings from env (or explicit mapping) and return a Client."""
    settings = load_gemini_settings(environ)
    return create_genai_client(settings)


__all__ = ["create_genai_client", "get_genai_client", "GeminiConfigError"]
