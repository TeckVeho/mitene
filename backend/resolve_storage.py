"""
Resolve object storage backend: GCS > S3 > local (aligned with kumu resolveStorageKind).

Uses os.environ when ``environ`` is omitted. Callers may pass an explicit mapping for tests.
"""

from __future__ import annotations

import os
from typing import Literal, Mapping, overload

ResolvedStorageKind = Literal["gcs", "s3", "local"]


def _get(environ: Mapping[str, str], key: str, default: str = "") -> str:
    v = environ.get(key, default)
    if v is None:
        return default
    return v if isinstance(v, str) else str(v)


def _has_s3_config(environ: Mapping[str, str]) -> bool:
    return bool(_get(environ, "S3_BUCKET_NAME").strip() and _get(environ, "AWS_REGION").strip())


def _has_gcs_config(environ: Mapping[str, str]) -> bool:
    return bool(_get(environ, "GCS_BUCKET").strip())


@overload
def resolve_storage_kind(environ: None = None) -> ResolvedStorageKind: ...


@overload
def resolve_storage_kind(environ: Mapping[str, str]) -> ResolvedStorageKind: ...


def resolve_storage_kind(environ: Mapping[str, str] | None = None) -> ResolvedStorageKind:
    """
    - ``MITENE_ENV=test`` or ``PYTEST_CURRENT_TEST`` (process env only): ``local``.
    - ``STORAGE_BACKEND``: force ``gcs`` / ``s3`` / ``local`` when valid for available config.
    - Else: ``GCS_BUCKET`` → ``gcs``; else S3 config → ``s3``; else ``local``.
    """
    if environ is None:
        env = os.environ
        if _get(env, "MITENE_ENV").lower() == "test" or _get(env, "PYTEST_CURRENT_TEST"):
            return "local"
    else:
        env = environ

    forced = _get(env, "STORAGE_BACKEND").strip().lower()
    if forced == "local":
        return "local"
    if forced == "gcs":
        return "gcs" if _has_gcs_config(env) else "local"
    if forced == "s3":
        return "s3" if _has_s3_config(env) else "local"

    if _has_gcs_config(env):
        return "gcs"
    if _has_s3_config(env):
        return "s3"
    return "local"
