"""
E-learning バックエンド API
社内Wikiの .md ファイルを NotebookLM で動画化し、エンジニアが視聴できるシステム

ストレージ:
  - DATABASE_URL 環境変数が設定されている場合: MySQL（RDS）
  - 未設定の場合: インメモリ（開発用）
  - S3_BUCKET_NAME 環境変数が設定されている場合: AWS S3 にファイル保存
  - 未設定の場合: ローカルファイルシステム（開発用）
"""

import asyncio
import base64
import json
import logging
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path as _Path

from dotenv import load_dotenv
load_dotenv(_Path(__file__).parent / ".env")
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, List, Optional

from fastapi import BackgroundTasks, Depends, FastAPI, File, Form, HTTPException, UploadFile, Cookie, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse, Response, StreamingResponse
from pydantic import BaseModel, Field

import database
import storage
from runner import run_job
from api_v1 import router as v1_router, register_store_functions

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logging.getLogger("notebooklm").setLevel(logging.DEBUG)

# ---------------------------------------------------------------------------
# Paths（ローカルストレージモード時に使用）
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).parent
UPLOADS_DIR = BASE_DIR / "uploads"
OUTPUTS_DIR = BASE_DIR / "outputs"
UPLOADS_DIR.mkdir(exist_ok=True)
OUTPUTS_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


class JobStepInfo(BaseModel):
    id: str
    label: str
    status: str
    message: Optional[str] = None


class Job(BaseModel):
    id: str
    jobType: str = "video"
    csvFileNames: str
    notebookTitle: str
    instructions: str
    style: Optional[str] = None
    format: Optional[str] = None
    language: str
    timeout: int
    status: str
    steps: list[JobStepInfo]
    currentStep: Optional[str] = None
    errorMessage: Optional[str] = None
    createdAt: str
    updatedAt: str
    completedAt: Optional[str] = None
    callbackUrl: Optional[str] = None


class JobStats(BaseModel):
    total: int
    processing: int
    completed: int
    error: int


class AuthStatus(BaseModel):
    status: str


class LoginResponse(BaseModel):
    message: str


class VideoResponse(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    thumbnailUrl: Optional[str] = None
    durationSec: Optional[int] = None
    style: Optional[str] = None
    status: str
    publishedAt: Optional[str] = None
    createdAt: str
    updatedAt: str
    jobId: Optional[str] = None
    articleId: Optional[str] = None
    categoryId: Optional[str] = None
    categoryName: Optional[str] = None
    categorySlug: Optional[str] = None
    watched: Optional[bool] = None
    watchLater: Optional[bool] = None
    liked: Optional[bool] = None
    wikiUrl: Optional[str] = None
    viewerCount: int = 0
    viewCount: int = 0


class CategoryResponse(BaseModel):
    id: str
    name: str
    slug: str
    description: Optional[str] = None
    sortOrder: int = 0
    videoCount: int = 0


class UserLoginRequest(BaseModel):
    email: str
    displayName: str


class UserResponse(BaseModel):
    id: str
    email: str
    displayName: str
    createdAt: str
    isAdmin: bool = False


class WatchRequest(BaseModel):
    completed: bool = True


class WatchHistoryItem(BaseModel):
    id: str
    userId: str
    videoId: str
    videoTitle: Optional[str] = None
    videoStatus: Optional[str] = None
    categoryName: Optional[str] = None
    categorySlug: Optional[str] = None
    completed: bool
    watchedAt: str


class ApiInfoResponse(BaseModel):
    base_url: str
    api_keys: list[str]
    has_keys: bool


class ArticleResponse(BaseModel):
    id: str
    title: str
    gitPath: str
    gitHash: Optional[str] = None
    categoryId: Optional[str] = None
    categoryName: Optional[str] = None
    latestVideoId: Optional[str] = None
    latestVideoStatus: Optional[str] = None
    createdAt: str
    updatedAt: str


class WikiSyncDirectoryRequest(BaseModel):
    path: Optional[str] = ""
    paths: Optional[list[str]] = None


class CommentResponse(BaseModel):
    id: str
    videoId: str
    userId: str
    displayName: str
    text: str
    likeCount: int
    likedByMe: bool
    createdAt: str
    parentId: Optional[str] = None
    replies: List["CommentResponse"] = Field(default_factory=list)


class CreateCommentBody(BaseModel):
    text: str
    parentId: Optional[str] = None


# ---------------------------------------------------------------------------
# Job semaphore（同時実行制限: 最大3件）
# ---------------------------------------------------------------------------

MAX_CONCURRENT_JOBS = 3
_job_semaphore = asyncio.Semaphore(MAX_CONCURRENT_JOBS)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _initial_steps() -> list[dict]:
    return [
        {"id": "create_notebook", "label": "ノートブック作成", "status": "pending"},
        {"id": "add_source", "label": "ドキュメント追加", "status": "pending"},
        {"id": "generate_video", "label": "動画生成開始", "status": "pending"},
        {"id": "wait_completion", "label": "生成完了待機", "status": "pending"},
        {"id": "download_ready", "label": "ダウンロード準備完了", "status": "pending"},
    ]


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="E-learning API",
    version="1.0.0",
    description=(
        "社内エンジニア向けE-learningシステムのバックエンドAPI。\n\n"
        "社内WikiのMarkdownファイルをNotebookLMでAI動画に変換し配信します。\n\n"
        "## 認証\n"
        "外部API (`/api/v1/`) は `X-API-Key` ヘッダーによるAPIキー認証が必要です。\n\n"
        "## エンドポイント\n"
        "- `/api/` - フロントエンド用（認証不要）\n"
        "- `/api/v1/` - 外部API用（APIキー認証あり）"
    ),
)

