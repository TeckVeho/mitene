"""Public video catalog, stream, thumbnail, watch progress."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Cookie, Header, HTTPException
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse

import database
import storage
from app.schemas.user import WatchRequest
from app.schemas.video import VideoResponse
from app.services.video import resolve_local_mp4_path, resolve_local_thumbnail_path, video_dict_to_response

router = APIRouter(prefix="/api/videos", tags=["videos"])


@router.get("", response_model=list[VideoResponse])
async def get_videos(
    category: Optional[str] = None,
    search: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    locale: Optional[str] = None,
    published_after: Optional[str] = None,
    x_user_id: Optional[str] = Header(default=None),
):
    language = locale if locale in ("ja", "vi") else "ja"
    videos = await database.list_videos(
        category_slug=category,
        search=search,
        status=status,
        limit=limit,
        offset=offset,
        user_id=x_user_id,
        language=language,
        published_after=published_after,
    )
    if x_user_id:
        watch_later_ids = await database.get_watch_later_ids(x_user_id)
        liked_ids = await database.get_liked_video_ids(x_user_id)
        for v in videos:
            v["watch_later"] = v["id"] in watch_later_ids
            v["liked"] = v["id"] in liked_ids
    ids = [v["id"] for v in videos]
    watch_counts = await database.get_video_watch_counts_batch(ids)
    return [
        video_dict_to_response(v, *watch_counts.get(v["id"], (0, 0)))
        for v in videos
    ]


@router.get("/{video_id}", response_model=VideoResponse)
async def get_video(video_id: str, x_user_id: Optional[str] = Header(default=None)):
    video = await database.get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="動画が見つかりません")
    if x_user_id:
        history = await database.get_watch_history(x_user_id, limit=1000)
        watched_ids = {h["video_id"] for h in history}
        video["watched"] = video_id in watched_ids
        watch_later_ids = await database.get_watch_later_ids(x_user_id)
        liked_ids = await database.get_liked_video_ids(x_user_id)
        video["watch_later"] = video_id in watch_later_ids
        video["liked"] = video_id in liked_ids
    viewer_count, view_count = await database.get_video_watch_counts(video_id)
    return video_dict_to_response(video, viewer_count, view_count)


@router.get("/{video_id}/stream")
async def stream_video(video_id: str):
    """動画をストリーミングまたはダウンロードURLを返す"""
    video = await database.get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="動画が見つかりません")
    if video.get("status") != "ready":
        raise HTTPException(status_code=400, detail="動画はまだ準備ができていません")

    job_id = video.get("job_id")

    if storage.is_remote_object_storage_enabled() and job_id:
        url = storage.generate_mp4_streaming_url(job_id, expires_in=86400)
        if url:
            return RedirectResponse(url=url, status_code=302)

    output_path = resolve_local_mp4_path(video_id, job_id)
    if not output_path:
        raise HTTPException(status_code=404, detail="動画ファイルが見つかりません")

    def iter_file():
        with open(output_path, "rb") as f:
            while chunk := f.read(1024 * 1024):
                yield chunk

    return StreamingResponse(iter_file(), media_type="video/mp4")


@router.get("/{video_id}/thumbnail")
async def stream_thumbnail(video_id: str):
    """サムネイル画像を返す（S3時はリダイレクト、ローカル時はファイル返却）"""
    video = await database.get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="動画が見つかりません")
    if video.get("status") != "ready":
        raise HTTPException(status_code=400, detail="動画はまだ準備ができていません")

    job_id = video.get("job_id")

    if storage.is_remote_object_storage_enabled() and job_id:
        url = storage.generate_thumbnail_streaming_url(job_id, expires_in=86400)
        if url:
            return RedirectResponse(url=url, status_code=302)

    thumbnail_path = resolve_local_thumbnail_path(video_id, job_id)
    if not thumbnail_path:
        raise HTTPException(status_code=404, detail="サムネイルが見つかりません")
    return FileResponse(path=str(thumbnail_path), media_type="image/jpeg")


@router.post("/{video_id}/watch")
async def record_watch(
    video_id: str,
    req: WatchRequest,
    x_user_id: Optional[str] = Header(default=None),
):
    if not x_user_id:
        raise HTTPException(status_code=401, detail="ユーザーIDが必要です")
    video = await database.get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="動画が見つかりません")
    record = await database.record_watch(x_user_id, video_id, req.completed)
    return {"success": True, "record": record}


@router.post("/{video_id}/watch-later")
async def toggle_watch_later(
    video_id: str,
    x_user_id: Optional[str] = Header(default=None),
    user_id: Optional[str] = Cookie(default=None),
):
    uid = x_user_id or user_id
    if not uid:
        raise HTTPException(status_code=401, detail="ログインが必要です")
    video = await database.get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="動画が見つかりません")
    added = await database.toggle_watch_later(uid, video_id)
    return {"success": True, "added": added}


@router.post("/{video_id}/liked")
async def toggle_liked_video(
    video_id: str,
    x_user_id: Optional[str] = Header(default=None),
    user_id: Optional[str] = Cookie(default=None),
):
    uid = x_user_id or user_id
    if not uid:
        raise HTTPException(status_code=401, detail="ログインが必要です")
    video = await database.get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="動画が見つかりません")
    added = await database.toggle_liked_video(uid, video_id)
    return {"success": True, "added": added}
