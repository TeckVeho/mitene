"""Videos CRUD."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from . import connection
from .connection import (
    _USE_MYSQL,
    _articles_store,
    _categories_store,
    _comment_likes_store,
    _comments_store,
    _elearning_lock,
    _liked_videos_store,
    _now,
    _videos_store,
    _watch_history_store,
    _watch_later_store,
)


async def create_video(
    article_id: Optional[str],
    job_id: str,
    title: str,
    description: Optional[str] = None,
    style: Optional[str] = None,
    language: str = "ja",
) -> dict:
    if not _USE_MYSQL:
        async with _elearning_lock:
            vid_id = f"vid_{uuid.uuid4().hex[:8]}"
            cat_id = None
            cat_name = None
            cat_slug = None
            if article_id and article_id in _articles_store:
                art = _articles_store[article_id]
                cat_id = art.get("category_id")
                if cat_id and cat_id in _categories_store:
                    cat = _categories_store[cat_id]
                    cat_name = cat["name"]
                    cat_slug = cat["slug"]
            new_vid = {
                "id": vid_id,
                "article_id": article_id,
                "job_id": job_id,
                "title": title,
                "description": description,
                "thumbnail_url": None,
                "duration_sec": None,
                "style": style,
                "language": language,
                "status": "generating",
                "published_at": None,
                "created_at": _now(),
                "updated_at": _now(),
                "category_id": cat_id,
                "category_name": cat_name,
                "category_slug": cat_slug,
            }
            _videos_store[vid_id] = new_vid
            return dict(new_vid)

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")
    vid_id = str(uuid.uuid4())
    async with connection._pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO videos (id, article_id, job_id, title, description, style, language, status, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s, 'generating', %s, %s)",
                (vid_id, article_id, job_id, title, description, style, language, now_str, now_str),
            )
            await cur.execute(
                "SELECT v.*, c.id as category_id, c.name as category_name, c.slug as category_slug FROM videos v LEFT JOIN articles a ON a.id = v.article_id LEFT JOIN categories c ON c.id = a.category_id WHERE v.id = %s",
                (vid_id,),
            )
            return dict(await cur.fetchone())


_ALLOWED_VIDEO_UPDATE_FIELDS = frozenset(
    {
        "status",
        "duration_sec",
        "thumbnail_url",
        "published_at",
        "description",
        "title",
        "style",
        "language",
    }
)


async def update_video(video_id: str, **kwargs) -> Optional[dict]:
    filtered = {k: v for k, v in kwargs.items() if k in _ALLOWED_VIDEO_UPDATE_FIELDS}
    if not _USE_MYSQL:
        async with _elearning_lock:
            if video_id not in _videos_store:
                return None
            if filtered:
                _videos_store[video_id].update(filtered)
                _videos_store[video_id]["updated_at"] = _now()
            return dict(_videos_store[video_id])

    set_clauses = []
    params = []
    for k, v in filtered.items():
        set_clauses.append(f"`{k}` = %s")
        params.append(v)
    if not set_clauses:
        return await get_video(video_id)
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")
    set_clauses.append("`updated_at` = %s")
    params.append(now_str)
    params.append(video_id)
    async with connection._pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(f"UPDATE videos SET {', '.join(set_clauses)} WHERE id = %s", params)
    return await get_video(video_id)


async def delete_video(video_id: str) -> bool:
    if not _USE_MYSQL:
        async with _elearning_lock:
            if video_id not in _videos_store:
                return False
            del _videos_store[video_id]
            _watch_history_store[:] = [h for h in _watch_history_store if h["video_id"] != video_id]
            _watch_later_store[:] = [w for w in _watch_later_store if w["video_id"] != video_id]
            _liked_videos_store[:] = [lv for lv in _liked_videos_store if lv["video_id"] != video_id]
            comment_ids = [cid for cid, c in _comments_store.items() if c.get("video_id") == video_id]
            for cid in comment_ids:
                del _comments_store[cid]
            dead = set(comment_ids)
            _comment_likes_store[:] = [lk for lk in _comment_likes_store if lk["comment_id"] not in dead]
            return True

    async with connection._pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM videos WHERE id = %s", (video_id,))
            return cur.rowcount > 0


async def get_video(video_id: str) -> Optional[dict]:
    if not _USE_MYSQL:
        async with _elearning_lock:
            vid = _videos_store.get(video_id)
            if not vid:
                return None
            result = dict(vid)
            art_id = vid.get("article_id")
            if art_id and art_id in _articles_store:
                result["article_git_path"] = _articles_store[art_id].get("git_path")
            return result

    async with connection._pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT v.*, c.id as category_id, c.name as category_name, c.slug as category_slug,
                       a.git_path as article_git_path
                FROM videos v
                LEFT JOIN articles a ON a.id = v.article_id
                LEFT JOIN categories c ON c.id = a.category_id
                WHERE v.id = %s
            """,
                (video_id,),
            )
            row = await cur.fetchone()
    return dict(row) if row else None