_CORS_ORIGINS = [
    o.strip()
    for o in os.environ.get(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    ).split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_router)


def _allowed_oauth_frontends() -> set[str]:
    """Browser origins allowed as GitHub OAuth return target (localStorage is per-origin)."""
    bases: set[str] = set()
    fu = (os.environ.get("FRONTEND_URL") or "http://localhost:3000").strip().rstrip("/")
    if fu:
        bases.add(fu)
    for o in _CORS_ORIGINS:
        o = o.strip().rstrip("/")
        if o:
            bases.add(o)
    return bases


def _resolve_oauth_frontend(requested: Optional[str]) -> str:
    req = (requested or "").strip().rstrip("/")
    allowed = _allowed_oauth_frontends()
    if req in allowed:
        return req
    return (os.environ.get("FRONTEND_URL") or "http://localhost:3000").strip().rstrip("/")


def _oauth_state_encode(frontend_base: str) -> str:
    raw = json.dumps({"fb": frontend_base}, separators=(",", ":"))
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def _oauth_state_decode(state: Optional[str]) -> Optional[str]:
    if not state:
        return None
    try:
        pad = "=" * (-len(state) % 4)
        data = json.loads(base64.urlsafe_b64decode(state + pad))
        fb = data.get("fb")
        if isinstance(fb, str):
            return fb.strip().rstrip("/")
    except (json.JSONDecodeError, ValueError, TypeError):
        pass
    return None


# ---------------------------------------------------------------------------
# Admin allowlist (ADMIN_EMAILS=comma-separated, case-insensitive; empty = no admins)
# ---------------------------------------------------------------------------

_ADMIN_EMAILS_LOWER: frozenset[str] = frozenset(
    e.strip().lower()
    for e in os.environ.get("ADMIN_EMAILS", "").split(",")
    if e.strip()
)


def _is_admin_email(email: Optional[str]) -> bool:
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
    if not _is_admin_email(em):
        raise HTTPException(status_code=403, detail="管理権限がありません")
    return user


@app.on_event("startup")
async def _on_startup() -> None:
    await database.init_db()
    raw_store, raw_lock = database.get_raw_store()
    register_store_functions(
        store_create_fn=database.store_create,
        store_get_fn=database.store_get,
        store_list_fn=database.store_list,
        store_update_fn=database.store_update,
        initial_steps_fn=_initial_steps,
        run_job_fn=run_job,
        semaphore=_job_semaphore,
        raw_store=raw_store,
        raw_lock=raw_lock,
    )


