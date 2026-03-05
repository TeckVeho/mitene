"""
APIキー認証モジュール
環境変数 NOTEVIDEO_API_KEYS にカンマ区切りでAPIキーを設定する。
未設定の場合は開発用フリーアクセスとなる。
"""

import os

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


def _load_api_keys() -> set[str]:
    raw = os.environ.get("NOTEVIDEO_API_KEYS", "")
    return {k.strip() for k in raw.split(",") if k.strip()}


async def verify_api_key(api_key: str | None = Security(API_KEY_HEADER)) -> str:
    """
    X-API-Key ヘッダーを検証する FastAPI Dependency。

    - NOTEVIDEO_API_KEYS が未設定の場合: 認証スキップ（開発環境向け）
    - キーが一致しない場合: 401 Unauthorized
    - キーが一致した場合: そのキー文字列を返す
    """
    keys = _load_api_keys()
    if not keys:
        return "anonymous"
    if not api_key or api_key not in keys:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return api_key
