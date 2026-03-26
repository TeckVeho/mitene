"""
ファイルストレージ抽象化モジュール

S3_BUCKET_NAME 環境変数が設定されている場合は AWS S3 を使用し、
未設定の場合はローカルファイルシステムにフォールバックする（開発環境向け）。

S3 フォルダ構成:
  uploads/{job_id}/{filename}  - アップロードされたファイル
  outputs/{job_id}.mp4         - 生成済み MP4 ファイル
"""

import logging
import os
import subprocess
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

S3_BUCKET: Optional[str] = os.environ.get("S3_BUCKET_NAME")
AWS_REGION: str = os.environ.get("AWS_REGION", "ap-northeast-1")

_s3_client = None


def is_s3_enabled() -> bool:
    """S3 が有効かどうかを返す"""
    return bool(S3_BUCKET)


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


def upload_csv_to_s3(job_id: str, filename: str, content: bytes) -> Optional[str]:
    """
    ファイルを S3 にアップロードする。
    S3 が無効な場合は None を返す。
    """
    if not is_s3_enabled():
        return None

    key = f"uploads/{job_id}/{filename}"
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
    生成済み MP4 ファイルをローカルから S3 にアップロードする。
    アップロード後、ローカルの一時ファイルは削除する。
    S3 が無効な場合は None を返す。
    """
    if not is_s3_enabled():
        return None

    key = f"outputs/{job_id}.mp4"
    try:
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
        logger.error("MP4 S3 アップロード失敗: %s", exc)
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
    サムネイル JPEG をローカルから S3 にアップロードする。
    アップロード後、ローカルファイルは削除する。
    S3 が無効な場合は None を返す。
    """
    if not is_s3_enabled():
        return None

    key = f"outputs/{job_id}.jpg"
    try:
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
        logger.error("サムネイル S3 アップロード失敗: %s", exc)
        raise


def generate_mp4_download_url(job_id: str, expires_in: int = 3600) -> Optional[str]:
    """
    MP4 の S3 署名付きダウンロード URL を生成する（有効期限: デフォルト1時間）。
    S3 が無効な場合は None を返す。
    """
    if not is_s3_enabled():
        return None

    key = f"outputs/{job_id}.mp4"
    try:
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
    """
    MP4 のストリーミング用 S3 署名付き URL を生成する（有効期限: デフォルト24時間）。
    S3 が無効な場合は None を返す。
    """
    if not is_s3_enabled():
        return None

    key = f"outputs/{job_id}.mp4"
    try:
        url = _get_s3_client().generate_presigned_url(
            "get_object",
            Params={"Bucket": S3_BUCKET, "Key": key},
            ExpiresIn=expires_in,
        )
        return url
    except Exception as exc:
        logger.error("ストリーミング URL 生成失敗: %s", exc)
        return None


def generate_thumbnail_streaming_url(job_id: str, expires_in: int = 86400) -> Optional[str]:
    """
    サムネイル用 S3 署名付き URL を生成する（有効期限: デフォルト24時間）。
    S3 が無効な場合は None を返す。
    """
    if not is_s3_enabled():
        return None

    key = f"outputs/{job_id}.jpg"
    try:
        url = _get_s3_client().generate_presigned_url(
            "get_object",
            Params={"Bucket": S3_BUCKET, "Key": key},
            ExpiresIn=expires_in,
        )
        return url
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
    動画レコード削除時に、S3 およびローカルのジョブ成果物をベストエフォートで削除する。
    失敗しても例外は握りつぶす（DB は既に削除済みの想定）。
    """
    if is_s3_enabled():
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
