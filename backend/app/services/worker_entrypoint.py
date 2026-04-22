"""
Cloud Run Job entrypoint: one execution processes one video job (env JOB_ID).

Not used on local/EC2; the API runs ``run_job`` inline there.
Run: ``python -m app.services.worker_entrypoint``
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logging.getLogger("notebooklm").setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)


async def _async_main() -> int:
    import app.config  # noqa: F401 — load_dotenv
    import database as db
    import storage as storage_mod
    from app.config import OUTPUTS_DIR, UPLOADS_DIR, VIDEO_JOB_TIMEOUT_DEFAULT_SEC
    from app.services.notebooklm_gcs import (
        download_storage_state_if_configured,
        log_notebooklm_storage_config,
    )
    from app.services.runner import _mark_video_failed_for_job, run_job

    job_id = os.environ.get("JOB_ID", "").strip()
    if not job_id:
        logger.error("JOB_ID が設定されていません")
        return 1

    logger.info("worker start job_id=%s", job_id)
    log_notebooklm_storage_config()
    download_storage_state_if_configured()
    await db.init_db()
    try:
        job = await db.store_get(job_id)
        logger.info(
            "worker loaded job row job_id=%s status=%s execution_name=%s",
            job_id,
            job.get("status"),
            job.get("executionName"),
        )
        raw_names = (job.get("sourceFileNames") or job.get("csvFileNames") or "").strip()
        if not raw_names:
            logger.error("ジョブにソースファイル名がありません job_id=%s", job_id)
            return 1

        files = [n.strip() for n in raw_names.split(",") if n.strip()]
        source_paths: list[Path] = []
        for fn in files:
            p = UPLOADS_DIR / f"{job_id}_{fn}"
            if p.is_file():
                logger.info("worker source local hit job_id=%s path=%s", job_id, p)
                source_paths.append(p)
                continue

            logger.info(
                "worker source local miss job_id=%s filename=%s path=%s, attempting restore",
                job_id,
                fn,
                p,
            )
            restored = storage_mod.restore_source_file_locally(UPLOADS_DIR, job_id, fn)
            if restored is None:
                logger.error(
                    "worker source unavailable job_id=%s filename=%s path=%s",
                    job_id,
                    fn,
                    p,
                )
                try:
                    await db.store_update(
                        job_id,
                        status="error",
                        errorMessage=f"Source file is missing locally and remotely: {p}",
                    )
                except Exception:
                    pass
                await _mark_video_failed_for_job(job_id)
                return 1
            source_paths.append(restored)

        output_path = OUTPUTS_DIR / f"{job_id}.mp4"
        logger.info(
            "worker invoking run_job job_id=%s source_count=%d output_path=%s",
            job_id,
            len(source_paths),
            output_path,
        )

        await run_job(
            job_id=job_id,
            source_paths=source_paths,
            output_path=output_path,
            notebook_title=job["notebookTitle"],
            instructions=job["instructions"],
            style=job.get("style") or "whiteboard",
            video_format=job.get("format") or "explainer",
            language=job.get("language") or "ja",
            timeout=int(job.get("timeout") or VIDEO_JOB_TIMEOUT_DEFAULT_SEC),
            store_update=db.store_update,
            callback_url=job.get("callbackUrl"),
            semaphore=None,
        )
        logger.info("worker finished successfully job_id=%s", job_id)
        return 0
    except Exception:
        logger.exception("worker_entrypoint failed job_id=%s", job_id)
        return 1
    finally:
        try:
            await db.close_db()
        except Exception:
            logger.debug("close_db skipped or failed", exc_info=True)


def main() -> None:
    try:
        code = asyncio.run(_async_main())
    except Exception:
        logger.exception("worker_entrypoint 致命的エラー")
        code = 1
    sys.exit(code)


if __name__ == "__main__":
    main()
