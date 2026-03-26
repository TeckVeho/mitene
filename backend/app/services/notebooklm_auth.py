"""NotebookLM CLI login helpers."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

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
