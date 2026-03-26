"""Video comments and comment likes."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Cookie, Header, HTTPException

import database
from app.schemas.comment import CommentResponse, CreateCommentBody
from app.services.video import dict_to_comment

router = APIRouter(prefix="/api", tags=["comments"])


@router.get("/videos/{video_id}/comments", response_model=list[CommentResponse])
async def list_video_comments(
    video_id: str,
    x_user_id: Optional[str] = Header(default=None),
    user_id: Optional[str] = Cookie(default=None),
):
    video = await database.get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="動画が見つかりません")
    viewer = x_user_id or user_id
    raw = await database.list_comments_for_video(video_id, viewer)
    return [dict_to_comment(c) for c in raw]


@router.post("/videos/{video_id}/comments", response_model=CommentResponse)
async def create_video_comment(
    video_id: str,
    body: CreateCommentBody,
    x_user_id: Optional[str] = Header(default=None),
    user_id: Optional[str] = Cookie(default=None),
):
    uid = x_user_id or user_id
    if not uid:
        raise HTTPException(status_code=401, detail="ログインが必要です")
    video = await database.get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="動画が見つかりません")
    created = await database.create_comment(video_id, uid, body.text, body.parentId)
    if not created:
        raise HTTPException(status_code=400, detail="コメントを投稿できません")
    return dict_to_comment(created)


@router.post("/comments/{comment_id}/like", response_model=CommentResponse)
async def toggle_comment_like_route(
    comment_id: str,
    x_user_id: Optional[str] = Header(default=None),
    user_id: Optional[str] = Cookie(default=None),
):
    uid = x_user_id or user_id
    if not uid:
        raise HTTPException(status_code=401, detail="ログインが必要です")
    out = await database.toggle_comment_like(comment_id, uid)
    if not out:
        raise HTTPException(status_code=404, detail="コメントが見つかりません")
    return dict_to_comment(out)
