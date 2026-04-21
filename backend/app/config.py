"""Paths and environment-derived settings (backend root)."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

UPLOADS_DIR = BASE_DIR / "uploads"
OUTPUTS_DIR = BASE_DIR / "outputs"
UPLOADS_DIR.mkdir(exist_ok=True)
OUTPUTS_DIR.mkdir(exist_ok=True)

MAX_CONCURRENT_JOBS = 3

_CORS_ORIGINS = [
    o.strip()
    for o in os.environ.get(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    ).split(",")
    if o.strip()
]

_ADMIN_EMAILS_LOWER: frozenset[str] = frozenset(
    e.strip().lower()
    for e in os.environ.get("ADMIN_EMAILS", "").split(",")
    if e.strip()
)

GITHUB_CLIENT_ID = os.environ.get("GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET = os.environ.get("GITHUB_CLIENT_SECRET", "")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")

# GCS (Terraform sets GCS_BUCKET on Cloud Run when enable_gcs)
GCS_BUCKET: str | None = os.environ.get("GCS_BUCKET", "").strip() or None


def _is_managed_google_cloud_runtime() -> bool:
    """Cloud Run (K_SERVICE) or App Engine (GAE_SERVICE)."""
    return bool(os.environ.get("K_SERVICE") or os.environ.get("GAE_SERVICE"))


def _notebooklm_force_gcs_sync() -> bool:
    return os.environ.get("NOTEBOOKLM_FORCE_GCS_SYNC", "").lower() in ("1", "true", "yes")


def _notebooklm_disable_gcs_sync() -> bool:
    return os.environ.get("NOTEBOOKLM_DISABLE_GCS_SYNC", "").lower() in ("1", "true", "yes")


# Object key inside GCS_BUCKET (default prefix for NotebookLM session file)
NOTEBOOKLM_GCS_OBJECT_KEY = (
    os.environ.get("NOTEBOOKLM_GCS_OBJECT_KEY", "notebooklm/storage_state.json").strip()
    or "notebooklm/storage_state.json"
)

# Sync storage_state.json to/from GCS when running on GCP with app bucket configured
NOTEBOOKLM_GCS_SYNC_ENABLED = (
    bool(GCS_BUCKET)
    and not _notebooklm_disable_gcs_sync()
    and (_is_managed_google_cloud_runtime() or _notebooklm_force_gcs_sync())
)

# NotebookLM Playwright session file.
# On GCP + GCS_BUCKET: default to /tmp (writable) and sync from GCS on startup / after login.
# Some notebooklm-py versions call load_httpx_cookies() without a path; they then resolve
# ~/.notebooklm via NOTEBOOKLM_HOME. Docker user mitene has HOME=/app, so set NOTEBOOKLM_HOME
# to match our sync dir (setdefault only — operator can override via env).
_NOTEBOOKLM_STORAGE_STATE_RAW = os.environ.get("NOTEBOOKLM_STORAGE_STATE", "").strip()
if _NOTEBOOKLM_STORAGE_STATE_RAW:
    STORAGE_STATE = Path(_NOTEBOOKLM_STORAGE_STATE_RAW).expanduser()
elif NOTEBOOKLM_GCS_SYNC_ENABLED:
    os.environ.setdefault("NOTEBOOKLM_HOME", "/tmp/.notebooklm")
    STORAGE_STATE = Path("/tmp/.notebooklm/storage_state.json")
else:
    STORAGE_STATE = Path.home() / ".notebooklm" / "storage_state.json"
AUTH_COOKIE_NAMES = frozenset({"SID", "__Secure-1PSID", "__Secure-3PSID", "SAPISID"})
