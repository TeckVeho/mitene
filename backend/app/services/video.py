"""Video path helpers and API dict mapping."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from app.config import OUTPUTS_DIR
from app.schemas.comment import CommentResponse
from app.schemas.video import AdminVideoPatchRequest, VideoResponse


def build_wiki_url(git_path: Optional[str]) -> Optional[str]:
    """article の git_path から Wiki サイトの URL を構築する"""
    if not git_path:
        return None
    base = os.environ.get("WIKI_BASE_URL", "").rstrip("/")
    if not base:
        repo_url = os.environ.get("WIKI_GIT_REPO_URL", "").rstrip("/").removesuffix(".git")
        branch = os.environ.get("WIKI_GIT_BRANCH", "main")
        if repo_url and "github.com" in repo_url:
            base = f"{repo_url}/blob/{branch}"
        else:
            return None
    return f"{base}/{git_path}" if base else None


def resolve_local_mp4_path(video_id: str, job_id: Optional[str]) -> Optional[Path]:
    """
    ローカル outputs: まず job_id.mp4（本番・S3 と同じキー規則）、無ければ video_id.mp4（手動配置や旧データ向け）。
    """
    if job_id:
        p = OUTPUTS_DIR / f"{job_id}.mp4"
        if p.is_file():
            return p
    p = OUTPUTS_DIR / f"{video_id}.mp4"
    if p.is_file():
        return p
    return None


def resolve_local_thumbnail_path(video_id: str, job_id: Optional[str]) -> Optional[Path]:
    thumbs = OUTPUTS_DIR / "thumbnails"
    if job_id:
        p = thumbs / f"{job_id}.jpg"
        if p.is_file():
            return p
    p = thumbs / f"{video_id}.jpg"
    if p.is_file():
        return p
    return None


def dict_to_comment(d: dict) -> CommentResponse:
    replies = [dict_to_comment(r) for r in (d.get("replies") or [])]
    return CommentResponse(
        id=d["id"],
        videoId=d["videoId"],
        userId=d["userId"],
        displayName=d["displayName"],
        text=d["text"],
        likeCount=int(d.get("likeCount", 0)),
        likedByMe=bool(d.get("likedByMe")),
        createdAt=str(d.get("createdAt", "")),
        parentId=d.get("parentId"),
        replies=replies,
    )


def video_dict_to_response(v: dict, viewer_count: int = 0, view_count: int = 0) -> VideoResponse:
    git_path = v.get("article_git_path")
    wiki_url = build_wiki_url(git_path) if git_path else None
    return VideoResponse(
        id=v["id"],
        title=v["title"],
        description=v.get("description"),
        thumbnailUrl=v.get("thumbnail_url"),
        durationSec=v.get("duration_sec"),
        style=v.get("style"),
        status=v.get("status", "generating"),
        publishedAt=str(v["published_at"]) if v.get("published_at") else None,
        createdAt=str(v.get("created_at", "")),
        updatedAt=str(v.get("updated_at", "")),
        jobId=v.get("job_id"),
        articleId=v.get("article_id"),
        categoryId=v.get("category_id"),
        categoryName=v.get("category_name"),
        categorySlug=v.get("category_slug"),
        watched=v.get("watched"),
        watchLater=v.get("watch_later"),
        liked=v.get("liked"),
        wikiUrl=wiki_url,
        viewerCount=viewer_count,
        viewCount=view_count,
    )


def admin_video_patch_to_db(body: AdminVideoPatchRequest) -> dict:
    raw = body.model_dump(exclude_unset=True)
    key_map = {
        "thumbnailUrl": "thumbnail_url",
        "durationSec": "duration_sec",
        "publishedAt": "published_at",
    }
    return {key_map.get(k, k): v for k, v in raw.items()}
