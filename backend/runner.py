"""Backward-compatible export of the background job runner."""
from app.services.runner import run_job  # noqa: F401

__all__ = ["run_job"]
