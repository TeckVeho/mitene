"""Comments CRUD."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from . import connection
from .connection import (
    _USE_MYSQL,
    _comment_likes_store,
    _comments_store,
    _elearning_lock,
    _now,
    _users_store,
)
from .videos import get_video


async def list_comments_for_video(video_id: str, viewer_user_id: Optional[str] = None) -> list[dict]:
    """トップレベルコメントのリスト。各要素に replies（ネスト）を含む。API 用 camelCase キー。"""
    if not _USE_MYSQL:
        async with _elearning_lock:
            rows = [dict(c) for c in _comments_store.values() if c["video_id"] == video_id]
        rows.sort(key=lambda c: c.get("created_at") or "")
        if not rows:
            return []
        comment_ids = [r["id"] for r in rows]
        counts: dict[str, int] = {cid: 0 for cid in comment_ids}
        liked: set[str] = set()
        for lk in _comment_likes_store:
            cid = lk["comment_id"]
            if cid in counts:
                counts[cid] += 1
                if viewer_user_id and lk["user_id"] == viewer_user_id:
                    liked.add(cid)
        nodes: dict[str, dict] = {}
        for r in rows:
            uid = r["user_id"]
            user = _users_store.get(uid) or {}
            dn = user.get("display_name") or user.get("displayName") or "Unknown"
            cid = r["id"]
            nodes[cid] = {
                "id": cid,
                "videoId": video_id,
                "userId": uid,
                "displayName": dn,
                "text": r["text"],
                "likeCount": counts.get(cid, 0),
                "likedByMe": cid in liked,
                "createdAt": str(r.get("created_at", "")),
                "parentId": r.get("parent_id"),
                "replies": [],
            }
        roots: list[dict] = []
        for r in rows:
            cid = r["id"]
            pid = r.get("parent_id")
            if pid and pid in nodes:
                nodes[pid]["replies"].append(nodes[cid])
            else:
                roots.append(nodes[cid])
        return roots

    async with connection._pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT c.id, c.video_id, c.user_id, c.parent_id, c.text, c.created_at, u.display_name
                FROM comments c
                JOIN users u ON u.id = c.user_id
                WHERE c.video_id = %s
                ORDER BY c.created_at ASC
                """,
                (video_id,),
            )
            rows = await cur.fetchall()
    if not rows:
        return []
    rows = [dict(r) for r in rows]
    comment_ids = [r["id"] for r in rows]
    counts = {cid: 0 for cid in comment_ids}
    liked: set[str] = set()
    async with connection._pool.acquire() as conn:
        async with conn.cursor() as cur:
            ph = ",".join(["%s"] * len(comment_ids))
            await cur.execute(
                f"SELECT comment_id, user_id FROM comment_likes WHERE comment_id IN ({ph})",
                comment_ids,
            )
            for lr in await cur.fetchall():
                cid = lr["comment_id"]
                if cid in counts:
                    counts[cid] += 1
                    if viewer_user_id and lr["user_id"] == viewer_user_id:
                        liked.add(cid)
    nodes: dict[str, dict] = {}
    for r in rows:
        cid = r["id"]
        dn = r.get("display_name") or "Unknown"
        nodes[cid] = {
            "id": cid,
            "videoId": r["video_id"],
            "userId": r["user_id"],
            "displayName": dn,
            "text": r["text"],
            "likeCount": counts.get(cid, 0),
            "likedByMe": cid in liked,
            "createdAt": str(r.get("created_at", "")),
            "parentId": r.get("parent_id"),
            "replies": [],
        }
    roots = []
    for r in rows:
        cid = r["id"]
        pid = r.get("parent_id")
        if pid and pid in nodes:
            nodes[pid]["replies"].append(nodes[cid])
        else:
            roots.append(nodes[cid])
    return roots


