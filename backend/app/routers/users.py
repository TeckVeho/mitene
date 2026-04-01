"""App user profile, history, watch-later, liked."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Cookie, Header, HTTPException, Response

import database
from app.dependencies import is_admin_email
from app.schemas.user import UserLoginRequest, UserResponse, WatchHistoryItem
from app.schemas.video import VideoResponse
from app.services.video import video_dict_to_response

router = APIRouter(prefix="/api/users", tags=["users"])


@router.post("/login", response_model=UserResponse)
async def user_login(req: UserLoginRequest, response: Response):
    if not req.email or not req.displayName:
        raise HTTPException(status_code=400, detail="メールアドレスと名前は必須です")
    user = await database.get_or_create_user(req.email, req.displayName)
    response.set_cookie(
        key="user_id",
        value=user["id"],
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 30,
    )
    em = user.get("email") or ""
    return UserResponse(
        id=user["id"],
        email=em,
        displayName=user.get("display_name", user.get("displayName", "")),
        createdAt=str(user.get("created_at", "")),
        isAdmin=is_admin_email(em),
    )


@router.get("/me", response_model=Optional[UserResponse])
async def get_current_user(
    x_user_id: Optional[str] = Header(default=None),
    user_id: Optional[str] = Cookie(default=None),
):
    """未ログイン時は 401 ではなく null（200）を返す。呼び出し側は認証なしで利用可能。"""
    uid = x_user_id or user_id
    if not uid:
        return None
    user = await database.get_user(uid)
    if not user:
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")
    em = user.get("email") or ""
    return UserResponse(
        id=user["id"],
        email=em,
        displayName=user.get("display_name", user.get("displayName", "")),
        createdAt=str(user.get("created_at", "")),
        isAdmin=is_admin_email(em),
    )


@router.get("/me/history", response_model=list[WatchHistoryItem])
async def get_watch_history(
    x_user_id: Optional[str] = Header(default=None),
    user_id: Optional[str] = Cookie(default=None),
    limit: int = 50,
):
    uid = x_user_id or user_id
    if not uid:
        raise HTTPException(status_code=401, detail="ログインが必要です")
    history = await database.get_watch_history(uid, limit=limit)
    return [
        WatchHistoryItem(
            id=h["id"],
            userId=h["user_id"],
            videoId=h["video_id"],
            videoTitle=h.get("videoTitle", h.get("video_title")),
            videoStatus=h.get("videoStatus", h.get("video_status")),
            categoryName=h.get("categoryName", h.get("category_name")),
            categorySlug=h.get("categorySlug", h.get("category_slug")),
            completed=bool(h.get("completed", True)),
            watchedAt=str(h.get("watched_at", "")),
        )
        for h in history
    ]


@router.get("/me/watch-later", response_model=list[VideoResponse])
async def get_watch_later(
    x_user_id: Optional[str] = Header(default=None),
    user_id: Optional[str] = Cookie(default=None),
    limit: int = 100,
):
    uid = x_user_id or user_id
    if not uid:
        raise HTTPException(status_code=401, detail="ログインが必要です")
    videos = await database.get_watch_later_videos(uid, limit=limit)
    liked_ids = await database.get_liked_video_ids(uid)
    history = await database.get_watch_history(uid, limit=1000)
    watched_ids = {h["video_id"] for h in history}
    for v in videos:
        v["watched"] = v["id"] in watched_ids
        v["watch_later"] = True
        v["liked"] = v["id"] in liked_ids
    ids = [v["id"] for v in videos]
    watch_counts = await database.get_video_watch_counts_batch(ids)
    return [
        video_dict_to_response(v, *watch_counts.get(v["id"], (0, 0)))
        for v in videos
    ]


@router.get("/me/liked", response_model=list[VideoResponse])
async def get_liked_videos(
    x_user_id: Optional[str] = Header(default=None),
    user_id: Optional[str] = Cookie(default=None),
    limit: int = 100,
):
    uid = x_user_id or user_id
    if not uid:
        raise HTTPException(status_code=401, detail="ログインが必要です")
    videos = await database.get_liked_videos(uid, limit=limit)
    watch_later_ids = await database.get_watch_later_ids(uid)
    history = await database.get_watch_history(uid, limit=1000)
    watched_ids = {h["video_id"] for h in history}
    for v in videos:
        v["watched"] = v["id"] in watched_ids
        v["watch_later"] = v["id"] in watch_later_ids
        v["liked"] = True
    ids = [v["id"] for v in videos]
    watch_counts = await database.get_video_watch_counts_batch(ids)
    return [
        video_dict_to_response(v, *watch_counts.get(v["id"], (0, 0)))
        for v in videos
    ]
