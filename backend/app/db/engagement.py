"""Watch history, watch-later, liked videos."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from . import connection
from .connection import (
    _USE_MYSQL,
    _elearning_lock,
    _liked_videos_store,
    _now,
    _videos_store,
    _watch_history_store,
    _watch_later_store,
)


async def record_watch(user_id: str, video_id: str, completed: bool = True) -> dict:
    if not _USE_MYSQL:
        async with _elearning_lock:
            for record in _watch_history_store:
                if record["user_id"] == user_id and record["video_id"] == video_id:
                    record["completed"] = completed
                    record["watched_at"] = _now()
                    return dict(record)
            record_id = str(uuid.uuid4())
            new_record = {
                "id": record_id,
                "user_id": user_id,
                "video_id": video_id,
                "completed": completed,
                "watched_at": _now(),
            }
            _watch_history_store.append(new_record)
            return dict(new_record)

    record_id = str(uuid.uuid4())
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")
    async with connection._pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """INSERT INTO watch_history (id, user_id, video_id, completed, watched_at) VALUES (%s, %s, %s, %s, %s)
                   ON DUPLICATE KEY UPDATE completed = %s, watched_at = %s""",
                (record_id, user_id, video_id, completed, now_str, completed, now_str),
            )
    return {
        "id": record_id,
        "user_id": user_id,
        "video_id": video_id,
        "completed": completed,
        "watched_at": now_str,
    }


async def get_watch_history(user_id: str, limit: int = 50) -> list[dict]:
    if not _USE_MYSQL:
        async with _elearning_lock:
            history = [h for h in _watch_history_store if h["user_id"] == user_id]
        history.sort(key=lambda h: h["watched_at"], reverse=True)
        history = history[:limit]
        result = []
        for h in history:
            vid = _videos_store.get(h["video_id"])
            if vid:
                result.append(
                    {
                        **h,
                        "videoTitle": vid["title"],
                        "videoStatus": vid["status"],
                        "categoryName": vid.get("category_name"),
                        "categorySlug": vid.get("category_slug"),
                    }
                )
        return result

    async with connection._pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT wh.*, v.title as video_title, v.status as video_status,
                       c.name as category_name, c.slug as category_slug
                FROM watch_history wh
                JOIN videos v ON v.id = wh.video_id
                LEFT JOIN articles a ON a.id = v.article_id
                LEFT JOIN categories c ON c.id = a.category_id
                WHERE wh.user_id = %s
                ORDER BY wh.watched_at DESC
                LIMIT %s
                """,
                (user_id, limit),
            )
            rows = await cur.fetchall()
    return [dict(r) for r in rows]


async def get_video_watch_counts(video_id: str) -> tuple[int, int]:
    """動画の視聴者数（ユニークユーザー数）と視聴回数を返す"""
    if not _USE_MYSQL:
        async with _elearning_lock:
            records = [h for h in _watch_history_store if h["video_id"] == video_id]
        count = len(records)
        return (count, count)

    async with connection._pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT COUNT(*) as cnt FROM watch_history WHERE video_id = %s",
                (video_id,),
            )
            row = await cur.fetchone()
    cnt = row["cnt"] if row else 0
    return (cnt, cnt)


async def get_video_watch_counts_batch(video_ids: list[str]) -> dict[str, tuple[int, int]]:
    """複数動画の視聴者数・視聴回数（get_video_watch_counts と同じ定義）を一括取得"""
    if not video_ids:
        return {}
    if not _USE_MYSQL:
        wanted = set(video_ids)
        counts: dict[str, int] = {}
        async with _elearning_lock:
            for h in _watch_history_store:
                vid = h["video_id"]
                if vid in wanted:
                    counts[vid] = counts.get(vid, 0) + 1
        return {vid: (c, c) for vid, c in counts.items()}

    placeholders = ",".join(["%s"] * len(video_ids))
    async with connection._pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"""
                SELECT video_id, COUNT(*) AS cnt
                FROM watch_history
                WHERE video_id IN ({placeholders})
                GROUP BY video_id
                """,
                video_ids,
            )
            rows = await cur.fetchall()
    out: dict[str, tuple[int, int]] = {}
    for r in rows:
        cnt = int(r["cnt"])
        vid = r["video_id"]
        out[vid] = (cnt, cnt)
    return out


