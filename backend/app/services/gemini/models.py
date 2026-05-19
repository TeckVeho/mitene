"""Default Gemini model identifiers (Developer API and Vertex AI share names)."""

DEFAULT_LLM_MODEL = "gemini-2.5-flash"
DEFAULT_TTS_MODEL = "gemini-2.5-flash-tts"

# Gemini TTS on Vertex AI is not available in asia-northeast1; use global endpoint.
TTS_VERTEX_LOCATION = "global"