@app.on_event("shutdown")
async def _on_shutdown() -> None:
    await database.close_db()


# ---------------------------------------------------------------------------
# Auth routes (NotebookLM)
# ---------------------------------------------------------------------------

_STORAGE_STATE = Path.home() / ".notebooklm" / "storage_state.json"
_AUTH_COOKIE_NAMES = {"SID", "__Secure-1PSID", "__Secure-3PSID", "SAPISID"}


def _check_auth_from_storage() -> str:
    if not _STORAGE_STATE.exists():
        return "not_logged_in"
    try:
        import json
        import time
        data = json.loads(_STORAGE_STATE.read_text())
        cookies = {c["name"]: c for c in data.get("cookies", [])}
        now = time.time()
        for name in _AUTH_COOKIE_NAMES:
            if name not in cookies:
                return "session_expired"
            exp = cookies[name].get("expires", -1)
            if exp != -1 and exp < now:
                return "session_expired"
        return "authenticated"
    except Exception:
        return "session_expired"


@app.get("/api/auth/status", response_model=AuthStatus)
async def get_auth_status(_admin: Annotated[dict, Depends(require_admin_user)]):
    return AuthStatus(status=_check_auth_from_storage())


def _find_notebooklm() -> str:
    cmd = shutil.which("notebooklm")
    if cmd:
        return cmd
    bin_dir = Path(sys.executable).parent
    candidate = bin_dir / "notebooklm"
    if candidate.exists():
        return str(candidate)
    for prefix in [
        "/Library/Frameworks/Python.framework/Versions/3.10/bin",
        "/Library/Frameworks/Python.framework/Versions/3.11/bin",
        "/Library/Frameworks/Python.framework/Versions/3.12/bin",
        "/usr/local/bin",
        "/opt/homebrew/bin",
        str(Path.home() / ".local" / "bin"),
    ]:
        candidate = Path(prefix) / "notebooklm"
        if candidate.exists():
            return str(candidate)
    raise FileNotFoundError(
        "notebooklm コマンドが見つかりません。"
        "`pip install 'notebooklm-py[browser]'` でインストールしてください。"
    )


@app.post("/api/auth/login", response_model=LoginResponse)
async def trigger_login(_admin: Annotated[dict, Depends(require_admin_user)]):
    try:
        notebooklm_cmd = _find_notebooklm()
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


# ---------------------------------------------------------------------------
# GitHub OAuth routes
# ---------------------------------------------------------------------------

_GITHUB_CLIENT_ID = os.environ.get("GITHUB_CLIENT_ID", "")
_GITHUB_CLIENT_SECRET = os.environ.get("GITHUB_CLIENT_SECRET", "")
_FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")


@app.get("/api/auth/github")
async def github_oauth_start(frontend_base: Optional[str] = None):
    """GitHub OAuth を開始。別タブで開く想定。

    `frontend_base` にブラウザの origin（例: http://127.0.0.1:3000）を渡すと、
    コールバック後その URL に戻す（localhost と 127.0.0.1 で localStorage が分かれないようにする）。
    """
    if not _GITHUB_CLIENT_ID:
        raise HTTPException(
            status_code=500,
            detail="GITHUB_CLIENT_ID が設定されていません。.env に設定してください。",
        )
    from urllib.parse import urlencode

    base_url = os.environ.get("API_BASE_URL", "http://localhost:8000")
    redirect_uri = f"{base_url}/api/auth/github/callback"
    fb = _resolve_oauth_frontend(frontend_base)
    oauth_state = _oauth_state_encode(fb)
    params = {
        "client_id": _GITHUB_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "scope": "user:email read:user",
        "state": oauth_state,
    }
    return RedirectResponse(
        url=f"https://github.com/login/oauth/authorize?{urlencode(params)}",
        status_code=302,
    )


