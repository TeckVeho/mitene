"""
ファイルストレージ抽象化モジュール

resolve_storage_kind に従い GCS / S3 / ローカルを使用する。
- GCS: GCS_BUCKET（Terraform が Cloud Run に注入する場合あり）
- S3: S3_BUCKET_NAME + AWS_REGION
- いずれも無い場合はローカルファイルシステム（開発用）

オブジェクトキー構成（GCS / S3 共通）:
  uploads/{job_id}/{filename}  - アップロードされたファイル
  outputs/{job_id}.mp4         - 生成済み MP4 ファイル
  outputs/{job_id}.jpg         - サムネイル
  （GCS かつ wiki モード）固定プレフィックス wiki-repo/ 配下の .md — gcs_list_object_keys_under_prefix / gcs_download_bytes / gcs_upload_bytes
"""

from __future__ import annotations

import logging
import os
import subprocess
from datetime import timedelta
from pathlib import Path
from typing import Optional

import google.auth
import google.auth.transport.requests
from google.oauth2 import service_account as oauth_service_account

from resolve_storage import resolve_storage_kind

logger = logging.getLogger(__name__)

S3_BUCKET: Optional[str] = os.environ.get("S3_BUCKET_NAME")
AWS_REGION: str = os.environ.get("AWS_REGION", "ap-northeast-1")
GCS_BUCKET: Optional[str] = os.environ.get("GCS_BUCKET", "").strip() or None

_s3_client = None
_gcs_client = None


def is_remote_object_storage_enabled() -> bool:
    """GCS または S3 でオブジェクトストレージを使う場合 True。"""
    return resolve_storage_kind() in ("gcs", "s3")


def is_s3_enabled() -> bool:
    """後方互換名: リモートオブジェクトストレージ（GCS 含む）が有効か。"""
    return is_remote_object_storage_enabled()


def _get_s3_client():
    """S3クライアントをシングルトンで返す（boto3 遅延インポート）"""
    global _s3_client
    if _s3_client is None:
        try:
            import boto3

            _s3_client = boto3.client("s3", region_name=AWS_REGION)
        except ImportError:
            raise RuntimeError(
                "boto3 がインストールされていません。"
                "pip install 'boto3>=1.35.0' を実行してください。"
            )
    return _s3_client


def _get_gcs_client():
    global _gcs_client
    if _gcs_client is None:
        try:
            from google.cloud import storage
        except ImportError:
            raise RuntimeError(
                "google-cloud-storage がインストールされていません。"
                "pip install 'google-cloud-storage>=2.14.0' を実行してください。"
            )
        project = os.environ.get("GCP_PROJECT_ID", "").strip() or None
        _gcs_client = storage.Client(project=project)
    return _gcs_client


def _gcs_bucket():
    if not GCS_BUCKET:
        raise RuntimeError("GCS_BUCKET is not set")
    return _get_gcs_client().bucket(GCS_BUCKET)


def gcs_list_object_keys_under_prefix(prefix: str) -> list[str]:
    """
    GCS_BUCKET 内で prefix で始まるオブジェクトキーを列挙する（再帰的）。
    resolve_storage_kind() が gcs のとき、かつ GCS_BUCKET が設定されているときに使用する。
    """
    if not prefix:
        raise ValueError("prefix must be non-empty")
    bucket = _gcs_bucket()
    return sorted({blob.name for blob in bucket.list_blobs(prefix=prefix)})


def gcs_download_bytes(object_key: str) -> bytes:
    """GCS_BUCKET の object_key をバイト列で取得する。"""
    blob = _gcs_bucket().blob(object_key)
    return blob.download_as_bytes()


