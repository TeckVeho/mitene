"""Wiki sync admin routes."""

from __future__ import annotations

import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, BackgroundTasks, Depends

import database
from app.config import OUTPUTS_DIR
from app.dependencies import require_admin_user
from app.job_runtime import job_semaphore
from app.schemas.wiki import WikiSyncDirectoryRequest
from app.services.runner import run_job
from app.services.wiki_sync import get_sync_status, get_wiki_directories, sync_wiki_from_directory

router = APIRouter(prefix="/api/wiki", tags=["wiki"])


@router.get("/directories")
async def wiki_get_directories(_admin: Annotated[dict, Depends(require_admin_user)]):
    """リポジトリ内の .md を含むディレクトリ一覧を返す"""
    return get_wiki_directories()


@router.post("/sync-directory")
async def trigger_wiki_sync_directory(
    background_tasks: BackgroundTasks,
    _admin: Annotated[dict, Depends(require_admin_user)],
    payload: Optional[WikiSyncDirectoryRequest] = None,
    path: str = "",
):
    """指定ディレクトリ配下の .md ファイルのみを同期し、動画生成を実行する"""
    requested_paths = payload.paths if payload and payload.paths else None
    requested_path = payload.path if payload and payload.path is not None else path

    sync_id = f"sync_{uuid.uuid4().hex[:8]}"

    async def _do_sync():
        await sync_wiki_from_directory(
            relative_dir=requested_path or "",
            target_paths=requested_paths,
            store_update_fn=database.store_update,
            run_job_fn=run_job,
            semaphore=job_semaphore,
            outputs_dir=OUTPUTS_DIR,
            sync_id=sync_id,
        )

    background_tasks.add_task(_do_sync)
    return {"message": "ディレクトリの動画作成を開始しました", "sync_id": sync_id}


@router.get("/sync-status")
async def get_wiki_sync_status(_admin: Annotated[dict, Depends(require_admin_user)]):
    """Wiki同期の現在の状態を返す"""
    return get_sync_status()