@app.get("/api/auth/github/callback")
async def github_oauth_callback(
    code: Optional[str] = None,
    error: Optional[str] = None,
    state: Optional[str] = None,
):
    """GitHub OAuth コールバック。トークン交換後、フロントエンドにリダイレクト。"""
    def _redirect_front() -> str:
        fb = _oauth_state_decode(state)
        if fb and fb in _allowed_oauth_frontends():
            return fb
        return _FRONTEND_URL.rstrip("/")

    if error:
        front = _redirect_front()
        return RedirectResponse(
            url=f"{front}/login?error={error}",
            status_code=302,
        )
    if not code:
        raise HTTPException(status_code=400, detail="認証コードがありません")
    if not _GITHUB_CLIENT_ID or not _GITHUB_CLIENT_SECRET:
        raise HTTPException(
            status_code=500,
            detail="GITHUB_CLIENT_ID / GITHUB_CLIENT_SECRET が設定されていません。",
        )

    import httpx
    from urllib.parse import urlencode

    async with httpx.AsyncClient() as client:
        # トークン交換
        token_res = await client.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            data={
                "client_id": _GITHUB_CLIENT_ID,
                "client_secret": _GITHUB_CLIENT_SECRET,
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

        # ユーザー情報取得
        user_res = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        user_res.raise_for_status()
        gh_user = user_res.json()

        # メール取得（非公開の場合は別API）
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

    # フロントエンドにリダイレクト（クエリで localStorage 用 + API 用 HttpOnly cookie）
    from urllib.parse import urlencode

    front = _redirect_front()
    q = urlencode({
        "user_id": user["id"],
        "email": user["email"],
        "display_name": user.get("display_name", user.get("displayName", display_name)),
    })
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


# ---------------------------------------------------------------------------
# Settings routes
# ---------------------------------------------------------------------------


def _mask_key(key: str) -> str:
    if len(key) <= 10:
        return key[:2] + "***" if len(key) > 2 else "***"
    return key[:7] + "***" + key[-3:]


@app.get("/api/settings/api-info", response_model=ApiInfoResponse)
async def get_api_info(_admin: Annotated[dict, Depends(require_admin_user)]):
    raw = os.environ.get("NOTEVIDEO_API_KEYS", "")
    keys = [k.strip() for k in raw.split(",") if k.strip()]
    masked = [_mask_key(k) for k in keys]
    host = os.environ.get("API_BASE_URL", "http://localhost:8000")
    return ApiInfoResponse(
        base_url=f"{host}/api/v1",
        api_keys=masked,
        has_keys=bool(keys),
    )


# ---------------------------------------------------------------------------
# Job routes（管理用・後方互換）
# ---------------------------------------------------------------------------


@app.get("/api/jobs/stats", response_model=JobStats)
async def get_stats(_admin: Annotated[dict, Depends(require_admin_user)]):
    jobs = await database.store_list()
    return JobStats(
        total=len(jobs),
        processing=sum(1 for j in jobs if j["status"] == "processing"),
        completed=sum(1 for j in jobs if j["status"] == "completed"),
        error=sum(1 for j in jobs if j["status"] == "error"),
    )


@app.get("/api/jobs", response_model=list[Job])
async def get_jobs(
    _admin: Annotated[dict, Depends(require_admin_user)],
    status: Optional[str] = None,
    type: Optional[str] = None,
):
    return await database.store_list(status, job_type=type)


@app.get("/api/jobs/{job_id}", response_model=Job)
async def get_job(job_id: str, _admin: Annotated[dict, Depends(require_admin_user)]):
    return await database.store_get(job_id)


@app.get("/api/jobs/{job_id}/download")
async def download_job(job_id: str, _admin: Annotated[dict, Depends(require_admin_user)]):
    job = await database.store_get(job_id)
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="ファイルはまだ準備ができていません")

    if storage.is_s3_enabled():
        url = storage.generate_mp4_download_url(job_id)
        if url is None:
            raise HTTPException(status_code=500, detail="ダウンロード URL の生成に失敗しました")
        return RedirectResponse(url=url, status_code=302)

    output_path = OUTPUTS_DIR / f"{job_id}.mp4"
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="動画ファイルが見つかりません")

    safe_title = job["notebookTitle"].replace("/", "_").replace("\\", "_")
    return FileResponse(
        path=str(output_path),
        media_type="video/mp4",
        filename=f"{safe_title}.mp4",
    )