def gcs_upload_bytes(object_key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
    """GCS_BUCKET に object_key でバイト列を書き込む（wiki .md 同期など）。"""
    blob = _gcs_bucket().blob(object_key)
    blob.upload_from_string(data, content_type=content_type)


def _gcs_signed_url(key: str, expires_in: int) -> str:
    """
    Cloud Run / GCE では ADC に秘密鍵が無く generate_signed_url が失敗することがある。
    service_account_email + access_token を渡すと IAM SignBlob で署名される。
    ローカルのサービスアカウント JSON（oauth_service_account.Credentials）は従来どおりローカル署名。
    """
    blob = _gcs_bucket().blob(key)
    url_kwargs = dict(
        version="v4",
        expiration=timedelta(seconds=expires_in),
        method="GET",
    )

    creds, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
    req = google.auth.transport.requests.Request()
    creds.refresh(req)

    if isinstance(creds, oauth_service_account.Credentials):
        return blob.generate_signed_url(**url_kwargs)

    sa_email = getattr(creds, "service_account_email", None)
    access_token = getattr(creds, "token", None)
    if sa_email and access_token:
        return blob.generate_signed_url(
            **url_kwargs,
            service_account_email=sa_email,
            access_token=access_token,
        )

    return blob.generate_signed_url(**url_kwargs)


def save_file_locally(uploads_dir: Path, job_id: str, filename: str, content: bytes) -> Path:
    """
    ファイルをローカルに保存する。
    notebooklm-py がローカルパスを必要とするためローカル保存は必須。
    """
    local_path = uploads_dir / f"{job_id}_{filename}"
    local_path.write_bytes(content)
    return local_path


def save_csv_locally(uploads_dir: Path, job_id: str, filename: str, content: bytes) -> Path:
    """後方互換のためのエイリアス"""
    return save_file_locally(uploads_dir, job_id, filename, content)


def restore_source_file_locally(uploads_dir: Path, job_id: str, filename: str) -> Optional[Path]:
    """
    Restore an uploaded source file from remote object storage into ``uploads_dir``.

    Returns the local path on success, or ``None`` when the active storage backend is local
    or the remote object does not exist.
    """
    kind = resolve_storage_kind()
    if kind == "local":
        return None

    local_path = uploads_dir / f"{job_id}_{filename}"
    key = f"uploads/{job_id}/{filename}"

    try:
        if kind == "gcs":
            blob = _gcs_bucket().blob(key)
            if not blob.exists():
                logger.warning(
                    "source restore miss job_id=%s backend=gcs key=gs://%s/%s",
                    job_id,
                    GCS_BUCKET,
                    key,
                )
                return None
            local_path.write_bytes(blob.download_as_bytes())
            logger.info(
                "source restore success job_id=%s backend=gcs key=gs://%s/%s local_path=%s",
                job_id,
                GCS_BUCKET,
                key,
                local_path,
            )
            return local_path

        if not S3_BUCKET:
            raise RuntimeError("S3_BUCKET_NAME is not set")

        try:
            _get_s3_client().head_object(Bucket=S3_BUCKET, Key=key)
        except Exception:
            logger.warning(
                "source restore miss job_id=%s backend=s3 key=s3://%s/%s",
                job_id,
                S3_BUCKET,
                key,
            )
            return None

        body = _get_s3_client().get_object(Bucket=S3_BUCKET, Key=key)["Body"].read()
        local_path.write_bytes(body)
        logger.info(
            "source restore success job_id=%s backend=s3 key=s3://%s/%s local_path=%s",
            job_id,
            S3_BUCKET,
            key,
            local_path,
        )
        return local_path
    except Exception as exc:
        logger.exception(
            "source restore failed job_id=%s backend=%s key=%s error=%s",
            job_id,
            kind,
            key,
            exc,
        )
        raise


def upload_csv_to_s3(job_id: str, filename: str, content: bytes) -> Optional[str]:
    """
    ファイルを GCS または S3 にアップロードする。
    ローカルモードの場合は None を返す。
    """
    kind = resolve_storage_kind()
    if kind == "local":
        return None

    key = f"uploads/{job_id}/{filename}"
    if kind == "gcs":
        try:
            blob = _gcs_bucket().blob(key)
            blob.upload_from_string(content, content_type="text/plain")
            logger.info("ファイルを GCS にアップロード: gs://%s/%s", GCS_BUCKET, key)
            return key
        except Exception as exc:
            logger.warning("GCS アップロード失敗（ローカル保存は継続）: %s", exc)
            return None

    try:
        _get_s3_client().put_object(
            Bucket=S3_BUCKET,
            Key=key,
            Body=content,
            ContentType="text/plain",
        )
        logger.info("ファイルを S3 にアップロード: s3://%s/%s", S3_BUCKET, key)
        return key
    except Exception as exc:
        logger.warning("S3 アップロード失敗（ローカル保存は継続）: %s", exc)
        return None


def upload_mp4_to_s3(job_id: str, local_path: Path) -> Optional[str]:
    """
    生成済み MP4 を GCS または S3 にアップロードする。
    アップロード後、ローカルの一時ファイルは削除する。
    """
    kind = resolve_storage_kind()
    if kind == "local":
        return None

    key = f"outputs/{job_id}.mp4"
    try:
        if kind == "gcs":
            blob = _gcs_bucket().blob(key)
            blob.upload_from_filename(str(local_path), content_type="video/mp4")
            logger.info("MP4 を GCS にアップロード: gs://%s/%s", GCS_BUCKET, key)
        else:
            with open(local_path, "rb") as f:
                _get_s3_client().upload_fileobj(
                    f,
                    S3_BUCKET,
                    key,
                    ExtraArgs={"ContentType": "video/mp4"},
                )
            logger.info("MP4 を S3 にアップロード: s3://%s/%s", S3_BUCKET, key)

        try:
            local_path.unlink(missing_ok=True)
            logger.debug("ローカル MP4 一時ファイルを削除: %s", local_path)
        except Exception as e:
            logger.warning("ローカル MP4 削除失敗（無視）: %s", e)

        return key
    except Exception as exc:
        logger.error("MP4 アップロード失敗: %s", exc)
        raise


def _probe_video_duration_seconds(local_path: Path) -> Optional[float]:
    """MP4 の秒数を ffprobe で取得する。"""
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(local_path),
    ]
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        duration_raw = result.stdout.strip()
        if not duration_raw:
            return None
        duration = float(duration_raw)
        if duration <= 0:
            return None
        return duration
    except Exception as exc:
        logger.warning("ffprobe で duration 取得失敗: %s", exc)
        return None


