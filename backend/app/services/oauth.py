"""GitHub OAuth helper functions."""

from __future__ import annotations

import base64
import json
import os
from typing import Optional

from app.config import _CORS_ORIGINS


def allowed_oauth_frontends() -> set[str]:
    """Browser origins allowed as GitHub OAuth return target (localStorage is per-origin)."""
    bases: set[str] = set()
    fu = (os.environ.get("FRONTEND_URL") or "http://localhost:3000").strip().rstrip("/")
    if fu:
        bases.add(fu)
    for o in _CORS_ORIGINS:
        o = o.strip().rstrip("/")
        if o:
            bases.add(o)
    return bases


def resolve_oauth_frontend(requested: Optional[str]) -> str:
    req = (requested or "").strip().rstrip("/")
    allowed = allowed_oauth_frontends()
    if req in allowed:
        return req
    return (os.environ.get("FRONTEND_URL") or "http://localhost:3000").strip().rstrip("/")


def oauth_state_encode(frontend_base: str) -> str:
    raw = json.dumps({"fb": frontend_base}, separators=(",", ":"))
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def oauth_state_decode(state: Optional[str]) -> Optional[str]:
    if not state:
        return None
    try:
        pad = "=" * (-len(state) % 4)
        data = json.loads(base64.urlsafe_b64decode(state + pad))
        fb = data.get("fb")
        if isinstance(fb, str):
            return fb.strip().rstrip("/")
    except (json.JSONDecodeError, ValueError, TypeError):
        pass
    return None