# ---------------------------------------------------------------------------
# E-learning: Videos routes
# ---------------------------------------------------------------------------


def _build_wiki_url(git_path: Optional[str]) -> Optional[str]:
    """article の git_path から Wiki サイトの URL を構築する"""
    if not git_path:
        return None
    base = os.environ.get("WIKI_BASE_URL", "").rstrip("/")
    if not base:
        # WIKI_GIT_REPO_URL から導出を試みる
        repo_url = os.environ.get("WIKI_GIT_REPO_URL", "").rstrip("/").removesuffix(".git")
        branch = os.environ.get("WIKI_GIT_BRANCH", "main")
        if repo_url and "github.com" in repo_url:
            base = f"{repo_url}/blob/{branch}"
        else:
            return None
    return f"{base}/{git_path}" if base else None


def _dict_to_comment(d: dict) -> CommentResponse:
    replies = [_dict_to_comment(r) for r in (d.get("replies") or [])]
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


def _video_dict_to_response(v: dict, viewer_count: int = 0, view_count: int = 0) -> VideoResponse:
    git_path = v.get("article_git_path")
    wiki_url = _build_wiki_url(git_path) if git_path else None
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


@app.get("/api/videos", response_model=list[VideoResponse])
async def get_videos(
    category: Optional[str] = None,
    search: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    locale: Optional[str] = None,
    published_after: Optional[str] = None,
    x_user_id: Optional[str] = Header(default=None),
):
    language = locale if locale in ("ja", "vi") else "ja"
    videos = await database.list_videos(
        category_slug=category,
        search=search,
        status=status,
        limit=limit,
        offset=offset,
        user_id=x_user_id,
        language=language,
        published_after=published_after,
    )
    if x_user_id:
        watch_later_ids = await database.get_watch_later_ids(x_user_id)
        liked_ids = await database.get_liked_video_ids(x_user_id)
        for v in videos:
            v["watch_later"] = v["id"] in watch_later_ids
            v["liked"] = v["id"] in liked_ids
    return [_video_dict_to_response(v) for v in videos]


@app.get("/api/videos/{video_id}", response_model=VideoResponse)
async def get_video(video_id: str, x_user_id: Optional[str] = Header(default=None)):
    video = await database.get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="動画が見つかりません")
    if x_user_id:
        history = await database.get_watch_history(x_user_id, limit=1000)
        watched_ids = {h["video_id"] for h in history}
        video["watched"] = video_id in watched_ids
        watch_later_ids = await database.get_watch_later_ids(x_user_id)
        liked_ids = await database.get_liked_video_ids(x_user_id)
        video["watch_later"] = video_id in watch_later_ids
        video["liked"] = video_id in liked_ids
    viewer_count, view_count = await database.get_video_watch_counts(video_id)
    return _video_dict_to_response(video, viewer_count, view_count)


@app.get("/api/videos/{video_id}/stream")
async def stream_video(video_id: str):
    """動画をストリーミングまたはダウンロードURLを返す"""
    video = await database.get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="動画が見つかりません")
    if video.get("status") != "ready":
        raise HTTPException(status_code=400, detail="動画はまだ準備ができていません")

    job_id = video.get("job_id")
    if not job_id:
        raise HTTPException(status_code=404, detail="動画ファイルの情報が見つかりません")

    if storage.is_s3_enabled():
        url = storage.generate_mp4_streaming_url(job_id, expires_in=86400)
        if url:
            return RedirectResponse(url=url, status_code=302)

    output_path = OUTPUTS_DIR / f"{job_id}.mp4"
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="動画ファイルが見つかりません")

    def iter_file():
        with open(output_path, "rb") as f:
            while chunk := f.read(1024 * 1024):
                yield chunk

    return StreamingResponse(iter_file(), media_type="video/mp4")