def _thumbnail_seek_seconds(duration_sec: Optional[float]) -> float:
    """サムネイル抽出の seek 秒数を計算する。"""
    if duration_sec is None:
        return 5.0
    if duration_sec <= 5:
        return max(0.5, duration_sec / 2.0)
    return min(max(duration_sec * 0.3, 3.0), duration_sec - 2.0)


def extract_thumbnail_locally(job_id: str, mp4_path: Path) -> Path:
    """
    MP4 から JPEG サムネイルを抽出する。
    成功時はローカル JPEG のパスを返す。
    """
    duration_sec = _probe_video_duration_seconds(mp4_path)
    seek_sec = _thumbnail_seek_seconds(duration_sec)
    thumbnails_dir = mp4_path.parent / "thumbnails"
    thumbnails_dir.mkdir(parents=True, exist_ok=True)
    thumbnail_path = thumbnails_dir / f"{job_id}.jpg"

    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-ss",
        f"{seek_sec:.3f}",
        "-i",
        str(mp4_path),
        "-frames:v",
        "1",
        "-q:v",
        "2",
        str(thumbnail_path),
    ]

    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        logger.info(
            "サムネイル抽出成功: job_id=%s seek=%.3fs path=%s",
            job_id,
            seek_sec,
            thumbnail_path,
        )
        return thumbnail_path
    except Exception as exc:
        thumbnail_path.unlink(missing_ok=True)
        logger.error("サムネイル抽出失敗: job_id=%s err=%s", job_id, exc)
        raise


def upload_thumbnail_to_s3(job_id: str, local_jpg: Path) -> Optional[str]:
    """
    サムネイル JPEG を GCS または S3 にアップロードする。
    アップロード後、ローカルファイルは削除する。
    """
    kind = resolve_storage_kind()
    if kind == "local":
        return None

    key = f"outputs/{job_id}.jpg"
    try:
        if kind == "gcs":
            blob = _gcs_bucket().blob(key)
            blob.upload_from_filename(str(local_jpg), content_type="image/jpeg")
            logger.info("サムネイルを GCS にアップロード: gs://%s/%s", GCS_BUCKET, key)
        else:
            with open(local_jpg, "rb") as f:
                _get_s3_client().upload_fileobj(
                    f,
                    S3_BUCKET,
                    key,
                    ExtraArgs={"ContentType": "image/jpeg"},
                )
            logger.info("サムネイルを S3 にアップロード: s3://%s/%s", S3_BUCKET, key)

        try:
            local_jpg.unlink(missing_ok=True)
            logger.debug("ローカルサムネイル一時ファイルを削除: %s", local_jpg)
        except Exception as e:
            logger.warning("ローカルサムネイル削除失敗（無視）: %s", e)

        return key
    except Exception as exc:
        logger.error("サムネイル アップロード失敗: %s", exc)
        raise


def generate_mp4_download_url(job_id: str, expires_in: int = 3600) -> Optional[str]:
    """MP4 の署名付きダウンロード URL（GCS V4 または S3）。"""
    kind = resolve_storage_kind()
    if kind == "local":
        return None

    key = f"outputs/{job_id}.mp4"
    try:
        if kind == "gcs":
            url = _gcs_signed_url(key, expires_in)
        else:
            url = _get_s3_client().generate_presigned_url(
                "get_object",
                Params={"Bucket": S3_BUCKET, "Key": key},
                ExpiresIn=expires_in,
            )
        logger.debug("MP4 署名付き URL を生成: %s", url[:80])
        return url
    except Exception as exc:
        logger.error("署名付き URL 生成失敗: %s", exc)
        return None


