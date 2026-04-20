"""Unit tests for wiki GCS helpers (mocked GCS; no live cloud)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.services import wiki_sync


def test_build_wiki_directories_from_md_files() -> None:
    out = wiki_sync._build_wiki_directories_from_md_files(["root.md", "sec/a.md", "sec/b.md"])
    paths = {d["path"] for d in out}
    assert paths == {"", "sec"}
    root = next(d for d in out if d["path"] == "")
    assert root["count"] == 1


def test_list_all_md_rel_paths_gcs_filters_and_strips_prefix() -> None:
    with patch.object(
        wiki_sync.storage_mod,
        "gcs_list_object_keys_under_prefix",
        return_value=["wiki-repo/a.md", "wiki-repo/nested/x.md", "wiki-repo/readme.txt", "wiki-repo/"],
    ):
        rels = wiki_sync._list_all_md_rel_paths_gcs()
    assert set(rels) == {"a.md", "nested/x.md"}


def test_gcs_object_key_for_rel() -> None:
    assert wiki_sync._gcs_object_key_for_rel("foo/bar.md") == "wiki-repo/foo/bar.md"
    assert wiki_sync._gcs_object_key_for_rel("/x.md") == "wiki-repo/x.md"


def test_wiki_uses_gcs_respects_resolve_storage(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MITENE_ENV", raising=False)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setenv("GCS_BUCKET", "test-bucket")
    monkeypatch.delenv("S3_BUCKET_NAME", raising=False)
    monkeypatch.delenv("AWS_REGION", raising=False)
    assert wiki_sync._wiki_uses_gcs() is True

    monkeypatch.setenv("STORAGE_BACKEND", "local")
    assert wiki_sync._wiki_uses_gcs() is False
