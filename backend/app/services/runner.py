"""
バックグラウンドジョブランナー
.md（Markdown）または CSV ファイルを NotebookLM に送り動画を生成する。

S3_BUCKET_NAME 環境変数が設定されている場合、MP4 生成後に S3 へアップロードし、
ローカルの一時ファイルを削除する。

ジョブ完了後:
  - videos テーブルを更新
  - Slack 通知を送信
"""

import asyncio
import logging
import os
import time
import traceback
from pathlib import Path
from typing import Callable, Awaitable, Optional
from urllib.parse import urljoin

import storage as storage_mod
from app.config import STORAGE_STATE
from app.services.notebooklm_gcs import download_storage_state_if_configured
from webhook import send_webhook

logger = logging.getLogger(__name__)


STEP_IDS = [
    "create_notebook",
    "add_source",
    "generate_video",
    "wait_completion",
    "download_ready",
]

# Clamp job `timeout` for download / MP4 upload phases (no env vars).
_DOWNLOAD_OR_UPLOAD_TIMEOUT_MIN_SEC = 600
_DOWNLOAD_OR_UPLOAD_TIMEOUT_MAX_SEC = 7200


def _effective_phase_timeout_sec(job_timeout: int) -> int:
    return max(
        _DOWNLOAD_OR_UPLOAD_TIMEOUT_MIN_SEC,
        min(_DOWNLOAD_OR_UPLOAD_TIMEOUT_MAX_SEC, job_timeout),
    )


StoreUpdateFn = Callable[..., Awaitable[dict]]


def _is_notebooklm_auth_error(exc: Exception) -> bool:
    raw = f"{type(exc).__name__}: {exc}".lower()
    return any(
        token in raw
        for token in (
            "authentication expired or invalid",
            "redirected to: https://accounts.google.com",
            "servicelogin",
            "accounts.google.com",
        )
    )


async def _set_step_status(
    store_update: StoreUpdateFn,
    job_id: str,
    current_steps: list[dict],
    step_id: str,
    step_status: str,
    message: str | None = None,
) -> list[dict]:
    """指定ステップのステータスを更新し、新しい steps リストを返す。"""
    updated = []
    for s in current_steps:
        if s["id"] == step_id:
            s = {**s, "status": step_status}
            if message is not None:
                s["message"] = message
        updated.append(s)
    await store_update(job_id, steps=updated, currentStep=step_id)
    return updated


async def _fail_job(
    store_update: StoreUpdateFn,
    job_id: str,
    steps: list[dict],
    failed_step: str,
    error_message: str,
) -> None:
    steps = await _set_step_status(store_update, job_id, steps, failed_step, "error", error_message)
    await store_update(
        job_id,
        status="error",
        steps=steps,
        errorMessage=error_message,
    )
    await _mark_video_failed_for_job(job_id)


async def _wait_for_source_ready(
    client,
    nb_id: str,
    source_id: str,
    name: str,
    max_wait: int = 300,
) -> bool:
    """SourceStatus.READY (=2) になるまでポーリング。タイムアウト時 False を返す。"""
    poll_interval = 5
    elapsed = 0
    while elapsed < max_wait:
        src = await client.sources.get(nb_id, source_id)
        if hasattr(src, "status") and src.status == 2:
            return True
        await asyncio.sleep(poll_interval)
        elapsed += poll_interval
    return False


