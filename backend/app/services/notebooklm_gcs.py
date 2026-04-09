"""Download/upload NotebookLM storage_state.json to GCS (shared app bucket, dedicated prefix)."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from app.config import (
    GCS_BUCKET,
    NOTEBOOKLM_GCS_OBJECT_KEY,
    NOTEBOOKLM_GCS_SYNC_ENABLED,
    STORAGE_STATE,
)

logger = logging.getLogger(__name__)


def _client():
    from google.cloud import storage

    return storage.Client()


def download_storage_state_if_configured() -> None:
    """On startup: pull latest session file from GCS into STORAGE_STATE path if syncing is enabled."""
    if not NOTEBOOKLM_GCS_SYNC_ENABLED or not GCS_BUCKET:
        return
    dest = Path(STORAGE_STATE)
    try:
        bucket = _client().bucket(GCS_BUCKET)
        blob = bucket.blob(NOTEBOOKLM_GCS_OBJECT_KEY)
        if not blob.exists():
            logger.info(
                "NotebookLM GCS: object gs://%s/%s not found (first deploy or empty)",
                GCS_BUCKET,
                NOTEBOOKLM_GCS_OBJECT_KEY,
            )
            return
        dest.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        blob.download_to_filename(str(dest))
        try:
            dest.chmod(0o600)
        except OSError:
            pass
        logger.info(
            "NotebookLM GCS: downloaded gs://%s/%s -> %s",
            GCS_BUCKET,
            NOTEBOOKLM_GCS_OBJECT_KEY,
            dest,
        )
    except Exception as exc:
        logger.warning(
            "NotebookLM GCS: download failed (continuing without remote session): %s",
            exc,
        )


def upload_storage_state_if_configured() -> None:
    """After saving storage_state locally, push to GCS so new revisions keep the session."""
    if not NOTEBOOKLM_GCS_SYNC_ENABLED or not GCS_BUCKET:
        return
    path = Path(STORAGE_STATE)
    if not path.is_file():
        logger.warning("NotebookLM GCS: skip upload, local file missing: %s", path)
        return
    try:
        bucket = _client().bucket(GCS_BUCKET)
        blob = bucket.blob(NOTEBOOKLM_GCS_OBJECT_KEY)
        blob.upload_from_filename(str(path), content_type="application/json")
        logger.info(
            "NotebookLM GCS: uploaded %s -> gs://%s/%s",
            path,
            GCS_BUCKET,
            NOTEBOOKLM_GCS_OBJECT_KEY,
        )
    except Exception as exc:
        logger.error("NotebookLM GCS: upload failed: %s", exc)
