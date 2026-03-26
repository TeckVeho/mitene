"""NotebookLM CLI login helpers."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

import httpx

from app.config import AUTH_COOKIE_NAMES, STORAGE_STATE


def check_auth_from_storage() -> str:
    if not STORAGE_STATE.exists():
        return "not_logged_in"
    try:
        data = json.loads(STORAGE_STATE.read_text())
        cookies = {c["name"]: c for c in data.get("cookies", [])}
        now = time.time()
        for name in AUTH_COOKIE_NAMES:
            if name not in cookies:
                return "session_expired"
            exp = cookies[name].get("expires", -1)
            if exp != -1 and exp < now:
                return "session_expired"
        return "authenticated"
    except Exception:
        return "session_expired"


def _load_storage_cookies() -> list[dict]:
    data = json.loads(STORAGE_STATE.read_text())
    cookies = data.get("cookies", [])
    if not isinstance(cookies, list):
        return []
    return [c for c in cookies if isinstance(c, dict)]


def _build_google_cookie_jar(cookies: list[dict]) -> dict[str, str]:
    now = time.time()
    jar: dict[str, str] = {}
    for cookie in cookies:
        name = cookie.get("name")
        value = cookie.get("value")
        domain = str(cookie.get("domain", ""))
        exp = cookie.get("expires", -1)
        if not name or value is None:
            continue
        if "google.com" not in domain:
            continue
        if exp != -1 and exp < now:
            continue
        jar[str(name)] = str(value)
    return jar


async def validate_auth_live(timeout_sec: float = 8.0) -> bool:
    """Validate that saved Google session is usable by notebooklm-py."""
    if not STORAGE_STATE.exists():
        return False

    try:
        from notebooklm.auth import AuthTokens

        tokens = AuthTokens.from_storage(str(STORAGE_STATE))
        # If from_storage succeeds and returns tokens, the auth is valid
        return tokens is not None
    except Exception:
        return False


async def check_auth_status_strict() -> str:
    """Return auth status using storage pre-check + library validation."""
    precheck = check_auth_from_storage()
    if precheck == "not_logged_in":
        return precheck
    # Use notebooklm-py's own validation instead of httpx
    is_valid = await validate_auth_live()
    return "authenticated" if is_valid else "session_expired"


def find_notebooklm() -> str:
    cmd = shutil.which("notebooklm")
    if cmd:
        return cmd
    bin_dir = Path(sys.executable).parent
    candidate = bin_dir / "notebooklm"
    if candidate.exists():
        return str(candidate)
    for prefix in [
        "/Library/Frameworks/Python.framework/Versions/3.10/bin",
        "/Library/Frameworks/Python.framework/Versions/3.11/bin",
        "/Library/Frameworks/Python.framework/Versions/3.12/bin",
        "/usr/local/bin",
        "/opt/homebrew/bin",
        str(Path.home() / ".local" / "bin"),
    ]:
        candidate = Path(prefix) / "notebooklm"
        if candidate.exists():
            return str(candidate)
    raise FileNotFoundError(
        "notebooklm コマンドが見つかりません。"
        "`pip install 'notebooklm-py[browser]'` でインストールしてください。"
    )