async def get_video_by_job_id(job_id: str) -> Optional[dict]:
    if not _USE_MYSQL:
        async with _elearning_lock:
            for vid in _videos_store.values():
                if vid.get("job_id") == job_id:
                    return dict(vid)
        return None

    async with connection._pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT * FROM videos WHERE job_id = %s", (job_id,))
            row = await cur.fetchone()
    return dict(row) if row else None


async def list_videos(
    category_slug: Optional[str] = None,
    search: Optional[str] = None,
    status: Optional[str] = "ready",
    limit: int = 50,
    offset: int = 0,
    user_id: Optional[str] = None,
    language: Optional[str] = None,
    published_after: Optional[str] = None,
) -> list[dict]:
    if not _USE_MYSQL:
        async with _elearning_lock:
            vids = list(_videos_store.values())
        if status:
            vids = [v for v in vids if v.get("status") == status]
        if language:
            vids = [v for v in vids if v.get("language", "ja") == language]
        if category_slug:
            vids = [v for v in vids if v.get("category_slug") == category_slug]
        if search:
            s = search.lower()
            vids = [
                v
                for v in vids
                if s in v.get("title", "").lower() or s in (v.get("description") or "").lower()
            ]
        if published_after:
            vids = [v for v in vids if (v.get("published_at") or v.get("created_at", "")) >= published_after]
        vids.sort(key=lambda v: v.get("published_at") or v.get("created_at", ""), reverse=True)
        vids = vids[offset : offset + limit]
        for v in vids:
            art_id = v.get("article_id")
            if art_id and art_id in _articles_store:
                v["article_git_path"] = _articles_store[art_id].get("git_path")
        if user_id:
            watched_ids = {h["video_id"] for h in _watch_history_store if h["user_id"] == user_id}
            for v in vids:
                v["watched"] = v["id"] in watched_ids
        return vids

    conditions = []
    params = []
    if status:
        conditions.append("v.status = %s")
        params.append(status)
    if language:
        conditions.append("v.language = %s")
        params.append(language)
    if category_slug:
        conditions.append("c.slug = %s")
        params.append(category_slug)
    if search:
        conditions.append("(v.title LIKE %s OR v.description LIKE %s)")
        params.extend([f"%{search}%", f"%{search}%"])
    if published_after:
        conditions.append("COALESCE(v.published_at, v.created_at) >= %s")
        params.append(published_after)

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    async with connection._pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"""
                SELECT v.*, c.id as category_id, c.name as category_name, c.slug as category_slug,
                       a.git_path as article_git_path
                FROM videos v
                LEFT JOIN articles a ON a.id = v.article_id
                LEFT JOIN categories c ON c.id = a.category_id
                {where}
                ORDER BY v.published_at DESC, v.created_at DESC
                LIMIT %s OFFSET %s
            """,
                params + [limit, offset],
            )
            rows = await cur.fetchall()

    result = [dict(r) for r in rows]
    if user_id:
        async with connection._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT video_id FROM watch_history WHERE user_id = %s", (user_id,))
                watched_rows = await cur.fetchall()
        watched_ids = {r["video_id"] for r in watched_rows}
        for v in result:
            v["watched"] = v["id"] in watched_ids
    return result
