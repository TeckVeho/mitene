"""NotebookLM + GitHub OAuth routes."""

from __future__ import annotations

import os
import subprocess
from typing import Annotated, Optional

import httpx
from fastapi import APIRouter, Cookie, Depends, HTTPException
from fastapi.responses import RedirectResponse
from urllib.parse import urlencode

import database
import json
from app.config import FRONTEND_URL, GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET, STORAGE_STATE
from app.dependencies import require_admin_user
from app.schemas.auth import AuthStatus, LoginResponse, UploadSessionRequest
from app.services.notebooklm_auth import check_auth_status_strict, find_notebooklm
from app.services.notebooklm_gcs import upload_storage_state_if_configured
from app.services.oauth import allowed_oauth_frontends, oauth_state_decode, oauth_state_encode, resolve_oauth_frontend

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/status", response_model=AuthStatus)
async def get_auth_status(_admin: Annotated[dict, Depends(require_admin_user)]):
    return AuthStatus(status=await check_auth_status_strict())


@router.post("/login", response_model=LoginResponse)
async def trigger_login(_admin: Annotated[dict, Depends(require_admin_user)]):
    try:
        notebooklm_cmd = find_notebooklm()
        env = os.environ.copy()
        subprocess.Popen(
            [notebooklm_cmd, "login"],
            env=env,
            start_new_session=True,
        )
        return LoginResponse(message="ログインブラウザを開きました。認証後しばらくお待ちください。")
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ログイン起動に失敗しました: {e}")


@router.post("/upload-session", response_model=LoginResponse)
async def upload_session(
    payload: UploadSessionRequest,
    _admin: Annotated[dict, Depends(require_admin_user)]
):
    """Save manual Cookie-Editor JSON to Playwright storage_state and upload to GCS."""
    try:
        raw_data = json.loads(payload.session_json)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format.")

    if not isinstance(raw_data, list):
        raise HTTPException(status_code=400, detail="Expected a JSON array of cookies from Cookie-Editor.")

    converted_cookies = []
    for c in raw_data:
        if not isinstance(c, dict):
            continue
        same_site_raw = (c.get("sameSite") or "").lower()
        if same_site_raw in ["no_restriction", "none"]:
            same_site = "None"
        elif same_site_raw == "strict":
            same_site = "Strict"
        else:
            same_site = "Lax"

        expires = c.get("expirationDate", -1)
        if expires is None:
            expires = -1

        converted = {
            "name": c.get("name") or "",
            "value": c.get("value") or "",
            "domain": c.get("domain") or "",
            "path": c.get("path") or "/",
            "expires": expires,
            "httpOnly": bool(c.get("httpOnly")),
            "secure": bool(c.get("secure")),
            "sameSite": same_site
        }
        if converted["name"] and converted["value"]:
            converted_cookies.append(converted)

    if not converted_cookies:
        raise HTTPException(status_code=400, detail="No valid cookies found in the provided JSON.")

    playwright_state = {
        "cookies": converted_cookies,
        "origins": []
    }

    try:
        STORAGE_STATE.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with open(STORAGE_STATE, "w", encoding="utf-8") as f:
            json.dump(playwright_state, f, indent=2)
        STORAGE_STATE.chmod(0o600)

        upload_storage_state_if_configured()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save storage state: {e}")

    return LoginResponse(message="認証情報を保存しました。")



@router.get("/github")
async def github_oauth_start(frontend_base: Optional[str] = None):
    """GitHub OAuth を開始。別タブで開く想定。"""
    if not GITHUB_CLIENT_ID:
        raise HTTPException(
            status_code=500,
            detail="GITHUB_CLIENT_ID が設定されていません。.env に設定してください。",
        )
    base_url = os.environ.get("API_BASE_URL", "http://localhost:8000")
    redirect_uri = f"{base_url}/api/auth/github/callback"
    fb = resolve_oauth_frontend(frontend_base)
    oauth_state = oauth_state_encode(fb)
    params = {
        "client_id": GITHUB_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "scope": "user:email read:user",
        "state": oauth_state,
    }
    return RedirectResponse(
        url=f"https://github.com/login/oauth/authorize?{urlencode(params)}",
        status_code=302,
    )


@router.get("/github/callback")
async def github_oauth_callback(
    code: Optional[str] = None,
    error: Optional[str] = None,
    state: Optional[str] = None,
):
    """GitHub OAuth コールバック。トークン交換後、フロントエンドにリダイレクト。"""

    def _redirect_front() -> str:
        fb = oauth_state_decode(state)
        if fb and fb in allowed_oauth_frontends():
            return fb
        return FRONTEND_URL.rstrip("/")

    if error:
        front = _redirect_front()
        return RedirectResponse(
            url=f"{front}/login?error={error}",
            status_code=302,
        )
    if not code:
        raise HTTPException(status_code=400, detail="認証コードがありません")
    if not GITHUB_CLIENT_ID or not GITHUB_CLIENT_SECRET:
        raise HTTPException(
            status_code=500,
            detail="GITHUB_CLIENT_ID / GITHUB_CLIENT_SECRET が設定されていません。",
        )

    async with httpx.AsyncClient() as client:
        token_res = await client.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            data={
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "code": code,
            },
        )
        token_res.raise_for_status()
        token_data = token_res.json()
        access_token = token_data.get("access_token")
        if not access_token:
            front = _redirect_front()
            return RedirectResponse(
                url=f"{front}/login?error=access_denied",
                status_code=302,
            )

        user_res = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        user_res.raise_for_status()
        gh_user = user_res.json()

        email = gh_user.get("email")
        if not email:
            em_res = await client.get(
                "https://api.github.com/user/emails",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if em_res.status_code == 200:
                emails = em_res.json()
                primary = next((e for e in emails if e.get("primary")), emails[0] if emails else None)
                if primary:
                    email = primary.get("email", "")
        if not email:
            email = f"{gh_user.get('id', '')}@users.noreply.github.com"

        display_name = gh_user.get("name") or gh_user.get("login") or "GitHub User"

    user = await database.get_or_create_user(email, display_name)

    front = _redirect_front()
    q = urlencode(
        {
            "user_id": user["id"],
            "email": user["email"],
            "display_name": user.get("display_name", user.get("displayName", display_name)),
        }
    )
    target = f"{front}/login/callback?{q}"
    response = RedirectResponse(url=target, status_code=302)
    response.set_cookie(
        key="user_id",
        value=user["id"],
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 30,
        path="/",
    )
    return response