@app.get("/api/videos/{video_id}/thumbnail")
async def stream_thumbnail(video_id: str):
    """サムネイル画像を返す（S3時はリダイレクト、ローカル時はファイル返却）"""
    video = await database.get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="動画が見つかりません")
    if video.get("status") != "ready":
        raise HTTPException(status_code=400, detail="動画はまだ準備ができていません")

    job_id = video.get("job_id")
    if not job_id:
        raise HTTPException(status_code=404, detail="サムネイル情報が見つかりません")

    if storage.is_s3_enabled():
        url = storage.generate_thumbnail_streaming_url(job_id, expires_in=86400)
        if not url:
            raise HTTPException(status_code=404, detail="サムネイルが見つかりません")
        return RedirectResponse(url=url, status_code=302)

    thumbnail_path = OUTPUTS_DIR / "thumbnails" / f"{job_id}.jpg"
    if not thumbnail_path.exists():
        raise HTTPException(status_code=404, detail="サムネイルが見つかりません")
    return FileResponse(path=str(thumbnail_path), media_type="image/jpeg")


@app.post("/api/videos/{video_id}/watch")
async def record_watch(
    video_id: str,
    req: WatchRequest,
    x_user_id: Optional[str] = Header(default=None),
):
    if not x_user_id:
        raise HTTPException(status_code=401, detail="ユーザーIDが必要です")
    video = await database.get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="動画が見つかりません")
    record = await database.record_watch(x_user_id, video_id, req.completed)
    return {"success": True, "record": record}


# ---------------------------------------------------------------------------
# E-learning: Categories routes
# ---------------------------------------------------------------------------


@app.get("/api/categories", response_model=list[CategoryResponse])
async def get_categories(locale: Optional[str] = None):
    language = locale if locale in ("ja", "vi") else "ja"
    cats = await database.get_categories(language=language)
    return [
        CategoryResponse(
            id=c["id"],
            name=c["name"],
            slug=c["slug"],
            description=c.get("description"),
            sortOrder=c.get("sort_order", c.get("sortOrder", 0)),
            videoCount=c.get("videoCount", c.get("video_count", 0)),
        )
        for c in cats
    ]


# ---------------------------------------------------------------------------
# E-learning: Users routes
# ---------------------------------------------------------------------------


@app.post("/api/users/login", response_model=UserResponse)
async def user_login(req: UserLoginRequest, response: Response):
    if not req.email or not req.displayName:
        raise HTTPException(status_code=400, detail="メールアドレスと名前は必須です")
    user = await database.get_or_create_user(req.email, req.displayName)
    response.set_cookie(
        key="user_id",
        value=user["id"],
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 30,
    )
    em = user.get("email") or ""
    return UserResponse(
        id=user["id"],
        email=em,
        displayName=user.get("display_name", user.get("displayName", "")),
        createdAt=str(user.get("created_at", "")),
        isAdmin=_is_admin_email(em),
    )


@app.get("/api/users/me", response_model=Optional[UserResponse])
async def get_current_user(
    x_user_id: Optional[str] = Header(default=None),
    user_id: Optional[str] = Cookie(default=None),
):
    """未ログイン時は 401 ではなく null（200）を返す。呼び出し側は認証なしで利用可能。"""
    uid = x_user_id or user_id
    if not uid:
        return None
    user = await database.get_user(uid)
    if not user:
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")
    em = user.get("email") or ""
    return UserResponse(
        id=user["id"],
        email=em,
        displayName=user.get("display_name", user.get("displayName", "")),
        createdAt=str(user.get("created_at", "")),
        isAdmin=_is_admin_email(em),
    )


@app.get("/api/users/me/history", response_model=list[WatchHistoryItem])
async def get_watch_history(
    x_user_id: Optional[str] = Header(default=None),
    user_id: Optional[str] = Cookie(default=None),
    limit: int = 50,
):
    uid = x_user_id or user_id
    if not uid:
        raise HTTPException(status_code=401, detail="ログインが必要です")
    history = await database.get_watch_history(uid, limit=limit)
    return [
        WatchHistoryItem(
            id=h["id"],
            userId=h["user_id"],
            videoId=h["video_id"],
            videoTitle=h.get("videoTitle", h.get("video_title")),
            videoStatus=h.get("videoStatus", h.get("video_status")),
            categoryName=h.get("categoryName", h.get("category_name")),
            categorySlug=h.get("categorySlug", h.get("category_slug")),
            completed=bool(h.get("completed", True)),
            watchedAt=str(h.get("watched_at", "")),
        )
        for h in history
    ]


