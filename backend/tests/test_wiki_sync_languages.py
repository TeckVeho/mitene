"""Tests for video language selection in wiki sync."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.wiki import WikiSyncDirectoryRequest


def test_wiki_sync_directory_request_languages_default() -> None:
    req = WikiSyncDirectoryRequest(path="sec")
    assert req.languages == ["ja", "vi"]


def test_wiki_sync_directory_request_languages_single() -> None:
    req = WikiSyncDirectoryRequest(path="sec", languages=["vi"])
    assert req.languages == ["vi"]


def test_wiki_sync_directory_request_languages_dedup_and_order() -> None:
    req = WikiSyncDirectoryRequest(path="sec", languages=["vi", "ja", "vi"])
    assert req.languages == ["ja", "vi"]


def test_wiki_sync_directory_request_languages_empty_rejected() -> None:
    with pytest.raises(ValidationError):
        WikiSyncDirectoryRequest(path="sec", languages=[])


def test_wiki_sync_directory_request_languages_invalid_rejected() -> None:
    with pytest.raises(ValidationError):
        WikiSyncDirectoryRequest(path="sec", languages=["en"])