async def _wait_for_video_with_media_check(
    client,
    notebook_id: str,
    task_id: str,
    timeout: int,
    media_ready_timeout: int = 120,
    poll_interval: int = 10,
):
    """ライブラリのバグを回避し、正確に動画生成の完了を待機するラッパー。

    notebooklm-py の `_is_media_ready()` には動画URLの判定バグがあり、URLが存在しても
    Falseを返してしまう（結果として永続的に PROCESSING にダウングレードされてしまう）。
    そのため、この関数の内部で直接APIの生データ (_list_raw) を参照し、
    正しい構造で動画URLの有無を確認する。
    """
    from notebooklm.types import GenerationStatus
    from notebooklm.rpc import artifact_status_to_str
    
    loop = asyncio.get_event_loop()
    start = loop.time()
    
    # 完全にスタックした場合のエラー判定用
    stuck_since: float | None = None
    last_stuck_status: str | None = None

    while True:
        elapsed = loop.time() - start
        if elapsed > timeout:
            raise TimeoutError(f"Task {task_id} timed out after {timeout}s")

        # 1. ライブラリ関数を使わず、直接アーティファクトのリストを取得
        artifacts_data = await client.artifacts._list_raw(notebook_id)
        
        target_art = None
        for art in artifacts_data:
            if isinstance(art, list) and len(art) > 0 and art[0] == task_id:
                target_art = art
                break
                
        # 2. アーティファクトの状態判定
        if not target_art:
            current_status = "pending"
            has_media = False
        else:
            status_code = target_art[4] if len(target_art) > 4 else 0
            current_status = artifact_status_to_str(status_code)
            
            # download_video() と同じ確実なロジックでメディアURLの存在をチェック
            has_media = False
            if len(target_art) > 8 and isinstance(target_art[8], list):
                for item in target_art[8]:
                    if (
                        isinstance(item, list)
                        and len(item) > 0
                        and isinstance(item[0], list)
                        and len(item[0]) > 0
                        and isinstance(item[0][0], str)
                        and item[0][0].startswith("http")
                    ):
                        has_media = True
                        break

        logger.debug(
            "poll_status bypass task_id=%s status=%s has_media=%s",
            task_id, current_status, has_media
        )

        if current_status == "completed" and has_media:
            return GenerationStatus(task_id=task_id, status="completed")
            
        if current_status in ("failed", "error"):
            # 何らかの理由で生成自体が失敗
            return GenerationStatus(task_id=task_id, status=current_status)

        # 3. 停滞パターンの検知
        # - "completed" だがURLがいつまでも取得できない
        # （注意: "pending" は単に生成完了を待っている正常な状態なので、全体の timeout で管理する）
        if current_status == "completed" and not has_media:
            if stuck_since is None:
                stuck_since = loop.time()
                last_stuck_status = "completed_no_media"
                logger.info(
                    "Task %s: status=%s detected, starting stuck timer",
                    task_id, last_stuck_status,
                )
            elif (loop.time() - stuck_since) > media_ready_timeout:
                error_detail = (
                    f"動画生成は完了しましたが、メディアURLが"
                    f"{media_ready_timeout}秒経過しても取得できませんでした。"
                    f"サーバー側で生成に失敗した可能性があります。再試行してください。"
                )
                logger.error(
                    "Task %s: stuck in '%s' for %ds. %s",
                    task_id, last_stuck_status, media_ready_timeout, error_detail,
                )
                raise TimeoutError(f"Task {task_id}: {error_detail}")
        else:
            # 正常に processing や pending の場合はタイマーをリセット
            if stuck_since is not None:
                logger.info("Task %s: status changed to '%s', resetting stuck timer", task_id, current_status)
            stuck_since = None
            last_stuck_status = None

        await asyncio.sleep(poll_interval)


