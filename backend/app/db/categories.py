"""Categories CRUD."""

from __future__ import annotations

import uuid
from typing import Optional

from . import connection
from .connection import (
    _USE_MYSQL,
    _categories_store,
    _elearning_lock,
    _now,
    _videos_store,
)


async def get_categories(language: Optional[str] = None) -> list[dict]:
    if not _USE_MYSQL:
        async with _elearning_lock:
            cats = sorted(_categories_store.values(), key=lambda c: c.get("sort_order", 0))
        result = []
        for cat in cats:
            video_count = sum(
                1
                for v in _videos_store.values()
                if v.get("category_id") == cat["id"]
                and v.get("status") == "ready"
                and (language is None or v.get("language", "ja") == language)
            )
            result.append({**cat, "videoCount": video_count})
        return result

    lang_filter = " AND v.language = %s" if language else ""
    params = [language] if language else []

    async with connection._pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"""
                SELECT c.*, COUNT(v.id) as video_count
                FROM categories c
                LEFT JOIN articles a ON a.category_id = c.id
                LEFT JOIN videos v ON v.article_id = a.id AND v.status = 'ready'{lang_filter}
                GROUP BY c.id
                ORDER BY c.sort_order ASC
                """,
                tuple(params) if params else (),
            )
            rows = await cur.fetchall()

    return [
        {
            "id": r["id"],
            "name": r["name"],
            "slug": r["slug"],
            "description": r.get("description"),
            "sortOrder": r.get("sort_order", 0),
            "videoCount": r.get("video_count", 0),
            "createdAt": str(r.get("created_at", "")),
        }
        for r in rows
    ]


async def get_category_by_slug(slug: str) -> Optional[dict]:
    if not _USE_MYSQL:
        async with _elearning_lock:
            for cat in _categories_store.values():
                if cat["slug"] == slug:
                    return dict(cat)
        return None

    async with connection._pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT * FROM categories WHERE slug = %s", (slug,))
            row = await cur.fetchone()
    return row


async def upsert_category(slug: str, name: str, description: Optional[str] = None) -> dict:
    if not _USE_MYSQL:
        async with _elearning_lock:
            for cat in _categories_store.values():
                if cat["slug"] == slug:
                    return dict(cat)
            cat_id = f"cat_{uuid.uuid4().hex[:8]}"
            sort_order = len(_categories_store) + 1
            new_cat = {
                "id": cat_id,
                "name": name,
                "slug": slug,
                "description": description,
                "sort_order": sort_order,
                "created_at": _now(),
            }
            _categories_store[cat_id] = new_cat
            return dict(new_cat)

    async with connection._pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT * FROM categories WHERE slug = %s", (slug,))
            existing = await cur.fetchone()
            if existing:
                return dict(existing)
            cat_id = str(uuid.uuid4())
            sort_order_q = "SELECT COALESCE(MAX(sort_order), 0) + 1 as next_order FROM categories"
            await cur.execute(sort_order_q)
            sort_row = await cur.fetchone()
            sort_order = sort_row["next_order"] if sort_row else 1
            await cur.execute(
                "INSERT INTO categories (id, name, slug, description, sort_order) VALUES (%s, %s, %s, %s, %s)",
                (cat_id, name, slug, description, sort_order),
            )
            await cur.execute("SELECT * FROM categories WHERE id = %s", (cat_id,))
            return dict(await cur.fetchone())