async def toggle_watch_later(user_id: str, video_id: str) -> bool:
    """後で見るをトグル。追加ならTrue、削除ならFalseを返す"""
    if not _USE_MYSQL:
        async with _elearning_lock:
            existing = next(
                (r for r in _watch_later_store if r["user_id"] == user_id and r["video_id"] == video_id),
                None,
            )
            if existing:
                _watch_later_store.remove(existing)
                return False
            _watch_later_store.append(
                {
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "video_id": video_id,
                    "created_at": _now(),
                }
            )
            return True

    async with connection._pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT id FROM watch_later WHERE user_id = %s AND video_id = %s", (user_id, video_id))
            row = await cur.fetchone()
            if row:
                await cur.execute("DELETE FROM watch_later WHERE user_id = %s AND video_id = %s", (user_id, video_id))
                return False
            record_id = str(uuid.uuid4())
            now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")
            await cur.execute(
                "INSERT INTO watch_later (id, user_id, video_id, created_at) VALUES (%s, %s, %s, %s)",
                (record_id, user_id, video_id, now_str),
            )
            return True


async def get_watch_later_ids(user_id: str) -> set[str]:
    if not _USE_MYSQL:
        async with _elearning_lock:
            return {r["video_id"] for r in _watch_later_store if r["user_id"] == user_id}

    async with connection._pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT video_id FROM watch_later WHERE user_id = %s", (user_id,))
            rows = await cur.fetchall()
    return {r["video_id"] for r in rows}


async def get_watch_later_videos(user_id: str, limit: int = 100) -> list[dict]:
    if not _USE_MYSQL:
        async with _elearning_lock:
            wl = [r for r in _watch_later_store if r["user_id"] == user_id]
            wl.sort(key=lambda r: r["created_at"], reverse=True)
            result = []
            for r in wl[:limit]:
                vid = _videos_store.get(r["video_id"])
                if vid:
                    vid_copy = dict(vid)
                    vid_copy["watch_later_at"] = r["created_at"]
                    result.append(vid_copy)
            return result

    async with connection._pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT v.*, c.id as category_id, c.name as category_name, c.slug as category_slug,
                       a.git_path as article_git_path, wl.created_at as watch_later_at
                FROM watch_later wl
                JOIN videos v ON v.id = wl.video_id
                LEFT JOIN articles a ON a.id = v.article_id
                LEFT JOIN categories c ON c.id = a.category_id
                WHERE wl.user_id = %s
                ORDER BY wl.created_at DESC
                LIMIT %s
                """,
                (user_id, limit),
            )
            rows = await cur.fetchall()
    return [dict(r) for r in rows]


async def toggle_liked_video(user_id: str, video_id: str) -> bool:
    """高く評価をトグル。追加ならTrue、削除ならFalseを返す"""
    if not _USE_MYSQL:
        async with _elearning_lock:
            existing = next(
                (r for r in _liked_videos_store if r["user_id"] == user_id and r["video_id"] == video_id),
                None,
            )
            if existing:
                _liked_videos_store.remove(existing)
                return False
            _liked_videos_store.append(
                {
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "video_id": video_id,
                    "created_at": _now(),
                }
            )
            return True

    async with connection._pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT id FROM liked_videos WHERE user_id = %s AND video_id = %s", (user_id, video_id))
            row = await cur.fetchone()
            if row:
                await cur.execute("DELETE FROM liked_videos WHERE user_id = %s AND video_id = %s", (user_id, video_id))
                return False
            record_id = str(uuid.uuid4())
            now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")
            await cur.execute(
                "INSERT INTO liked_videos (id, user_id, video_id, created_at) VALUES (%s, %s, %s, %s)",
                (record_id, user_id, video_id, now_str),
            )
            return True


async def get_liked_video_ids(user_id: str) -> set[str]:
    if not _USE_MYSQL:
        async with _elearning_lock:
            return {r["video_id"] for r in _liked_videos_store if r["user_id"] == user_id}

    async with connection._pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT video_id FROM liked_videos WHERE user_id = %s", (user_id,))
            rows = await cur.fetchall()
    return {r["video_id"] for r in rows}


async def get_liked_videos(user_id: str, limit: int = 100) -> list[dict]:
    if not _USE_MYSQL:
        async with _elearning_lock:
            liked = [r for r in _liked_videos_store if r["user_id"] == user_id]
            liked.sort(key=lambda r: r["created_at"], reverse=True)
            result = []
            for r in liked[:limit]:
                vid = _videos_store.get(r["video_id"])
                if vid:
                    result.append(dict(vid))
            return result

    async with connection._pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT v.*, c.id as category_id, c.name as category_name, c.slug as category_slug,
                       a.git_path as article_git_path
                FROM liked_videos lv
                JOIN videos v ON v.id = lv.video_id
                LEFT JOIN articles a ON a.id = v.article_id
                LEFT JOIN categories c ON c.id = a.category_id
                WHERE lv.user_id = %s
                ORDER BY lv.created_at DESC
                LIMIT %s
                """,
                (user_id, limit),
            )
            rows = await cur.fetchall()
    return [dict(r) for r in rows]
