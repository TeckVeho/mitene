"""Articles CRUD."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from . import connection
from .connection import (
    _USE_MYSQL,
    _articles_store,
    _categories_store,
    _elearning_lock,
    _now,
    _videos_store,
)


async def upsert_article(
    git_path: str,
    title: str,
    content_md: str,
    git_hash: str,
    category_id: Optional[str] = None,
) -> dict:
    if not _USE_MYSQL:
        async with _elearning_lock:
            for art in _articles_store.values():
                if art["git_path"] == git_path:
                    art.update(
                        {
                            "title": title,
                            "content_md": content_md,
                            "git_hash": git_hash,
                            "category_id": category_id,
                            "updated_at": _now(),
                        }
                    )
                    return dict(art)
            art_id = f"art_{uuid.uuid4().hex[:8]}"
            new_art = {
                "id": art_id,
                "title": title,
                "content_md": content_md,
                "git_path": git_path,
                "git_hash": git_hash,
                "category_id": category_id,
                "created_at": _now(),
                "updated_at": _now(),
            }
            _articles_store[art_id] = new_art
            return dict(new_art)

    async with connection._pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT * FROM articles WHERE git_path = %s", (git_path,))
            existing = await cur.fetchone()
            now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")
            if existing:
                await cur.execute(
                    "UPDATE articles SET title=%s, content_md=%s, git_hash=%s, category_id=%s, updated_at=%s WHERE git_path=%s",
                    (title, content_md, git_hash, category_id, now_str, git_path),
                )
                await cur.execute("SELECT * FROM articles WHERE git_path = %s", (git_path,))
                return dict(await cur.fetchone())
            art_id = str(uuid.uuid4())
            await cur.execute(
                "INSERT INTO articles (id, title, content_md, git_path, git_hash, category_id, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (art_id, title, content_md, git_path, git_hash, category_id, now_str, now_str),
            )
            await cur.execute("SELECT * FROM articles WHERE id = %s", (art_id,))
            return dict(await cur.fetchone())


async def get_article_by_git_path(git_path: str) -> Optional[dict]:
    if not _USE_MYSQL:
        async with _elearning_lock:
            for art in _articles_store.values():
                if art["git_path"] == git_path:
                    return dict(art)
        return None

    async with connection._pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT * FROM articles WHERE git_path = %s", (git_path,))
            row = await cur.fetchone()
    return dict(row) if row else None


async def list_articles() -> list[dict]:
    if not _USE_MYSQL:
        async with _elearning_lock:
            arts = sorted(_articles_store.values(), key=lambda a: a.get("updated_at", ""), reverse=True)
        result = []
        for art in arts:
            cat = _categories_store.get(art.get("category_id", "")) if art.get("category_id") else None
            vid_list = [v for v in _videos_store.values() if v.get("article_id") == art["id"]]
            latest_video = (
                sorted(vid_list, key=lambda v: v.get("created_at", ""), reverse=True)[0] if vid_list else None
            )
            result.append(
                {
                    **art,
                    "categoryName": cat["name"] if cat else None,
                    "latestVideoId": latest_video["id"] if latest_video else None,
                    "latestVideoStatus": latest_video["status"] if latest_video else None,
                }
            )
        return result

    async with connection._pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT a.*, c.name as category_name,
                       (SELECT v.id FROM videos v WHERE v.article_id = a.id ORDER BY v.created_at DESC LIMIT 1) as latest_video_id,
                       (SELECT v.status FROM videos v WHERE v.article_id = a.id ORDER BY v.created_at DESC LIMIT 1) as latest_video_status
                FROM articles a
                LEFT JOIN categories c ON c.id = a.category_id
                ORDER BY a.updated_at DESC
            """
            )
            rows = await cur.fetchall()
    return [dict(r) for r in rows]
