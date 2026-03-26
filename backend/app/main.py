"""
E-learning バックエンド API — application factory.

ストレージ:
  - DATABASE_URL 環境変数が設定されている場合: MySQL（RDS）
  - 未設定の場合: インメモリ（開発用）
  - S3_BUCKET_NAME 環境変数が設定されている場合: AWS S3 にファイル保存
  - 未設定の場合: ローカルファイルシステム（開発用）
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.config  # noqa: F401 — load_dotenv before database reads env
import database
from app.config import _CORS_ORIGINS
from app.job_runtime import job_semaphore
from app.routers import admin, auth, categories, comments, jobs, settings, users, videos, wiki
from app.routers.v1 import register_store_functions, router as v1_router
from app.services.jobs import initial_steps
from app.services.runner import run_job

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logging.getLogger("notebooklm").setLevel(logging.DEBUG)


@asynccontextmanager
async def _lifespan(_app: FastAPI) -> AsyncIterator[None]:
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

    return app


app = create_app()

logger = logging.getLogger(__name__)
