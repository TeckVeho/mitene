"""NotebookLM CLI login helpers."""

from __future__ import annotations

import json
import logging
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import httpx

from app.config import AUTH_COOKIE_NAMES, STORAGE_STATE
from app.services.notebooklm_gcs import download_storage_state_if_configured

logger = logging.getLogger(__name__)

# Browser-like UA for diagnostic GET (notebooklm-py's fetch_tokens uses plain httpx default UA).
_NOTEBOOKLM_PROBE_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

# Strip token-like material from HTML snippets before logging (never log cookie values).
_TOKENISH = re.compile(
    r"(?:g\.a[A-Za-z0-9._+=/-]{30,}|"
    r"GOCSPX-[A-Za-z0-9_-]+|"
    r"ya29\.[A-Za-z0-9_-]+|"
    r"[A-Za-z0-9_+=/-]{120,})"
)


def _mask_sensitive_log_fragment(text: str, max_len: int = 600) -> str:
    one_line = re.sub(r"\s+", " ", text).strip()
    if len(one_line) > max_len:
        one_line = one_line[:max_len] + "…"
    return _TOKENISH.sub("[REDACTED]", one_line)


async def _log_notebooklm_probe_context(cookie_dict: dict[str, str]) -> None:
    """Mirror fetch_tokens transport: GET homepage with Cookie header; log status/url/snippet (no cookie values)."""
    cookie_header = "; ".join(f"{k}={v}" for k, v in cookie_dict.items())
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://notebooklm.google.com/",
                headers={
                    "Cookie": cookie_header,
                    "User-Agent": _NOTEBOOKLM_PROBE_UA,
                },
                follow_redirects=True,
                timeout=30.0,
            )
    except Exception as probe_exc:
        logger.error(
            "NotebookLM auth probe GET failed: %s: %s",
            type(probe_exc).__name__,
            probe_exc,
            exc_info=True,
        )
        return

    snippet = _mask_sensitive_log_fragment(response.text)
    logger.error(
        "NotebookLM auth probe (after client failure): http_status=%s final_url=%s body_snippet=%s",
        response.status_code,
        str(response.url),
        snippet,
    )


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


async def validate_auth_live() -> bool:
    """Validate that saved Google session is usable by notebooklm-py by making an API call."""
    if not STORAGE_STATE.exists():
        return False

    from notebooklm.auth import load_auth_from_storage

    cookie_dict: dict[str, str] | None = None
    try:
        cookie_dict = load_auth_from_storage(STORAGE_STATE)
        logger.info(
            "NotebookLM auth check: extracted %d cookie names: %s",
            len(cookie_dict),
            ", ".join(sorted(cookie_dict.keys())),
        )
    except Exception:
        logger.exception("NotebookLM load_auth_from_storage failed")
        return False

    try:
        from notebooklm.client import NotebookLMClient

        async with await NotebookLMClient.from_storage(str(STORAGE_STATE)) as client:
            await client.notebooks.list()
            return True
    except Exception:
        logger.exception("NotebookLM validate_auth_live: NotebookLMClient failed")
        if cookie_dict is not None:
            await _log_notebooklm_probe_context(cookie_dict)
        return False


async def check_auth_status_strict() -> str:
    """Return auth status using a live API check as the definitive source of truth."""
    # Cloud Run: each revision instance has its own /tmp. After upload-session on instance A,
    # the next /auth/status request may hit instance B — refresh from GCS before validating.
    download_storage_state_if_configured()

    if not STORAGE_STATE.exists():
        return "not_logged_in"

    is_valid = await validate_auth_live()
    if not is_valid:
        logger.warning(
            "NotebookLM check_auth_status_strict: session not valid; see ERROR logs above for details."
        )
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
