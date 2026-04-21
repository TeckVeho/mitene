"""
E-learning バックエンド API — application factory.

ストレージ:
  - DATABASE_URL: MySQL（未設定時はインメモリ）
  - resolve_storage_kind: GCS_BUCKET → GCS、次に S3 設定 → S3、それ以外はローカル（STORAGE_BACKEND で上書き可）
"""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.config  # noqa: F401 — load_dotenv before database reads env
import database
from app.config import _CORS_ORIGINS
from app.job_runtime import job_semaphore
from app.routers import admin, auth, categories, comments, jobs, remote_login, settings, users, videos, wiki
from app.routers.v1 import register_store_functions, router as v1_router
from app.services.jobs import initial_steps
from app.services.notebooklm_gcs import (
    download_storage_state_if_configured,
    log_notebooklm_storage_config,
)
from app.services.runner import run_job

_log_level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, _log_level_name, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logging.getLogger("notebooklm").setLevel(logging.DEBUG)


@asynccontextmanager
async def _lifespan(_app: FastAPI) -> AsyncIterator[None]:
    log_notebooklm_storage_config()
    download_storage_state_if_configured()
    await database.init_db()
    raw_store, raw_lock = database.get_raw_store()
    register_store_functions(
        store_create_fn=database.store_create,
        store_get_fn=database.store_get,
        store_list_fn=database.store_list,
        store_update_fn=database.store_update,
        initial_steps_fn=initial_steps,
        run_job_fn=run_job,
        semaphore=job_semaphore,
        raw_store=raw_store,
        raw_lock=raw_lock,
    )
    yield
    await database.close_db()


def create_app() -> FastAPI:
    app = FastAPI(
        title="E-learning API",
        version="1.0.0",
        lifespan=_lifespan,
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

    app.add_middleware(
        CORSMiddleware,
        allow_origins=_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(v1_router)
    app.include_router(auth.router)
    app.include_router(settings.router)
    app.include_router(jobs.router)
    app.include_router(videos.router)
    app.include_router(categories.router)
    app.include_router(users.router)
    app.include_router(comments.router)
    app.include_router(wiki.router)
    app.include_router(admin.router)
    app.include_router(remote_login.router)

    @app.get("/health")
    def health() -> dict[str, str]:
        """Liveness/readiness for load balancers and Cloud Run optional HTTP probes."""
        return {"status": "ok"}

    return app


app = create_app()

logger = logging.getLogger(__name__)