async def run_job(
    *,
    job_id: str,
    source_paths: Optional[list[Path]] = None,
    csv_paths: Optional[list[Path]] = None,  # 後方互換
    output_path: Path,
    notebook_title: str,
    instructions: str,
    style: str,
    video_format: str,
    language: str,
    timeout: int,
    store_update: StoreUpdateFn,
    callback_url: Optional[str] = None,
    semaphore: asyncio.Semaphore | None = None,
) -> None:
    """
    ジョブを非同期バックグラウンドで実行する。
    source_paths には .md または .csv ファイルのパスを渡す。

    ステップ:
      1. ノートブック作成
      2. ドキュメントソース追加
      3. 動画生成開始
      4. 生成完了待機
      5. MP4 ダウンロード（→ S3 が有効な場合は S3 にアップロード）
      6. videos テーブル更新 + Slack 通知
    """
    # 後方互換: csv_paths が渡された場合は source_paths として扱う
    if source_paths is None:
        source_paths = csv_paths or []
    logger.info(
        "run_job started job_id=%s source_count=%d language=%s style=%s format=%s timeout=%s output_path=%s",
        job_id,
        len(source_paths),
        language,
        style,
        video_format,
        timeout,
        output_path,
    )

    if semaphore is not None:
        await semaphore.acquire()

    try:
        from notebooklm import NotebookLMClient, VideoFormat, VideoStyle
    except ImportError:
        await store_update(
            job_id,
            status="error",
            errorMessage=(
                "notebooklm-py がインストールされていません。"
                "pip install 'notebooklm-py[browser]' を実行してください。"
            ),
        )
        await _mark_video_failed_for_job(job_id)
        if semaphore is not None:
            semaphore.release()
        return

    style_map: dict[str, VideoStyle] = {
        "auto": VideoStyle.AUTO_SELECT,
        "classic": VideoStyle.CLASSIC,
        "whiteboard": VideoStyle.WHITEBOARD,
        "kawaii": VideoStyle.KAWAII,
        "anime": VideoStyle.ANIME,
        "watercolor": VideoStyle.WATERCOLOR,
        "retro-print": VideoStyle.RETRO_PRINT,
        "heritage": VideoStyle.HERITAGE,
        "paper-craft": VideoStyle.PAPER_CRAFT,
    }
    format_map: dict[str, VideoFormat] = {
        "explainer": VideoFormat.EXPLAINER,
        "brief": VideoFormat.BRIEF,
    }

    video_style = style_map.get(style, VideoStyle.WHITEBOARD)
    video_fmt = format_map.get(video_format, VideoFormat.EXPLAINER)

    job = await store_update(job_id, status="processing")
    steps: list[dict] = job["steps"]
    thumbnail_generated = False

    try:
        download_storage_state_if_configured()

        async with await NotebookLMClient.from_storage(str(STORAGE_STATE)) as client:

            # ── Step 1: ノートブック作成 ──────────────────────────────
            logger.info("run_job step start job_id=%s step=create_notebook", job_id)
            steps = await _set_step_status(
                store_update, job_id, steps, "create_notebook", "in_progress"
            )
            nb = await client.notebooks.create(notebook_title)
            logger.info(
                "run_job step success job_id=%s step=create_notebook notebook_id=%s title=%s",
                job_id,
                nb.id,
                notebook_title,
            )
            steps = await _set_step_status(
                store_update, job_id, steps, "create_notebook", "completed"
            )

            # ── Step 2: ソース追加 ────────────────────────────────────
            logger.info(
                "run_job step start job_id=%s step=add_source total_sources=%d",
                job_id,
                len(source_paths),
            )
            total = len(source_paths)
            for idx, source_path in enumerate(source_paths, start=1):
                progress = f"({idx}/{total})" if total > 1 else ""
                ext = source_path.suffix.lower()
                file_type = "Markdown" if ext == ".md" else "CSV"
                logger.info(
                    "run_job add_source uploading job_id=%s source=%s index=%d/%d type=%s",
                    job_id,
                    source_path,
                    idx,
                    total,
                    file_type,
                )
                steps = await _set_step_status(
                    store_update, job_id, steps, "add_source", "in_progress",
                    message=f"{file_type}ファイルをアップロード中... {progress}"
                )
                source = await client.sources.add_file(nb.id, source_path)
                logger.debug(
                    "run_job add_source uploaded job_id=%s source_id=%s source=%s",
                    job_id,
                    source.id,
                    source_path,
                )

                steps = await _set_step_status(
                    store_update, job_id, steps, "add_source", "in_progress",
                    message=f"ソースのインデックスを作成中... {progress}"
                )
                ready = await _wait_for_source_ready(
                    client, nb.id, source.id, source_path.name
                )
                if not ready:
                    logger.error(
                        "run_job add_source timeout job_id=%s source_id=%s source=%s",
                        job_id,
                        source.id,
                        source_path.name,
                    )
                    error_msg = (
                        f"{source_path.name} のインデックス作成がタイムアウトしました。"
                        "ファイルのサイズを確認してください。"
                    )
                    await _fail_job(store_update, job_id, steps, "add_source", error_msg)
                    if callback_url:
                        await send_webhook(
                            callback_url,
                            {"event": "job.error", "job_id": job_id, "status": "error", "error_message": error_msg},
                        )
                    return
                logger.info(
                    "run_job add_source ready job_id=%s source_id=%s source=%s",
                    job_id,
                    source.id,
                    source_path.name,
                )

            steps = await _set_step_status(
                store_update, job_id, steps, "add_source", "completed"
            )
            logger.info("run_job step success job_id=%s step=add_source", job_id)

            # ── Step 3: 解説動画を生成 ────────────────────────────────
            logger.info("run_job step start job_id=%s step=generate_video", job_id)
            steps = await _set_step_status(
                store_update, job_id, steps, "generate_video", "in_progress",
                message=f"動画生成を開始中... (指示: {instructions[:30]}{'...' if len(instructions) > 30 else ''})"
            )
            gen_status = await client.artifacts.generate_video(
                nb.id,
                instructions=instructions,
                video_format=video_fmt,
                video_style=video_style,
                language=language,
            )
            logger.info(
                "run_job step success job_id=%s step=generate_video task_id=%s",
                job_id,
                gen_status.task_id,
            )
            steps = await _set_step_status(
                store_update, job_id, steps, "generate_video", "completed"
            )

            # ── Step 4: 生成完了まで待機 ──────────────────────────────
            logger.info(
                "run_job step start job_id=%s step=wait_completion task_id=%s timeout=%s",
                job_id,
                gen_status.task_id,
                timeout,
            )
            steps = await _set_step_status(
                store_update, job_id, steps, "wait_completion", "in_progress",
                message=f"動画を生成中... (最大 {timeout // 60} 分)"
            )
            final = await _wait_for_video_with_media_check(
                client,
                nb.id,
                gen_status.task_id,
                timeout=timeout,
            )

            if not final.is_complete:
                logger.error(
                    "run_job step failed job_id=%s step=wait_completion final_status=%s",
                    job_id,
                    final.status,
                )
                error_msg = f"動画生成がタイムアウトまたは失敗しました。(ステータス: {final.status})"
                await _fail_job(store_update, job_id, steps, "wait_completion", error_msg)
                if callback_url:
                    await send_webhook(
                        callback_url,
                        {"event": "job.error", "job_id": job_id, "status": "error", "error_message": error_msg},
                    )
                return

            steps = await _set_step_status(
                store_update, job_id, steps, "wait_completion", "completed"
            )
            logger.info(
                "run_job step success job_id=%s step=wait_completion final_status=%s",
                job_id,
                final.status,
            )

            # ── Step 5: MP4 ダウンロード ──────────────────────────────
            logger.info(
                "run_job step start job_id=%s step=download_ready output_path=%s",
                job_id,
                output_path,
            )
            steps = await _set_step_status(
                store_update, job_id, steps, "download_ready", "in_progress",
                message="MP4ファイルをダウンロード中..."
            )
            # notebooklm-py reads storage_state.json from disk again for MP4 download; refresh
            # from GCS when sync is enabled so the file exists after cold start or rare races.
            logger.info(
                "run_job refresh NotebookLM storage from GCS before download_video job_id=%s path=%s",
                job_id,
                STORAGE_STATE,
            )
            t_sync_start = time.monotonic()
            download_storage_state_if_configured()
            sync_elapsed = time.monotonic() - t_sync_start
            logger.info(
                "run_job storage sync before download done job_id=%s elapsed_sec=%.3f",
                job_id,
                sync_elapsed,
            )

            effective_download_timeout = _effective_phase_timeout_sec(timeout)
            logger.info(
                "run_job download_video start job_id=%s notebook_id=%s output_path=%s timeout_sec=%s",
                job_id,
                nb.id,
                output_path,
                effective_download_timeout,
            )
            t_dl_start = time.monotonic()
            try:
                await asyncio.wait_for(
                    client.artifacts.download_video(nb.id, str(output_path)),
                    timeout=effective_download_timeout,
                )
            except asyncio.TimeoutError:
                dl_elapsed = time.monotonic() - t_dl_start
                error_msg = (
                    f"MP4 のダウンロードが {effective_download_timeout} 秒以内に完了しませんでした。"
                    f"（経過 {dl_elapsed:.1f} 秒）ネットワークまたは NotebookLM 側の応答を確認してください。"
                )
                logger.error(
                    "run_job download_video timeout job_id=%s notebook_id=%s timeout_sec=%s elapsed_sec=%.3f",
                    job_id,
                    nb.id,
                    effective_download_timeout,
                    dl_elapsed,
                )
                await _fail_job(store_update, job_id, steps, "download_ready", error_msg)
                if callback_url:
                    await send_webhook(
                        callback_url,
                        {
                            "event": "job.error",
                            "job_id": job_id,
                            "status": "error",
                            "error_message": error_msg,
                        },
                    )
                return

            dl_elapsed = time.monotonic() - t_dl_start
            out_size = output_path.stat().st_size if output_path.is_file() else 0
            logger.info(
                "run_job video downloaded job_id=%s notebook_id=%s output_path=%s "
                "size_bytes=%s elapsed_sec=%.3f",
                job_id,
                nb.id,
                output_path,
                out_size,
                dl_elapsed,
            )

            thumbnail_path: Optional[Path] = None
            try:
                steps = await _set_step_status(
                    store_update, job_id, steps, "download_ready", "in_progress",
                    message="サムネイルを生成中..."
                )
                thumbnail_path = await asyncio.get_event_loop().run_in_executor(
                    None, storage_mod.extract_thumbnail_locally, job_id, output_path
                )
                thumbnail_generated = True
                logger.info("run_job thumbnail generated job_id=%s path=%s", job_id, thumbnail_path)
            except Exception as thumb_exc:
                logger.warning(
                    "run_job thumbnail generation failed (continue): job_id=%s err=%s",
                    job_id,
                    thumb_exc,
                )

            if storage_mod.is_remote_object_storage_enabled():
                if thumbnail_path is not None:
                    try:
                        await asyncio.get_event_loop().run_in_executor(
                            None, storage_mod.upload_thumbnail_to_s3, job_id, thumbnail_path
                        )
                        logger.info("run_job thumbnail upload success job_id=%s", job_id)
                    except Exception as thumb_exc:
                        logger.warning(
                            "run_job thumbnail upload failed (continue): job_id=%s err=%s",
                            job_id,
                            thumb_exc,
                        )
                        if thumbnail_path.exists():
                            logger.info(
                                "run_job keep local thumbnail for debugging: job_id=%s path=%s",
                                job_id,
                                thumbnail_path,
                            )

                logger.info(
                    "run_job s3 upload start job_id=%s output_path=%s",
                    job_id,
                    output_path,
                )
                steps = await _set_step_status(
                    store_update, job_id, steps, "download_ready", "in_progress",
                    message="MP4 を S3 にアップロード中..."
                )
                effective_upload_timeout = _effective_phase_timeout_sec(timeout)
                logger.info(
                    "run_job mp4 remote upload start job_id=%s output_path=%s timeout_sec=%s",
                    job_id,
                    output_path,
                    effective_upload_timeout,
                )
                t_up_start = time.monotonic()
                try:
                    await asyncio.wait_for(
                        asyncio.get_event_loop().run_in_executor(
                            None, storage_mod.upload_mp4_to_s3, job_id, output_path
                        ),
                        timeout=effective_upload_timeout,
                    )
                except asyncio.TimeoutError:
                    up_elapsed = time.monotonic() - t_up_start
                    error_msg = (
                        f"MP4 のオブジェクトストレージへのアップロードが "
                        f"{effective_upload_timeout} 秒以内に完了しませんでした。"
                        f"（経過 {up_elapsed:.1f} 秒）"
                    )
                    logger.error(
                        "run_job mp4 upload timeout job_id=%s timeout_sec=%s elapsed_sec=%.3f",
                        job_id,
                        effective_upload_timeout,
                        up_elapsed,
                    )
                    await _fail_job(store_update, job_id, steps, "download_ready", error_msg)
                    if callback_url:
                        await send_webhook(
                            callback_url,
                            {
                                "event": "job.error",
                                "job_id": job_id,
                                "status": "error",
                                "error_message": error_msg,
                            },
                        )
                    return

                logger.info(
                    "run_job s3 upload success job_id=%s elapsed_sec=%.3f",
                    job_id,
                    time.monotonic() - t_up_start,
                )

            steps = await _set_step_status(
                store_update, job_id, steps, "download_ready", "completed"
            )
            logger.info("run_job step success job_id=%s step=download_ready", job_id)

        # ローカル一時ファイルを削除
        storage_mod.cleanup_local_csv(source_paths)

        from datetime import datetime, timezone
        completed_at = datetime.now(timezone.utc).isoformat()
        await store_update(
            job_id,
            status="completed",
            steps=steps,
            completedAt=completed_at,
        )
        logger.info("run_job completed job_id=%s completed_at=%s", job_id, completed_at)

        # ── Step 6: videos テーブルを更新 + Slack 通知 ────────────
        await _on_job_completed(job_id, notebook_title, thumbnail_generated)

        if callback_url:
            await send_webhook(
                callback_url,
                {
                    "event": "job.completed",
                    "job_id": job_id,
                    "status": "completed",
                    "completed_at": completed_at,
                },
            )

    except Exception as exc:
        current_step = "create_notebook"
        for s in steps:
            if s["status"] == "in_progress":
                current_step = s["id"]
                break

        exc_type = type(exc).__name__
        exc_msg = str(exc).split("\n")[0]
        error_detail = f"[{exc_type}] {exc_msg}"
        tb = traceback.format_exc()

        print(f"\n[RUNNER ERROR] Job {job_id} failed at step '{current_step}'")
        print(f"[RUNNER ERROR] {error_detail}")
        print(f"[RUNNER ERROR] Traceback:\n{tb}", flush=True)

        logger.error("Job %s failed at step '%s': %s", job_id, current_step, error_detail)

        if _is_notebooklm_auth_error(exc):
            error_message = (
                "NotebookLM の認証セッションが無効または期限切れです。"
                "管理画面の NotebookLM 認証から再ログインして、再度動画生成を実行してください。"
            )
        else:
            error_message = f"予期しないエラーが発生しました: {error_detail}"
        await _fail_job(
            store_update, job_id, steps, current_step,
            error_message,
        )

        if callback_url:
            await send_webhook(
                callback_url,
                {
                    "event": "job.error",
                    "job_id": job_id,
                    "status": "error",
                    "error_message": error_message,
                },
            )
    finally:
        if semaphore is not None:
            semaphore.release()


