"""
ファイルストレージ抽象化モジュール

S3_BUCKET_NAME 環境変数が設定されている場合は AWS S3 を使用し、
未設定の場合はローカルファイルシステムにフォールバックする（開発環境向け）。

S3 フォルダ構成:
  uploads/{job_id}/{filename}  - アップロードされた CSV ファイル
  outputs/{job_id}.mp4         - 生成済み MP4 ファイル
  outputs/{job_id}.wav         - 生成済み WAV ファイル（音声ジョブ）
"""

import logging
import os
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


def save_csv_locally(uploads_dir: Path, job_id: str, filename: str, content: bytes) -> Path:
    """
    CSV ファイルをローカルに保存する。
    S3 が有効な場合も notebooklm-py がローカルパスを必要とするためローカル保存は必須。
    """
    local_path = uploads_dir / f"{job_id}_{filename}"
    local_path.write_bytes(content)
    return local_path


def upload_csv_to_s3(job_id: str, filename: str, content: bytes) -> Optional[str]:
    """
    CSV ファイルを S3 にアップロードする。
    S3 が無効な場合は None を返す。

    Returns:
        S3 キー文字列（例: "uploads/job_abc123/data.csv"）、または None
    """
    if not is_s3_enabled():
        return None

    key = f"uploads/{job_id}/{filename}"
    try:
        _get_s3_client().put_object(
            Bucket=S3_BUCKET,
            Key=key,
            Body=content,
            ContentType="text/csv",
        )
        logger.info("CSV を S3 にアップロード: s3://%s/%s", S3_BUCKET, key)
        return key
    except Exception as exc:
        logger.warning("CSV S3 アップロード失敗（ローカル保存は継続）: %s", exc)
        return None


def upload_mp4_to_s3(job_id: str, local_path: Path) -> Optional[str]:
    """
    生成済み MP4 ファイルをローカルから S3 にアップロードする。
    アップロード後、ローカルの一時ファイルは削除する。
    S3 が無効な場合は None を返す。

    Returns:
        S3 キー文字列（例: "outputs/job_abc123.mp4"）、または None
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

        # S3 アップロード成功後にローカル一時ファイルを削除
        try:
            local_path.unlink(missing_ok=True)
            logger.debug("ローカル MP4 一時ファイルを削除: %s", local_path)
        except Exception as e:
            logger.warning("ローカル MP4 削除失敗（無視）: %s", e)

        return key
    except Exception as exc:
        logger.error("MP4 S3 アップロード失敗: %s", exc)
        raise


def generate_mp4_download_url(job_id: str, expires_in: int = 3600) -> Optional[str]:
    """
    MP4 の S3 署名付きダウンロード URL を生成する（有効期限: デフォルト1時間）。
    S3 が無効な場合は None を返す。

    Returns:
        署名付き URL 文字列、または None
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


def upload_audio_to_s3(job_id: str, local_path: Path) -> Optional[str]:
    """
    生成済み WAV ファイルをローカルから S3 にアップロードする。
    アップロード後、ローカルの一時ファイルは削除する。
    S3 が無効な場合は None を返す。

    Returns:
        S3 キー文字列（例: "outputs/job_abc123.wav"）、または None
    """
    if not is_s3_enabled():
        return None

    suffix = local_path.suffix or ".wav"
    key = f"outputs/{job_id}{suffix}"
    content_type = "audio/wav" if suffix == ".wav" else "audio/mpeg"
    try:
        with open(local_path, "rb") as f:
            _get_s3_client().upload_fileobj(
                f,
                S3_BUCKET,
                key,
                ExtraArgs={"ContentType": content_type},
            )
        logger.info("音声ファイルを S3 にアップロード: s3://%s/%s", S3_BUCKET, key)

        try:
            local_path.unlink(missing_ok=True)
            logger.debug("ローカル音声一時ファイルを削除: %s", local_path)
        except Exception as e:
            logger.warning("ローカル音声削除失敗（無視）: %s", e)

        return key
    except Exception as exc:
        logger.error("音声ファイル S3 アップロード失敗: %s", exc)
        raise


def generate_audio_download_url(job_id: str, suffix: str = ".wav", expires_in: int = 3600) -> Optional[str]:
    """
    音声ファイルの S3 署名付きダウンロード URL を生成する（有効期限: デフォルト1時間）。
    S3 が無効な場合は None を返す。

    Returns:
        署名付き URL 文字列、または None
    """
    if not is_s3_enabled():
        return None

    key = f"outputs/{job_id}{suffix}"
    try:
        url = _get_s3_client().generate_presigned_url(
            "get_object",
            Params={"Bucket": S3_BUCKET, "Key": key},
            ExpiresIn=expires_in,
        )
        logger.debug("音声署名付き URL を生成: %s", url[:80])
        return url
    except Exception as exc:
        logger.error("音声署名付き URL 生成失敗: %s", exc)
        return None


def download_audio_from_s3(job_id: str, suffix: str = ".wav") -> Optional[bytes]:
    """
    S3 から音声ファイルのバイト列をダウンロードして返す。
    S3 が無効な場合や失敗した場合は None を返す。

    Returns:
        音声ファイルのバイト列、または None
    """
    if not is_s3_enabled():
        return None

    key = f"outputs/{job_id}{suffix}"
    try:
        obj = _get_s3_client().get_object(Bucket=S3_BUCKET, Key=key)
        body = obj.get("Body")
        if body is None:
            logger.error("音声ファイルオブジェクトの Body が空です: s3://%s/%s", S3_BUCKET, key)
            return None
        data = body.read()
        logger.debug("音声ファイルを S3 からダウンロード: s3://%s/%s (size=%d)", S3_BUCKET, key, len(data))
        return data
    except Exception as exc:
        logger.error("音声ファイル S3 ダウンロード失敗: %s", exc)
        return None


def cleanup_local_csv(csv_paths: list[Path]) -> None:
    """ジョブ完了後、ローカルの一時 CSV ファイルを削除する"""
    for path in csv_paths:
        try:
            path.unlink(missing_ok=True)
            logger.debug("ローカル CSV 一時ファイルを削除: %s", path)
        except Exception as e:
            logger.warning("ローカル CSV 削除失敗（無視）: %s", e)
