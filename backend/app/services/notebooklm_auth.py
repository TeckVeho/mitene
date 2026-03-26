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
    """Validate that saved Google session can still access NotebookLM."""
    if not STORAGE_STATE.exists():
        return False

    try:
        cookies = _load_storage_cookies()
        cookie_jar = _build_google_cookie_jar(cookies)
        if not cookie_jar:
            return False

        async with httpx.AsyncClient(
            timeout=timeout_sec,
            follow_redirects=False,
            headers={"User-Agent": "mitene-auth-check/1.0"},
        ) as client:
            res = await client.get("https://notebooklm.google.com/", cookies=cookie_jar)
            location = (res.headers.get("location") or "").lower()
            if res.status_code in {301, 302, 303, 307, 308} and "accounts.google.com" in location:
                return False
            if res.status_code != 200:
                return False

            body = res.text.lower()
            if "servicelogin" in body and "accounts.google.com" in body:
                return False
            return True
    except Exception:
        return False


async def check_auth_status_strict() -> str:
    """Return auth status using storage pre-check + live session validation."""
    precheck = check_auth_from_storage()
    if precheck != "authenticated":
        return precheck
    is_live_valid = await validate_auth_live()
    return "authenticated" if is_live_valid else "session_expired"


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
