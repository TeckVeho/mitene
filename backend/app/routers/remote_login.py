"""WebSocket endpoint for remote NotebookLM browser login.

Streams browser screenshots to the client and forwards mouse/keyboard
input so that end users can log in to Google from the deployed web UI.

Protocol (JSON over WebSocket):
  Server → Client:
    {"type": "screenshot", "data": "<base64 JPEG>"}
    {"type": "status", "status": "started"|"auth_saved"|"cancelled"|"error", "message": "..."}
    {"type": "viewport", "width": 1280, "height": 800}

  Client → Server:
    {"action": "click", "x": 100, "y": 200, "button": "left"}
    {"action": "mousemove", "x": 100, "y": 200}
    {"action": "type", "text": "hello"}
    {"action": "keypress", "key": "Enter"}
    {"action": "save"}
    {"action": "cancel"}
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Optional

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

import database
from app.config import _ADMIN_EMAILS_LOWER
from app.services.remote_browser import (
    VIEWPORT_HEIGHT,
    VIEWPORT_WIDTH,
    SCREENSHOT_INTERVAL,
    get_or_create_session,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["auth"])


async def _verify_admin_ws(user_id: Optional[str]) -> bool:
    """Verify that a user_id belongs to an admin (for WebSocket auth)."""
    if not user_id:
        return False
    user = await database.get_user(user_id)
    if not user:
        return False
    email = (user.get("email") or "").strip().lower()
    return bool(_ADMIN_EMAILS_LOWER and email in _ADMIN_EMAILS_LOWER)


@router.websocket("/api/auth/remote-login")
async def remote_login_ws(
    websocket: WebSocket,
    user_id: Optional[str] = Query(default=None),
):
    """WebSocket endpoint for remote browser-based NotebookLM login.

    Query params:
      user_id: The admin user ID (required for auth).
    """
    # Auth check
    if not await _verify_admin_ws(user_id):
        await websocket.close(code=4003, reason="Admin access required")
        return

    await websocket.accept()
    logger.info("Remote login WebSocket connected (user_id=%s)", user_id)

    session = await get_or_create_session()
    screenshot_task: Optional[asyncio.Task] = None

    try:
        # Start the browser session
        if not session.is_running:
            await websocket.send_json({"type": "status", "status": "starting", "message": "ブラウザを起動中..."})
            await session.start()

        # Send viewport info so client can scale events
        await websocket.send_json({
            "type": "viewport",
            "width": VIEWPORT_WIDTH,
            "height": VIEWPORT_HEIGHT,
        })

        await websocket.send_json({"type": "status", "status": "started", "message": "ブラウザが起動しました"})

        # Start screenshot streaming in background
        async def _stream_screenshots():
            try:
                while session.is_running:
                    try:
                        b64 = await session.get_screenshot()
                        await websocket.send_json({"type": "screenshot", "data": b64})
                    except RuntimeError:
                        break
                    except Exception as e:
                        logger.debug("Screenshot error (may be transient): %s", e)
                    await asyncio.sleep(SCREENSHOT_INTERVAL)
            except asyncio.CancelledError:
                pass

        screenshot_task = asyncio.create_task(_stream_screenshots())

        # Listen for client input events
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            action = msg.get("action")
            if not action:
                continue

            if action == "click":
                x = float(msg.get("x", 0))
                y = float(msg.get("y", 0))
                button = msg.get("button", "left")
                await session.send_mouse_click(x, y, button=button)

            elif action == "mousemove":
                x = float(msg.get("x", 0))
                y = float(msg.get("y", 0))
                await session.send_mouse_move(x, y)

            elif action == "type":
                text = msg.get("text", "")
                if text:
                    await session.send_keyboard_type(text)

            elif action == "keypress":
                key = msg.get("key", "")
                if key:
                    await session.send_keyboard_press(key)

            elif action == "save":
                if screenshot_task:
                    screenshot_task.cancel()
                await websocket.send_json({
                    "type": "status",
                    "status": "saving",
                    "message": "認証情報を保存中...",
                })
                try:
                    path = await session.save_and_close()
                    await websocket.send_json({
                        "type": "status",
                        "status": "auth_saved",
                        "message": f"認証情報を保存しました: {path}",
                    })
                except Exception as e:
                    await websocket.send_json({
                        "type": "status",
                        "status": "error",
                        "message": f"保存に失敗しました: {e}",
                    })
                break

            elif action == "cancel":
                if screenshot_task:
                    screenshot_task.cancel()
                await session.cancel()
                await websocket.send_json({
                    "type": "status",
                    "status": "cancelled",
                    "message": "セッションをキャンセルしました",
                })
                break

    except WebSocketDisconnect:
        logger.info("Remote login WebSocket disconnected")
        if session.is_running:
            await session.cancel()
    except Exception as e:
        logger.error("Remote login WebSocket error: %s", e, exc_info=True)
        try:
            await websocket.send_json({
                "type": "status",
                "status": "error",
                "message": f"エラーが発生しました: {e}",
            })
        except Exception:
            pass
        if session.is_running:
            await session.cancel()
    finally:
        if screenshot_task and not screenshot_task.done():
            screenshot_task.cancel()
            try:
                await screenshot_task
            except asyncio.CancelledError:
                pass
