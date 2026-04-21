"""Parse Cookie-Editor export or Playwright storage_state JSON into a normalized storage_state dict."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

_NUMERIC_EXPIRES = re.compile(r"^-?\d+(\.\d+)?$")


def _same_site_value(c: dict) -> str:
    raw = c.get("sameSite")
    if raw is None:
        raw = ""
    if not isinstance(raw, str):
        return "Lax"
    same_site_raw = raw.strip().lower()
    if same_site_raw in ("no_restriction", "none"):
        return "None"
    if same_site_raw == "strict":
        return "Strict"
    if same_site_raw == "lax":
        return "Lax"
    if not same_site_raw:
        return "None" if c.get("secure") else "Lax"
    return "Lax"


def _expires_int(c: dict) -> int:
    for key in ("expirationDate", "expires"):
        v = c.get(key)
        if v is None:
            continue
        if isinstance(v, (int, float)) and v != -1:
            return int(round(float(v)))
        if isinstance(v, str):
            s = v.strip()
            if not s:
                continue
            if _NUMERIC_EXPIRES.fullmatch(s):
                n = float(s)
                if n != -1:
                    return int(round(n))
                continue
            try:
                iso = s[:-1] + "+00:00" if s.endswith("Z") else s
                dt = datetime.fromisoformat(iso)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return int(dt.timestamp())
            except ValueError:
                continue
    return -1


def _cookie_editor_row_to_playwright(c: dict) -> dict | None:
    if not isinstance(c, dict):
        return None
    name = (c.get("name") or "").strip()
    value = c.get("value")
    if not name or value is None or value == "":
        return None
    return {
        "name": name,
        "value": str(value),
        "domain": (c.get("domain") or "").strip() or "",
        "path": (c.get("path") or "/").strip() or "/",
        "expires": _expires_int(c),
        "httpOnly": bool(c.get("httpOnly")),
        "secure": bool(c.get("secure")),
        "sameSite": _same_site_value(c),
    }


def _playwright_cookie_row_normalize(c: dict) -> dict | None:
    if not isinstance(c, dict):
        return None
    name = (c.get("name") or "").strip()
    value = c.get("value")
    if not name or value is None or value == "":
        return None
    return {
        "name": name,
        "value": str(value),
        "domain": (c.get("domain") or "").strip() or "",
        "path": (c.get("path") or "/").strip() or "/",
        "expires": _expires_int(c),
        "httpOnly": bool(c.get("httpOnly")),
        "secure": bool(c.get("secure")),
        "sameSite": _same_site_value(c),
    }


def _normalize_origins(raw: Any) -> list[dict]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        return []
    out: list[dict] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        origin = item.get("origin")
        if not origin or not isinstance(origin, str):
            continue
        ls_raw = item.get("localStorage", [])
        local_storage: list[dict[str, str]] = []
        if isinstance(ls_raw, list):
            for row in ls_raw:
                if not isinstance(row, dict):
                    continue
                n = row.get("name")
                if n is None:
                    continue
                local_storage.append({"name": str(n), "value": str(row.get("value", ""))})
        out.append({"origin": origin, "localStorage": local_storage})
    return out


def session_json_to_playwright_state(raw_data: Any) -> dict[str, Any]:
    """Build ``{"cookies": [...], "origins": [...]}`` from API payload.

    Accepts:
    - Cookie-Editor: JSON array of cookie objects.
    - Playwright: object with ``cookies`` (and optional ``origins``).

    Raises:
        ValueError: invalid shape or no usable cookies.
    """
    if isinstance(raw_data, list):
        cookies: list[dict] = []
        for c in raw_data:
            row = _cookie_editor_row_to_playwright(c)
            if row:
                cookies.append(row)
        if not cookies:
            raise ValueError("No valid cookies found in the provided JSON.")
        return {"cookies": cookies, "origins": []}

    if isinstance(raw_data, dict) and isinstance(raw_data.get("cookies"), list):
        cookies = []
        for c in raw_data["cookies"]:
            row = _playwright_cookie_row_normalize(c)
            if row:
                cookies.append(row)
        if not cookies:
            raise ValueError("No valid cookies found in the provided JSON.")
        return {"cookies": cookies, "origins": _normalize_origins(raw_data.get("origins"))}

    raise ValueError(
        "Expected a JSON array (Cookie-Editor) or an object with a 'cookies' array (Playwright storage_state)."
    )


def assert_has_sid(playwright_state: dict[str, Any]) -> None:
    names = {c.get("name") for c in playwright_state.get("cookies", []) if isinstance(c, dict)}
    if "SID" not in names:
        raise ValueError(
            "必須のクッキー SID がありません。Google のセッション Cookie の多くは httpOnly のため、"
            "ページ内スクリプト（ブックマークレット）では取得できません。"
            "Cookie-Editor で JSON をエクスポートするか、notebooklm login を利用してください。"
        )
