"""
バックグラウンドジョブランナー
generate_video_from_csv.py のロジックを元に、各ステップでジョブストアを更新する。

S3_BUCKET_NAME 環境変数が設定されている場合、MP4 生成後に S3 へアップロードし、
ローカルの一時ファイルを削除する。
"""

import asyncio
import logging
import traceback
from pathlib import Path
from typing import Callable, Awaitable, Optional

import storage as storage_mod
from webhook import send_webhook

logger = logging.getLogger(__name__)


STEP_IDS = [
    "create_notebook",
    "add_source",
    "generate_video",
    "wait_completion",
    "download_ready",
]

StoreUpdateFn = Callable[..., Awaitable[dict]]


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


async def run_job(
    *,
    job_id: str,
    csv_paths: list[Path],
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

    ステップ:
      1. ノートブック作成
      2. CSV ソース追加
      3. 動画生成開始
      4. 生成完了待機
      5. MP4 ダウンロード（→ S3 が有効な場合は S3 にアップロード）
    """
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

    try:
        async with await NotebookLMClient.from_storage() as client:

            # ── Step 1: ノートブック作成 ──────────────────────────────
            steps = await _set_step_status(
                store_update, job_id, steps, "create_notebook", "in_progress"
            )
            nb = await client.notebooks.create(notebook_title)
            steps = await _set_step_status(
                store_update, job_id, steps, "create_notebook", "completed"
            )

            # ── Step 2: CSV をソースとして追加 ───────────────────────
            total = len(csv_paths)
            for idx, csv_path in enumerate(csv_paths, start=1):
                progress = f"({idx}/{total})" if total > 1 else ""
                steps = await _set_step_status(
                    store_update, job_id, steps, "add_source", "in_progress",
                    message=f"CSVファイルをアップロード中... {progress}"
                )
                source = await client.sources.add_file(nb.id, csv_path)

                steps = await _set_step_status(
                    store_update, job_id, steps, "add_source", "in_progress",
                    message=f"ソースのインデックスを作成中... {progress}"
                )
                ready = await _wait_for_source_ready(
                    client, nb.id, source.id, csv_path.name
                )
                if not ready:
                    error_msg = (
                        f"{csv_path.name} のインデックス作成がタイムアウトしました。"
                        "CSVファイルのサイズを確認してください。"
                    )
                    await _fail_job(store_update, job_id, steps, "add_source", error_msg)
                    if callback_url:
                        await send_webhook(
                            callback_url,
                            {"event": "job.error", "job_id": job_id, "status": "error", "error_message": error_msg},
                        )
                    return

            steps = await _set_step_status(
                store_update, job_id, steps, "add_source", "completed"
            )

            # ── Step 3: 解説動画を生成 ────────────────────────────────
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
            steps = await _set_step_status(
                store_update, job_id, steps, "generate_video", "completed"
            )

            # ── Step 4: 生成完了まで待機 ──────────────────────────────
            steps = await _set_step_status(
                store_update, job_id, steps, "wait_completion", "in_progress",
                message=f"動画を生成中... (最大 {timeout // 60} 分)"
            )
            final = await client.artifacts.wait_for_completion(
                nb.id,
                gen_status.task_id,
                timeout=timeout,
                poll_interval=10,
            )

            if not final.is_complete:
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

            # ── Step 5: MP4 ダウンロード ──────────────────────────────
            steps = await _set_step_status(
                store_update, job_id, steps, "download_ready", "in_progress",
                message="MP4ファイルをダウンロード中..."
            )
            await client.artifacts.download_video(nb.id, str(output_path))

            # S3 が有効な場合: ローカルに保存後 S3 にアップロードし一時ファイル削除
            if storage_mod.is_s3_enabled():
                steps = await _set_step_status(
                    store_update, job_id, steps, "download_ready", "in_progress",
                    message="MP4 を S3 にアップロード中..."
                )
                await asyncio.get_event_loop().run_in_executor(
                    None, storage_mod.upload_mp4_to_s3, job_id, output_path
                )

            steps = await _set_step_status(
                store_update, job_id, steps, "download_ready", "completed"
            )

        # ローカル CSV 一時ファイルを削除
        storage_mod.cleanup_local_csv(csv_paths)

        from datetime import datetime, timezone
        completed_at = datetime.now(timezone.utc).isoformat()
        await store_update(
            job_id,
            status="completed",
            steps=steps,
            completedAt=completed_at,
        )

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