@app.post("/api/videos/{video_id}/watch-later")
async def toggle_watch_later(
    video_id: str,
    x_user_id: Optional[str] = Header(default=None),
    user_id: Optional[str] = Cookie(default=None),
):
    uid = x_user_id or user_id
    if not uid:
        raise HTTPException(status_code=401, detail="ログインが必要です")
    video = await database.get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="動画が見つかりません")
    added = await database.toggle_watch_later(uid, video_id)
    return {"success": True, "added": added}


@app.post("/api/videos/{video_id}/liked")
async def toggle_liked_video(
    video_id: str,
    x_user_id: Optional[str] = Header(default=None),
    user_id: Optional[str] = Cookie(default=None),
):
    uid = x_user_id or user_id
    if not uid:
        raise HTTPException(status_code=401, detail="ログインが必要です")
    video = await database.get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="動画が見つかりません")
    added = await database.toggle_liked_video(uid, video_id)
    return {"success": True, "added": added}


@app.get("/api/users/me/watch-later", response_model=list[VideoResponse])
async def get_watch_later(
    x_user_id: Optional[str] = Header(default=None),
    user_id: Optional[str] = Cookie(default=None),
    limit: int = 100,
):
    uid = x_user_id or user_id
    if not uid:
        raise HTTPException(status_code=401, detail="ログインが必要です")
    videos = await database.get_watch_later_videos(uid, limit=limit)
    watch_later_ids = {v["id"] for v in videos}
    liked_ids = await database.get_liked_video_ids(uid)
    history = await database.get_watch_history(uid, limit=1000)
    watched_ids = {h["video_id"] for h in history}
    for v in videos:
        v["watched"] = v["id"] in watched_ids
        v["watch_later"] = True
        v["liked"] = v["id"] in liked_ids
    return [_video_dict_to_response(v) for v in videos]


@app.get("/api/users/me/liked", response_model=list[VideoResponse])
async def get_liked_videos(
    x_user_id: Optional[str] = Header(default=None),
    user_id: Optional[str] = Cookie(default=None),
    limit: int = 100,
):
    uid = x_user_id or user_id
    if not uid:
        raise HTTPException(status_code=401, detail="ログインが必要です")
    videos = await database.get_liked_videos(uid, limit=limit)
    liked_ids = {v["id"] for v in videos}
    watch_later_ids = await database.get_watch_later_ids(uid)
    history = await database.get_watch_history(uid, limit=1000)
    watched_ids = {h["video_id"] for h in history}
    for v in videos:
        v["watched"] = v["id"] in watched_ids
        v["watch_later"] = v["id"] in watch_later_ids
        v["liked"] = True
    return [_video_dict_to_response(v) for v in videos]


@app.get("/api/videos/{video_id}/comments", response_model=list[CommentResponse])
async def list_video_comments(
    video_id: str,
    x_user_id: Optional[str] = Header(default=None),
    user_id: Optional[str] = Cookie(default=None),
):
    video = await database.get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="動画が見つかりません")
    viewer = x_user_id or user_id
    raw = await database.list_comments_for_video(video_id, viewer)
    return [_dict_to_comment(c) for c in raw]


@app.post("/api/videos/{video_id}/comments", response_model=CommentResponse)
async def create_video_comment(
    video_id: str,
    body: CreateCommentBody,
    x_user_id: Optional[str] = Header(default=None),
    user_id: Optional[str] = Cookie(default=None),
):
    uid = x_user_id or user_id
    if not uid:
        raise HTTPException(status_code=401, detail="ログインが必要です")
    video = await database.get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="動画が見つかりません")
    created = await database.create_comment(video_id, uid, body.text, body.parentId)
    if not created:
        raise HTTPException(status_code=400, detail="コメントを投稿できません")
    return _dict_to_comment(created)


