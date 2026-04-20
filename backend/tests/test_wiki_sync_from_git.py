"""Tests for sync_wiki_from_git_source (no live Git/GCS)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.services import wiki_sync


@pytest.fixture(autouse=True)
def reset_sync_status():
    wiki_sync._sync_status["is_syncing"] = False
    wiki_sync._sync_status["wiki_source_syncing"] = False
    wiki_sync._sync_status["error"] = None
    yield
    wiki_sync._sync_status["is_syncing"] = False
    wiki_sync._sync_status["wiki_source_syncing"] = False


def test_sync_wiki_from_git_source_requires_repo_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(wiki_sync, "WIKI_GIT_REPO_URL", None)
    out = wiki_sync.sync_wiki_from_git_source()
    assert out["ok"] is False
    assert "WIKI_GIT_REPO_URL" in out["message"]


def test_sync_wiki_from_git_git_mode_calls_clone_or_pull(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(wiki_sync, "WIKI_GIT_REPO_URL", "https://example.com/wiki.git")
    monkeypatch.setattr(wiki_sync, "_wiki_uses_gcs", lambda: False)
    with patch.object(wiki_sync, "_clone_or_pull", return_value=(True, "abc123")) as m:
        out = wiki_sync.sync_wiki_from_git_source()
    assert out["ok"] is True
    assert out.get("hash") == "abc123"
    m.assert_called_once()
    args, kwargs = m.call_args
    assert "https://example.com/wiki.git" in args[0]


def test_sync_wiki_from_git_gcs_uploads(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setattr(wiki_sync, "WIKI_GIT_REPO_URL", "https://example.com/wiki.git")
    monkeypatch.setattr(wiki_sync, "_wiki_uses_gcs", lambda: True)

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "a.md").write_text("# A", encoding="utf-8")
    sub = repo / "sub"
    sub.mkdir()
    (sub / "b.md").write_text("# B", encoding="utf-8")

    uploaded: list[tuple[str, bytes]] = []

    def fake_clone_or_pull(url, local_path, branch, quiet=False):
        import shutil

        shutil.copytree(repo, local_path, dirs_exist_ok=True)
        return True, "deadbeef"

    def fake_upload(key: str, data: bytes, content_type: str = "") -> None:
        uploaded.append((key, data))

    with patch.object(wiki_sync, "_clone_or_pull", side_effect=fake_clone_or_pull):
        with patch.object(wiki_sync.storage_mod, "gcs_upload_bytes", side_effect=fake_upload):
            out = wiki_sync.sync_wiki_from_git_source()

    assert out["ok"] is True
    assert out.get("uploaded") == 2
    keys = {k for k, _ in uploaded}
    assert "wiki-repo/a.md" in keys
    assert "wiki-repo/sub/b.md" in keys
