"""Legacy admin job listing and download."""

from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, RedirectResponse

import database
import storage
from app.config import OUTPUTS_DIR
from app.dependencies import require_admin_user
from app.schemas.job import Job, JobStats

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("/stats", response_model=JobStats)
async def get_stats(_admin: Annotated[dict, Depends(require_admin_user)]):
    jobs = await database.store_list()
    return JobStats(
        total=len(jobs),
        processing=sum(1 for j in jobs if j["status"] == "processing"),
        completed=sum(1 for j in jobs if j["status"] == "completed"),
        error=sum(1 for j in jobs if j["status"] == "error"),
    )


@router.get("", response_model=list[Job])
async def get_jobs(
    _admin: Annotated[dict, Depends(require_admin_user)],
    status: Optional[str] = None,
    type: Optional[str] = None,
):
    return await database.store_list(status, job_type=type)


@router.get("/{job_id}", response_model=Job)
async def get_job(job_id: str, _admin: Annotated[dict, Depends(require_admin_user)]):
    return await database.store_get(job_id)


@router.get("/{job_id}/download")
async def download_job(job_id: str, _admin: Annotated[dict, Depends(require_admin_user)]):
    job = await database.store_get(job_id)
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="ファイルはまだ準備ができていません")

    if storage.is_s3_enabled():
        url = storage.generate_mp4_download_url(job_id)
        if url is None:
            raise HTTPException(status_code=500, detail="ダウンロード URL の生成に失敗しました")
        return RedirectResponse(url=url, status_code=302)

    output_path = OUTPUTS_DIR / f"{job_id}.mp4"
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="動画ファイルが見つかりません")

    safe_title = job["notebookTitle"].replace("/", "_").replace("\\", "_")
    return FileResponse(
        path=str(output_path),
        media_type="video/mp4",
        filename=f"{safe_title}.mp4",
    )
