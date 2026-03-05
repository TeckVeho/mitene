"""
Gemini API 動作確認スクリプト（方法A）
.env から GEMINI_API_KEY を読み込んでテキスト生成を実行します。
"""

import os
from pathlib import Path

# .env を手動で読み込む（python-dotenv 不要）
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip())

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key or api_key == "your-gemini-api-key-here":
    print("ERROR: GEMINI_API_KEY が設定されていません。backend/.env を確認してください。")
    raise SystemExit(1)

from google import genai

client = genai.Client(api_key=api_key)

print("=== Gemini API テスト ===")
print(f"APIキー: {api_key[:10]}...（先頭10文字のみ表示）")
print()

print("▶ テキスト生成（gemini-2.5-flash）")
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="こんにちは。あなたは何ができますか？3行以内で答えてください。",
)
print(response.text)
print()
print("=== テスト完了 ===")
