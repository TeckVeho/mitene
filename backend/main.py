"""
NoteVideo バックエンド API
generate_video_from_csv.py のロジックをジョブキュー方式で提供するFastAPIアプリ

ストレージ:
  - DATABASE_URL 環境変数が設定されている場合: PostgreSQL（RDS）
  - 未設定の場合: インメモリ（開発用）
  - S3_BUCKET_NAME 環境変数が設定されている場合: AWS S3 にファイル保存
  - 未設定の場合: ローカルファイルシステム（開発用）
"""

import asyncio
import logging
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel

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
    status: str  # pending | in_progress | completed | error
    message: Optional[str] = None


class Job(BaseModel):
    id: str
    csvFileNames: str
    notebookTitle: str
    instructions: str
    style: str
    format: str
    language: str
    timeout: int
    status: str  # pending | processing | completed | error
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
    status: str  # authenticated | not_logged_in | session_expired


class LoginResponse(BaseModel):
    message: str


# ---------------------------------------------------------------------------
# Job semaphore（同時実行制限: 最大3件）
# ---------------------------------------------------------------------------

_job_semaphore = asyncio.Semaphore(3)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _initial_steps() -> list[dict]:
    return [
        {"id": "create_notebook", "label": "ノートブック作成", "status": "pending"},
        {"id": "add_source", "label": "CSVソース追加", "status": "pending"},
        {"id": "generate_video", "label": "動画生成開始", "status": "pending"},
        {"id": "wait_completion", "label": "生成完了待機", "status": "pending"},
        {"id": "download_ready", "label": "ダウンロード準備完了", "status": "pending"},
    ]


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="NoteVideo API",
    version="0.3.0",
    description=(
        "CSV→AI解説動画生成サービス NoteVideo のバックエンドAPI。\n\n"
        "## 認証\n"
        "外部API (`/api/v1/`) は `X-API-Key` ヘッダーによるAPIキー認証が必要です。\n"
        "サーバーの環境変数 `NOTEVIDEO_API_KEYS` にカンマ区切りでキーを設定してください。\n\n"
        "## Webhook\n"
        "ジョブ作成時に `callback_url` を指定すると、完了・エラー時にPOSTで通知します。\n\n"
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


@app.on_event("startup")
async def _on_startup() -> None:
    """起動時: DB初期化 & v1ルーターにストア関数を登録する"""
    await database.init_db()

    # in-memory モード時は _store / lock を直接渡す（後方互換）
    raw_store, raw_lock = database.get_raw_store()

    register_store_functions(
        store_create_fn=database.store_create,
        store_get_fn=database.store_get,
        store_list_fn=database.store_list,
        store_update_fn=database.store_update,
        initial_steps_fn=_initial_steps,
        run_job_fn=run_job,
        semaphore=_job_semaphore,
        # in-memory モード専用（PostgreSQL モードでは使用しない）
        raw_store=raw_store,
        raw_lock=raw_lock,
    )


@app.on_event("shutdown")
async def _on_shutdown() -> None:
    await database.close_db()


# ---------------------------------------------------------------------------
# Auth routes
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
async def get_auth_status():
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
async def trigger_login():
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
# Job routes
# ---------------------------------------------------------------------------


@app.get("/api/jobs/stats", response_model=JobStats)
async def get_stats():
    jobs = await database.store_list()
    return JobStats(
        total=len(jobs),
        processing=sum(1 for j in jobs if j["status"] == "processing"),
        completed=sum(1 for j in jobs if j["status"] == "completed"),
        error=sum(1 for j in jobs if j["status"] == "error"),
    )


@app.get("/api/jobs", response_model=list[Job])
async def get_jobs(status: Optional[str] = None):
    return await database.store_list(status)


@app.get("/api/jobs/{job_id}", response_model=Job)
async def get_job(job_id: str):
    return await database.store_get(job_id)


@app.post("/api/jobs", response_model=Job, status_code=201)
async def create_job(
    background_tasks: BackgroundTasks,
    csvFiles: List[UploadFile] = File(...),
    notebookTitle: str = Form(default="CSV分析レポート"),
    instructions: str = Form(default="CSVデータの主要な傾向と示唆を分かりやすく解説してください"),
    style: str = Form(default="whiteboard"),
    format: str = Form(default="explainer"),
    language: str = Form(default="ja"),
    timeout: int = Form(default=1800),
):
    if not csvFiles:
        raise HTTPException(status_code=400, detail="CSVファイルを1つ以上指定してください")

    import uuid

    job_id = f"job_{uuid.uuid4().hex[:12]}"
    now = _now()

    csv_paths: list[Path] = []
    file_names: list[str] = []

    for upload in csvFiles:
        safe_name = upload.filename or "upload.csv"
        content = await upload.read()

        # ローカルに一時保存（notebooklm-py がローカルパスを必要とするため）
        local_path = storage.save_csv_locally(UPLOADS_DIR, job_id, safe_name, content)
        csv_paths.append(local_path)
        file_names.append(safe_name)

        # S3 が有効な場合はバックグラウンドで S3 にもアップロード
        storage.upload_csv_to_s3(job_id, safe_name, content)

    output_path = OUTPUTS_DIR / f"{job_id}.mp4"

    job: dict = {
        "id": job_id,
        "csvFileNames": ",".join(file_names),
        "notebookTitle": notebookTitle,
        "instructions": instructions,
        "style": style,
        "format": format,
        "language": language,
        "timeout": timeout,
        "status": "pending",
        "steps": _initial_steps(),
        "currentStep": None,
        "errorMessage": None,
        "createdAt": now,
        "updatedAt": now,
        "completedAt": None,
        "callbackUrl": None,
    }

    await database.store_create(job)

    background_tasks.add_task(
        run_job,
        job_id=job_id,
        csv_paths=csv_paths,
        output_path=output_path,
        notebook_title=notebookTitle,
        instructions=instructions,
        style=style,
        video_format=format,
        language=language,
        timeout=timeout,
        store_update=database.store_update,
        semaphore=_job_semaphore,
    )

    return job


@app.get("/api/jobs/{job_id}/download")
async def download_job(job_id: str):
    job = await database.store_get(job_id)
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="動画はまだ準備ができていません")

    # S3 モード: 署名付き URL にリダイレクト
    if storage.is_s3_enabled():
        url = storage.generate_mp4_download_url(job_id)
        if url is None:
            raise HTTPException(status_code=500, detail="ダウンロード URL の生成に失敗しました")
        return RedirectResponse(url=url, status_code=302)

    # ローカルモード: ファイルを直接返す
    output_path = OUTPUTS_DIR / f"{job_id}.mp4"
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="動画ファイルが見つかりません")

    safe_title = job["notebookTitle"].replace("/", "_").replace("\\", "_")
    return FileResponse(
        path=str(output_path),
        media_type="video/mp4",
        filename=f"{safe_title}.mp4",
    )