@app.post("/api/comments/{comment_id}/like", response_model=CommentResponse)
async def toggle_comment_like_route(
    comment_id: str,
    x_user_id: Optional[str] = Header(default=None),
    user_id: Optional[str] = Cookie(default=None),
):
    uid = x_user_id or user_id
    if not uid:
        raise HTTPException(status_code=401, detail="ログインが必要です")
    out = await database.toggle_comment_like(comment_id, uid)
    if not out:
        raise HTTPException(status_code=404, detail="コメントが見つかりません")
    return _dict_to_comment(out)


# ---------------------------------------------------------------------------
# Wiki sync routes
# ---------------------------------------------------------------------------


@app.get("/api/wiki/directories")
async def get_wiki_directories(_admin: Annotated[dict, Depends(require_admin_user)]):
    """リポジトリ内の .md を含むディレクトリ一覧を返す"""
    from wiki_sync import get_wiki_directories as _get_dirs
    return _get_dirs()


@app.post("/api/wiki/sync-directory")
async def trigger_wiki_sync_directory(
    background_tasks: BackgroundTasks,
    _admin: Annotated[dict, Depends(require_admin_user)],
    payload: Optional[WikiSyncDirectoryRequest] = None,
    path: str = "",
):
    """指定ディレクトリ配下の .md ファイルのみを同期し、動画生成を実行する"""
    from wiki_sync import sync_wiki_from_directory

    requested_paths = payload.paths if payload and payload.paths else None
    requested_path = (
        payload.path
        if payload and payload.path is not None
        else path
    )

    sync_id = f"sync_{uuid.uuid4().hex[:8]}"
    logger.info(
        "Wiki sync request received sync_id=%s path=%s paths_count=%d",
        sync_id,
        requested_path or "(root)",
        len(requested_paths or []),
    )

    async def _do_sync():
        logger.info(
            "Wiki sync background task started sync_id=%s path=%s paths_count=%d",
            sync_id,
            requested_path or "(root)",
            len(requested_paths or []),
        )
        try:
            result = await sync_wiki_from_directory(
                relative_dir=requested_path or "",
                target_paths=requested_paths,
                store_update_fn=database.store_update,
                run_job_fn=run_job,
                semaphore=_job_semaphore,
                outputs_dir=OUTPUTS_DIR,
                sync_id=sync_id,
            )
            logger.info(
                "Wiki sync background task finished sync_id=%s status=%s processed=%s jobs_created=%s hash=%s result=%s",
                sync_id,
                result.get("status"),
                result.get("processed"),
                result.get("jobs_created"),
                result.get("hash"),
                result,
            )
        except Exception:
            logger.exception(
                "Wiki sync background task crashed sync_id=%s path=%s",
                sync_id,
                requested_path or "(root)",
            )
            raise

    logger.info(
        "Wiki sync background task scheduled sync_id=%s path=%s paths_count=%d",
        sync_id,
        requested_path or "(root)",
        len(requested_paths or []),
    )
    background_tasks.add_task(_do_sync)
    return {"message": "ディレクトリの動画作成を開始しました", "sync_id": sync_id}


@app.get("/api/wiki/sync-status")
async def get_wiki_sync_status(_admin: Annotated[dict, Depends(require_admin_user)]):
    """Wiki同期の現在の状態を返す"""
    from wiki_sync import get_sync_status
    return get_sync_status()


# ---------------------------------------------------------------------------
# Admin routes
# ---------------------------------------------------------------------------


@app.get("/api/admin/articles", response_model=list[ArticleResponse])
async def get_admin_articles(_admin: Annotated[dict, Depends(require_admin_user)]):
    """記事一覧と動画生成状況を返す（管理用）"""
    articles = await database.list_articles()
    return [
        ArticleResponse(
            id=a["id"],
            title=a["title"],
            gitPath=a.get("git_path", a.get("gitPath", "")),
            gitHash=a.get("git_hash"),
            categoryId=a.get("category_id"),
            categoryName=a.get("categoryName", a.get("category_name")),
            latestVideoId=a.get("latestVideoId", a.get("latest_video_id")),
            latestVideoStatus=a.get("latestVideoStatus", a.get("latest_video_status")),
            createdAt=str(a.get("created_at", "")),
            updatedAt=str(a.get("updated_at", "")),
        )
        for a in articles
    ]


logger = logging.getLogger(__name__)
