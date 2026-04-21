"""Dispatch video pipeline: inline asyncio (local / EC2) or Cloud Run Job (GCP)."""

from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

StoreUpdateFn = Callable[..., Awaitable[dict]]
RunJobFn = Callable[..., Awaitable[None]]


def _dispatch_mode() -> str:
    """Default inline (legacy). Set JOB_DISPATCH_MODE=cloud_run_job for GCP Cloud Run Job."""
    m = os.environ.get("JOB_DISPATCH_MODE", "").strip().lower()
    if m == "cloud_run_job":
        return "cloud_run_job"
    return "inline"


def _gcp_project() -> str:
    return (
        os.environ.get("GOOGLE_CLOUD_PROJECT", "").strip()
        or os.environ.get("GCP_PROJECT_ID", "").strip()
        or ""
    )


def _worker_job_resource_name() -> str:
    project = _gcp_project()
    job = os.environ.get("CLOUD_RUN_WORKER_JOB_NAME", "").strip()
    region = (
        os.environ.get("CLOUD_RUN_REGION", "").strip()
        or os.environ.get("CLOUD_RUN_WORKER_REGION", "").strip()
        or "asia-northeast1"
    )
    if not project or not job:
        raise RuntimeError(
            "cloud_run_job requires GOOGLE_CLOUD_PROJECT or GCP_PROJECT_ID, "
            "CLOUD_RUN_WORKER_JOB_NAME, and CLOUD_RUN_REGION (or CLOUD_RUN_WORKER_REGION)."
        )
    return f"projects/{project}/locations/{region}/jobs/{job}"


def _sync_run_cloud_run_job(job_id: str) -> Optional[str]:
    try:
        from google.api_core import exceptions as gexc  # pyright: ignore[reportMissingImports]
        from google.cloud.run_v2 import JobsClient  # pyright: ignore[reportMissingImports]
        from google.cloud.run_v2.types import EnvVar, RunJobRequest  # pyright: ignore[reportMissingImports]
    except ImportError as e:
        raise RuntimeError(
            "Install google-cloud-run: pip install google-cloud-run"
        ) from e

    client = JobsClient()
    request = RunJobRequest(
        name=_worker_job_resource_name(),
        overrides=RunJobRequest.Overrides(
            container_overrides=[
                RunJobRequest.Overrides.ContainerOverride(
                    env=[EnvVar(name="JOB_ID", value=job_id)],
                )
            ],
        ),
    )
    # Fire-and-forget: do NOT poll the LRO. Polling calls operations.get which
    # requires run.operations.get permission (not included in roles/run.jobsExecutorWithOverrides).
    # The initial RunJob response already includes metadata.execution because Cloud Run
    # creates the execution synchronously at accept time.
    try:
        operation = client.run_job(request=request)
    except gexc.GoogleAPICallError as exc:
        logger.error(
            "RunJob API error job_id=%s code=%s message=%s resource=%s",
            job_id,
            exc.__class__.__name__,
            getattr(exc, "message", str(exc)),
            request.name,
        )
        raise

    execution: Optional[str] = None
    meta = getattr(operation, "metadata", None)
    if meta is not None:
        ex = getattr(meta, "execution", None)
        if isinstance(ex, str) and ex.strip():
            execution = ex.strip()

    if execution:
        logger.info("Cloud Run Job started job_id=%s execution=%s", job_id, execution)
    else:
        op_proto = getattr(operation, "operation", None)
        op_name = getattr(op_proto, "name", None) if op_proto is not None else None
        logger.info(
            "Cloud Run Job dispatched job_id=%s operation=%s (execution name not in initial metadata)",
            job_id,
            op_name,
        )
    return execution


async def _mark_dispatch_failed(store_update: StoreUpdateFn, job_id: str, message: str) -> None:
    from app.services.runner import _mark_video_failed_for_job

    import database as db

    try:
        row = await db.store_get(job_id)
        steps = list(row.get("steps", []))
        for s in steps:
            if s.get("status") == "in_progress":
                s["status"] = "error"
                s["message"] = message
        await store_update(
            job_id,
            status="error",
            steps=steps,
            errorMessage=message,
        )
    except Exception:
        try:
            await store_update(job_id, status="error", errorMessage=message)
        except Exception:
            logger.exception("store_update failed marking dispatch error job_id=%s", job_id)
    await _mark_video_failed_for_job(job_id)


async def dispatch_video_job(
    *,
    job_id: str,
    run_job_fn: RunJobFn,
    store_update: StoreUpdateFn,
    source_paths: list[Path],
    output_path: Path,
    notebook_title: str,
    instructions: str,
    style: str,
    video_format: str,
    language: str,
    timeout: int,
    callback_url: Optional[str],
    semaphore: Optional[asyncio.Semaphore],
) -> Optional[str]:
    """
    - inline: asyncio.create_task(run_job_fn(...)) — same as local/EC2 before.
    - cloud_run_job: call RunJob; worker reads JOB_ID; returns execution resource name if available.
    """
    mode = _dispatch_mode()
    logger.info("dispatch_video_job start job_id=%s mode=%s", job_id, mode)

    if mode == "cloud_run_job":
        try:
            execution = await asyncio.to_thread(_sync_run_cloud_run_job, job_id)
        except Exception as exc:
            msg = f"Failed to start Cloud Run Job: {exc}"
            logger.exception("dispatch_video_job failed job_id=%s", job_id)
            await _mark_dispatch_failed(store_update, job_id, msg)
            return None
        if execution:
            try:
                await store_update(job_id, executionName=execution)
            except Exception as exc:
                logger.warning(
                    "Failed to persist executionName job_id=%s err=%s", job_id, exc
                )
        logger.info(
            "dispatch_video_job success job_id=%s mode=%s execution=%s",
            job_id,
            mode,
            execution,
        )
        return execution

    asyncio.create_task(
        run_job_fn(
            job_id=job_id,
            source_paths=source_paths,
            output_path=output_path,
            notebook_title=notebook_title,
            instructions=instructions,
            style=style,
            video_format=video_format,
            language=language,
            timeout=timeout,
            store_update=store_update,
            callback_url=callback_url,
            semaphore=semaphore,
        )
    )
    logger.info("dispatch_video_job enqueued inline task job_id=%s mode=%s", job_id, mode)
    return None
