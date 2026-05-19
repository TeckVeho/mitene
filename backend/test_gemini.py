"""
Gemini API 動作確認スクリプト
.env から設定を読み込み、Developer API または Vertex AI でテキスト生成を実行します。
"""

import os
import sys
from pathlib import Path

# backend/ を import path に追加
_backend_dir = Path(__file__).resolve().parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

# .env を手動で読み込む（python-dotenv 不要）
env_path = _backend_dir / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip())

from app.services.gemini import (  # noqa: E402
    DEFAULT_LLM_MODEL,
    GeminiConfigError,
    get_genai_client,
    load_gemini_settings,
)

settings = load_gemini_settings()

print("=== Gemini API テスト ===")
if settings.uses_vertex:
    print(f"モード: Vertex AI (project={settings.project_id}, location={settings.location})")
else:
    key = settings.api_key or ""
    print(f"モード: Developer API (APIキー: {key[:10]}... 先頭10文字のみ表示)")
print()

try:
    client = get_genai_client()
except GeminiConfigError as exc:
    print(f"ERROR: {exc}")
    raise SystemExit(1) from exc

print(f"▶ テキスト生成（{DEFAULT_LLM_MODEL}）")
response = client.models.generate_content(
    model=DEFAULT_LLM_MODEL,
    contents="こんにちは。あなたは何ができますか？3行以内で答えてください。",
)
print(response.text)
print()
print("=== テスト完了 ===")
