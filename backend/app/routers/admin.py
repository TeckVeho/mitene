"""Admin CMS for videos and articles."""

from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Response

import database
import storage
from app.config import OUTPUTS_DIR
from app.dependencies import require_admin_user
from app.schemas.common import ArticleResponse
from app.schemas.video import AdminVideoPatchRequest, VideoResponse
from app.services.video import admin_video_patch_to_db, video_dict_to_response

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/videos", response_model=list[VideoResponse])
async def get_admin_videos(
    _admin: Annotated[dict, Depends(require_admin_user)],
    search: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
):
    """全ステータス・全言語の動画一覧（管理用）"""
    videos = await database.list_videos(
        category_slug=None,
        search=search,
        status=None,
        limit=limit,
        offset=offset,
        user_id=None,
        language=None,
        published_after=None,
    )
    out: list[VideoResponse] = []
    for v in videos:
        vc, vv = await database.get_video_watch_counts(v["id"])
        out.append(video_dict_to_response(v, vc, vv))
    return out


@router.patch("/videos/{video_id}", response_model=VideoResponse)
async def patch_admin_video(
    video_id: str,
    body: AdminVideoPatchRequest,
    _admin: Annotated[dict, Depends(require_admin_user)],
):
    existing = await database.get_video(video_id)
    if not existing:
        raise HTTPException(status_code=404, detail="動画が見つかりません")
    patch = admin_video_patch_to_db(body)
    updated = await database.update_video(video_id, **patch)
    if not updated:
        raise HTTPException(status_code=404, detail="動画が見つかりません")
    vc, vv = await database.get_video_watch_counts(video_id)
    return video_dict_to_response(updated, vc, vv)


@router.delete("/videos/{video_id}", status_code=204)
async def delete_admin_video(
    video_id: str,
    _admin: Annotated[dict, Depends(require_admin_user)],
):
    video = await database.get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="動画が見つかりません")
    job_id = video.get("job_id")
    deleted = await database.delete_video(video_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="動画が見つかりません")
    if job_id:
        from app.config import UPLOADS_DIR

        storage.delete_job_outputs(job_id, outputs_dir=OUTPUTS_DIR, uploads_dir=UPLOADS_DIR)
    return Response(status_code=204)


@router.get("/articles", response_model=list[ArticleResponse])
async def get_admin_articles(_admin: Annotated[dict, Depends(require_admin_user)]):
    """記事一覧と動画生成状況を返す（管理用）"""
    articles = await database.list_articles()
    return [
        ArticleResponse(
            id=a["id"],
            title=a["title"],
            gitPath=a.get("git_path", a.get("gitPath", "")),
            gitHash=a.get("git_hash"),
            categoryId=a.get("category_id"),
            categoryName=a.get("categoryName", a.get("category_name")),
            latestVideoId=a.get("latestVideoId", a.get("latest_video_id")),
            latestVideoStatus=a.get("latestVideoStatus", a.get("latest_video_status")),
            createdAt=str(a.get("created_at", "")),
            updatedAt=str(a.get("updated_at", "")),
        )
        for a in articles
    ]