def generate_mp4_streaming_url(job_id: str, expires_in: int = 86400) -> Optional[str]:
    """MP4 ストリーミング用署名付き URL。"""
    kind = resolve_storage_kind()
    if kind == "local":
        return None

    key = f"outputs/{job_id}.mp4"
    try:
        if kind == "gcs":
            return _gcs_signed_url(key, expires_in)
        return _get_s3_client().generate_presigned_url(
            "get_object",
            Params={"Bucket": S3_BUCKET, "Key": key},
            ExpiresIn=expires_in,
        )
    except Exception as exc:
        logger.error("ストリーミング URL 生成失敗: %s", exc)
        return None


def generate_thumbnail_streaming_url(job_id: str, expires_in: int = 86400) -> Optional[str]:
    """サムネイル用署名付き URL。"""
    kind = resolve_storage_kind()
    if kind == "local":
        return None

    key = f"outputs/{job_id}.jpg"
    try:
        if kind == "gcs":
            return _gcs_signed_url(key, expires_in)
        return _get_s3_client().generate_presigned_url(
            "get_object",
            Params={"Bucket": S3_BUCKET, "Key": key},
            ExpiresIn=expires_in,
        )
    except Exception as exc:
        logger.error("サムネイル URL 生成失敗: %s", exc)
        return None


def cleanup_local_csv(csv_paths: list[Path]) -> None:
    """ジョブ完了後、ローカルの一時ファイルを削除する"""
    for path in csv_paths:
        try:
            path.unlink(missing_ok=True)
            logger.debug("ローカル一時ファイルを削除: %s", path)
        except Exception as e:
            logger.warning("ローカルファイル削除失敗（無視）: %s", e)


def delete_job_outputs(
    job_id: str,
    outputs_dir: Optional[Path] = None,
    uploads_dir: Optional[Path] = None,
) -> None:
    """
    動画レコード削除時に、GCS / S3 およびローカルのジョブ成果物をベストエフォートで削除する。
    """
    kind = resolve_storage_kind()
    if kind == "gcs":
        from google.cloud.exceptions import NotFound

        prefix = f"uploads/{job_id}/"
        keys = [f"outputs/{job_id}.mp4", f"outputs/{job_id}.jpg"]
        try:
            bucket = _gcs_bucket()
            for key in keys:
                try:
                    bucket.blob(key).delete()
                except NotFound:
                    pass
                except Exception as exc:
                    logger.warning("GCS オブジェクト削除失敗（無視） key=%s: %s", key, exc)
            for blob in bucket.list_blobs(prefix=prefix):
                try:
                    blob.delete()
                except Exception as exc:
                    logger.warning("GCS 削除失敗（無視） %s: %s", blob.name, exc)
            logger.debug("GCS ジョブ出力削除 job_id=%s", job_id)
        except Exception as exc:
            logger.warning("GCS ジョブ出力削除失敗（無視） job_id=%s: %s", job_id, exc)

    elif kind == "s3":
        keys = [f"outputs/{job_id}.mp4", f"outputs/{job_id}.jpg"]
        prefix = f"uploads/{job_id}/"
        try:
            client = _get_s3_client()
            for key in keys:
                try:
                    client.delete_object(Bucket=S3_BUCKET, Key=key)
                    logger.debug("S3 削除: s3://%s/%s", S3_BUCKET, key)
                except Exception as exc:
                    logger.warning("S3 オブジェクト削除失敗（無視） key=%s: %s", key, exc)
            paginator = client.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=S3_BUCKET, Prefix=prefix):
                objs = page.get("Contents") or []
                if not objs:
                    continue
                client.delete_objects(
                    Bucket=S3_BUCKET,
                    Delete={"Objects": [{"Key": o["Key"]} for o in objs]},
                )
                logger.debug("S3 一括削除: %s 件 prefix=%s", len(objs), prefix)
        except Exception as exc:
            logger.warning("S3 ジョブ出力削除失敗（無視） job_id=%s: %s", job_id, exc)

    if outputs_dir is not None:
        mp4 = outputs_dir / f"{job_id}.mp4"
        thumb = outputs_dir / "thumbnails" / f"{job_id}.jpg"
        for path in (mp4, thumb):
            try:
                path.unlink(missing_ok=True)
                logger.debug("ローカル出力削除: %s", path)
            except Exception as exc:
                logger.warning("ローカルファイル削除失敗（無視） %s: %s", path, exc)

    if uploads_dir is not None:
        try:
            for path in uploads_dir.glob(f"{job_id}_*"):
                try:
                    path.unlink(missing_ok=True)
                    logger.debug("ローカルアップロード削除: %s", path)
                except Exception as exc:
                    logger.warning("ローカルアップロード削除失敗（無視） %s: %s", path, exc)
        except Exception as exc:
            logger.warning("ローカルアップロード glob 失敗（無視） job_id=%s: %s", job_id, exc)