async def create_comment(
    video_id: str, user_id: str, text: str, parent_id: Optional[str] = None
) -> Optional[dict]:
    text = (text or "").strip()
    if not text or len(text) > 8000:
        return None
    video = await get_video(video_id)
    if not video:
        return None
    if parent_id:
        if not _USE_MYSQL:
            async with _elearning_lock:
                parent = _comments_store.get(parent_id)
            if not parent or parent.get("video_id") != video_id:
                return None
        else:
            async with connection._pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        "SELECT video_id FROM comments WHERE id = %s",
                        (parent_id,),
                    )
                    prow = await cur.fetchone()
            if not prow or prow["video_id"] != video_id:
                return None
    cid = str(uuid.uuid4())
    now = _now()
    if not _USE_MYSQL:
        async with _elearning_lock:
            if user_id not in _users_store:
                return None
            user = dict(_users_store[user_id])
            _comments_store[cid] = {
                "id": cid,
                "video_id": video_id,
                "user_id": user_id,
                "parent_id": parent_id,
                "text": text,
                "created_at": now,
            }
            dn = user.get("display_name") or user.get("displayName") or ""
        like_c = sum(1 for lk in _comment_likes_store if lk["comment_id"] == cid)
        return {
            "id": cid,
            "videoId": video_id,
            "userId": user_id,
            "displayName": dn,
            "text": text,
            "likeCount": like_c,
            "likedByMe": False,
            "createdAt": now,
            "parentId": parent_id,
            "replies": [],
        }

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")
    async with connection._pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT id FROM users WHERE id = %s", (user_id,))
            if not await cur.fetchone():
                return None
            await cur.execute(
                """
                INSERT INTO comments (id, video_id, user_id, parent_id, text, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (cid, video_id, user_id, parent_id, text, now_str),
            )
            await cur.execute("SELECT display_name FROM users WHERE id = %s", (user_id,))
            urow = await cur.fetchone()
    dn = urow["display_name"] if urow else ""
    return {
        "id": cid,
        "videoId": video_id,
        "userId": user_id,
        "displayName": dn,
        "text": text,
        "likeCount": 0,
        "likedByMe": False,
        "createdAt": now_str,
        "parentId": parent_id,
        "replies": [],
    }


async def get_comment_row(comment_id: str) -> Optional[dict]:
    if not _USE_MYSQL:
        async with _elearning_lock:
            return dict(_comments_store[comment_id]) if comment_id in _comments_store else None
    async with connection._pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT c.*, u.display_name
                FROM comments c JOIN users u ON u.id = c.user_id
                WHERE c.id = %s
                """,
                (comment_id,),
            )
            row = await cur.fetchone()
    return dict(row) if row else None


async def comment_to_api_dict(comment_id: str, viewer_user_id: Optional[str]) -> Optional[dict]:
    row = await get_comment_row(comment_id)
    if not row:
        return None
    vid = row["video_id"]
    uid = row["user_id"]
    dn = row.get("display_name") or "Unknown"
    if not _USE_MYSQL:
        like_c = sum(1 for lk in _comment_likes_store if lk["comment_id"] == comment_id)
        liked = bool(
            viewer_user_id
            and any(
                lk["comment_id"] == comment_id and lk["user_id"] == viewer_user_id
                for lk in _comment_likes_store
            )
        )
    else:
        async with connection._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT COUNT(*) as c FROM comment_likes WHERE comment_id = %s",
                    (comment_id,),
                )
                crow = await cur.fetchone()
                like_c = int(crow["c"]) if crow else 0
                liked = False
                if viewer_user_id:
                    await cur.execute(
                        "SELECT 1 FROM comment_likes WHERE comment_id = %s AND user_id = %s LIMIT 1",
                        (comment_id, viewer_user_id),
                    )
                    liked = await cur.fetchone() is not None
    return {
        "id": comment_id,
        "videoId": vid,
        "userId": uid,
        "displayName": dn,
        "text": row["text"],
        "likeCount": like_c,
        "likedByMe": liked,
        "createdAt": str(row.get("created_at", "")),
        "parentId": row.get("parent_id"),
        "replies": [],
    }


async def toggle_comment_like(comment_id: str, user_id: str) -> Optional[dict]:
    row = await get_comment_row(comment_id)
    if not row:
        return None
    if not _USE_MYSQL:
        async with _elearning_lock:
            existing = next(
                (
                    lk
                    for lk in _comment_likes_store
                    if lk["comment_id"] == comment_id and lk["user_id"] == user_id
                ),
                None,
            )
            if existing:
                _comment_likes_store.remove(existing)
            else:
                _comment_likes_store.append(
                    {
                        "id": str(uuid.uuid4()),
                        "comment_id": comment_id,
                        "user_id": user_id,
                        "created_at": _now(),
                    }
                )
    else:
        async with connection._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT id FROM comment_likes WHERE comment_id = %s AND user_id = %s",
                    (comment_id, user_id),
                )
                ex = await cur.fetchone()
                if ex:
                    await cur.execute(
                        "DELETE FROM comment_likes WHERE comment_id = %s AND user_id = %s",
                        (comment_id, user_id),
                    )
                else:
                    lid = str(uuid.uuid4())
                    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")
                    await cur.execute(
                        """
                        INSERT INTO comment_likes (id, comment_id, user_id, created_at)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (lid, comment_id, user_id, now_str),
                    )
    return await comment_to_api_dict(comment_id, user_id)
