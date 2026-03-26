"""Shared FastAPI dependencies."""

from __future__ import annotations

from typing import Optional

from fastapi import Cookie, Header, HTTPException

import database

from app.config import _ADMIN_EMAILS_LOWER


def is_admin_email(email: Optional[str]) -> bool:
    if not email or not _ADMIN_EMAILS_LOWER:
        return False
    return email.strip().lower() in _ADMIN_EMAILS_LOWER


async def require_admin_user(
    x_user_id: Optional[str] = Header(default=None),
    user_id: Optional[str] = Cookie(default=None),
) -> dict:
    uid = x_user_id or user_id
    if not uid:
        raise HTTPException(status_code=401, detail="ログインが必要です")
    user = await database.get_user(uid)
    if not user:
        raise HTTPException(status_code=401, detail="ユーザーが見つかりません")
    em = user.get("email") or ""
    if not is_admin_email(em):
        raise HTTPException(status_code=403, detail="管理権限がありません")
    return user
