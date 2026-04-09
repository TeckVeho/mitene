"""Unit tests for resolve_storage_kind (explicit env dicts; no live cloud)."""

from __future__ import annotations

import os

import pytest

from resolve_storage import resolve_storage_kind


def test_explicit_env_gcs_wins_over_s3_when_both_set() -> None:
    kind = resolve_storage_kind(
        {
            "GCS_BUCKET": "gcs-bucket",
            "S3_BUCKET_NAME": "s3-bucket",
            "AWS_REGION": "ap-northeast-1",
        }
    )
    assert kind == "gcs"


def test_explicit_env_s3_when_only_s3() -> None:
    kind = resolve_storage_kind(
        {
            "S3_BUCKET_NAME": "s3-bucket",
            "AWS_REGION": "ap-northeast-1",
        }
    )
    assert kind == "s3"


def test_explicit_env_local_when_empty() -> None:
    kind = resolve_storage_kind({})
    assert kind == "local"


def test_forced_local() -> None:
    kind = resolve_storage_kind(
        {
            "STORAGE_BACKEND": "local",
            "GCS_BUCKET": "b",
        }
    )
    assert kind == "local"


def test_forced_gcs_without_bucket_falls_back_local() -> None:
    kind = resolve_storage_kind({"STORAGE_BACKEND": "gcs"})
    assert kind == "local"


def test_forced_s3_without_config_falls_back_local() -> None:
    kind = resolve_storage_kind({"STORAGE_BACKEND": "s3"})
    assert kind == "local"


def test_forced_s3_with_config() -> None:
    kind = resolve_storage_kind(
        {
            "STORAGE_BACKEND": "s3",
            "GCS_BUCKET": "g",
            "S3_BUCKET_NAME": "s",
            "AWS_REGION": "ap-northeast-1",
        }
    )
    assert kind == "s3"


def test_process_env_test_mode_returns_local(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MITENE_ENV", "test")
    monkeypatch.setenv("GCS_BUCKET", "should-be-ignored")
    assert resolve_storage_kind() == "local"


def test_process_env_pytest_returns_local(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MITENE_ENV", raising=False)
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "tests/test_foo.py::test_bar (call)")
    monkeypatch.setenv("GCS_BUCKET", "ignored")
    assert resolve_storage_kind() == "local"


def test_process_env_gcs_when_not_test(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MITENE_ENV", raising=False)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setenv("GCS_BUCKET", "my-bucket")
    # Avoid picking up real AWS env from developer machine
    monkeypatch.delenv("S3_BUCKET_NAME", raising=False)
    monkeypatch.delenv("AWS_REGION", raising=False)
    try:
        assert resolve_storage_kind() == "gcs"
    finally:
        pass


def test_s3_requires_region(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MITENE_ENV", raising=False)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.delenv("GCS_BUCKET", raising=False)
    monkeypatch.setenv("S3_BUCKET_NAME", "b")
    monkeypatch.delenv("AWS_REGION", raising=False)
    assert resolve_storage_kind() == "local"