def _build_thumbnail_url(video_id: str) -> Optional[str]:
    base_url = os.environ.get("API_BASE_URL")
    if not base_url:
        return None
    return urljoin(base_url.rstrip("/") + "/", f"/api/videos/{video_id}/thumbnail")


async def _mark_video_failed_for_job(job_id: str) -> None:
    """ジョブ失敗時、対応する videos レコードがあれば status=error に更新する。"""
    try:
        import database as db

        video = await db.get_video_by_job_id(job_id)
        if video:
            await db.update_video(video["id"], status="error")
        else:
            logger.debug("ジョブ %s に対応する動画レコードなし（動画ステータス更新スキップ）", job_id)
    except Exception as e:
        logger.error("ジョブ失敗後の動画ステータス更新エラー job_id=%s: %s", job_id, e)


async def _on_job_completed(job_id: str, title: str, thumbnail_generated: bool = False) -> None:
    """ジョブ完了後の後処理: videos テーブル更新 + Slack 通知"""
    try:
        import database as db
        from datetime import datetime, timezone
        from slack_notifier import notify_video_ready

        video = await db.get_video_by_job_id(job_id)
        if video:
            from datetime import datetime, timezone
            published_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")
            update_payload: dict = {
                "status": "ready",
                "published_at": published_at,
            }
            if thumbnail_generated:
                thumbnail_url = _build_thumbnail_url(video["id"])
                if thumbnail_url:
                    update_payload["thumbnail_url"] = thumbnail_url
            await db.update_video(
                video["id"],
                **update_payload,
            )
            updated_video = await db.get_video(video["id"])
            await notify_video_ready(
                video_id=video["id"],
                title=title,
                category_name=updated_video.get("category_name") if updated_video else None,
            )
        else:
            logger.warning("ジョブ %s に対応する動画レコードが見つかりません", job_id)
    except Exception as e:
        logger.error("ジョブ完了後処理エラー job_id=%s: %s", job_id, e)
