"""Unit tests for Gemini client settings and backend resolution."""

from __future__ import annotations

import pytest

from app.services.gemini import (
    DEFAULT_TTS_MODEL,
    GeminiConfigError,
    TTS_VERTEX_LOCATION,
    create_genai_client,
    create_genai_tts_client,
    load_gemini_settings,
    resolve_gemini_backend,
)


def test_resolve_backend_api_key_by_default() -> None:
    assert resolve_gemini_backend({}) == "api_key"


def test_resolve_backend_api_key_when_vertex_false() -> None:
    assert resolve_gemini_backend({"VERTEX_AI": "false"}) == "api_key"


def test_resolve_backend_vertex_when_true() -> None:
    assert resolve_gemini_backend({"VERTEX_AI": "true"}) == "vertex"
    assert resolve_gemini_backend({"VERTEX_AI": "1"}) == "vertex"
    assert resolve_gemini_backend({"VERTEX_AI": "yes"}) == "vertex"


def test_load_settings_api_key_mode() -> None:
    settings = load_gemini_settings(
        {
            "GEMINI_API_KEY": "test-key",
            "VERTEX_AI": "false",
        }
    )
    assert settings.backend == "api_key"
    assert settings.api_key == "test-key"
    assert settings.project_id is None
    assert settings.location == "asia-northeast1"


def test_load_settings_vertex_mode() -> None:
    settings = load_gemini_settings(
        {
            "VERTEX_AI": "true",
            "GCP_PROJECT_ID": "my-project",
            "VERTEX_AI_LOCATION": "us-central1",
        }
    )
    assert settings.uses_vertex is True
    assert settings.project_id == "my-project"
    assert settings.location == "us-central1"
    assert settings.api_key is None


def test_load_settings_vertex_falls_back_to_google_cloud_project() -> None:
    settings = load_gemini_settings(
        {
            "VERTEX_AI": "true",
            "GOOGLE_CLOUD_PROJECT": "fallback-project",
        }
    )
    assert settings.project_id == "fallback-project"


def test_validate_vertex_requires_project() -> None:
    settings = load_gemini_settings({"VERTEX_AI": "true"})
    with pytest.raises(GeminiConfigError, match="GCP_PROJECT_ID"):
        settings.validate_for_client()


def test_validate_api_key_requires_key() -> None:
    settings = load_gemini_settings({})
    with pytest.raises(GeminiConfigError, match="GEMINI_API_KEY"):
        settings.validate_for_client()


def test_validate_api_key_rejects_placeholder() -> None:
    settings = load_gemini_settings({"GEMINI_API_KEY": "your-gemini-api-key-here"})
    with pytest.raises(GeminiConfigError, match="GEMINI_API_KEY"):
        settings.validate_for_client()


def test_create_client_api_key_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict = {}

    class FakeClient:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr("google.genai.Client", FakeClient)

    settings = load_gemini_settings({"GEMINI_API_KEY": "secret-key"})
    create_genai_client(settings)

    assert captured == {"api_key": "secret-key"}


def test_create_client_vertex_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict = {}

    class FakeClient:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr("google.genai.Client", FakeClient)

    settings = load_gemini_settings(
        {
            "VERTEX_AI": "true",
            "GCP_PROJECT_ID": "proj-1",
            "VERTEX_AI_LOCATION": "asia-northeast1",
        }
    )
    create_genai_client(settings)

    assert captured == {
        "vertexai": True,
        "project": "proj-1",
        "location": "asia-northeast1",
    }


def test_default_tts_model_and_vertex_location() -> None:
    assert DEFAULT_TTS_MODEL == "gemini-2.5-flash-tts"
    assert TTS_VERTEX_LOCATION == "global"


def test_create_tts_client_vertex_uses_global_location(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict = {}

    class FakeClient:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr("google.genai.Client", FakeClient)

    settings = load_gemini_settings(
        {
            "VERTEX_AI": "true",
            "GCP_PROJECT_ID": "proj-1",
            "VERTEX_AI_LOCATION": "asia-northeast1",
        }
    )
    create_genai_tts_client(settings)

    assert captured == {
        "vertexai": True,
        "project": "proj-1",
        "location": "global",
    }
