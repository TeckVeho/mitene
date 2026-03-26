"""Users CRUD."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from . import connection
from .connection import _USE_MYSQL, _elearning_lock, _now, _users_store


async def get_or_create_user(email: str, display_name: str) -> dict:
    if not _USE_MYSQL:
        async with _elearning_lock:
            for user in _users_store.values():
                if user["email"] == email:
                    return dict(user)
            user_id = str(uuid.uuid4())
            new_user = {
                "id": user_id,
                "email": email,
                "display_name": display_name,
                "created_at": _now(),
            }
            _users_store[user_id] = new_user
            return dict(new_user)

    async with connection._pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT * FROM users WHERE email = %s", (email,))
            existing = await cur.fetchone()
            if existing:
                return dict(existing)
            user_id = str(uuid.uuid4())
            now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")
            await cur.execute(
                "INSERT INTO users (id, email, display_name, created_at) VALUES (%s, %s, %s, %s)",
                (user_id, email, display_name, now_str),
            )
            await cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            return dict(await cur.fetchone())


async def get_user(user_id: str) -> Optional[dict]:
    if not _USE_MYSQL:
        async with _elearning_lock:
            return dict(_users_store[user_id]) if user_id in _users_store else None

    async with connection._pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            row = await cur.fetchone()
    return dict(row) if row else None
