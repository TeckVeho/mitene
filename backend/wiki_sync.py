"""Backward-compatible Wiki sync module."""
from app.services.wiki_sync import (  # noqa: F401
    get_sync_status,
    get_wiki_directories,
    sync_wiki_from_directory,
)

__all__ = ["get_sync_status", "get_wiki_directories", "sync_wiki_from_directory"]
