"""
ジョブストア抽象化モジュール

DATABASE_URL 環境変数が設定されている場合は MySQL（RDS）を使用し、
未設定の場合はインメモリストアにフォールバックする（開発環境向け）。

DATABASE_URL 形式:
  mysql://user:password@host:3306/dbname
  mysql+aiomysql://user:password@host:3306/dbname
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse, unquote

logger = logging.getLogger(__name__)

DATABASE_URL: Optional[str] = os.environ.get("DATABASE_URL")
_USE_MYSQL: bool = bool(DATABASE_URL)

# ---------------------------------------------------------------------------
# In-memory fallback（開発用）
# ---------------------------------------------------------------------------

_store: dict[str, dict] = {}
_store_lock = asyncio.Lock()

# ---------------------------------------------------------------------------
# MySQL 接続プール（本番用）
# ---------------------------------------------------------------------------

_pool = None

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS jobs (
    id              VARCHAR(32)   PRIMARY KEY,
    csv_file_names  TEXT          NOT NULL,
    notebook_title  TEXT          NOT NULL,
    instructions    TEXT          NOT NULL,
    style           VARCHAR(32),
    format          VARCHAR(32),
    language        VARCHAR(8),
    timeout         INTEGER,
    status          VARCHAR(16)   NOT NULL DEFAULT 'pending',
    steps           JSON          NOT NULL,
    current_step    VARCHAR(32),
    error_message   TEXT,
    callback_url    TEXT,
    created_at      DATETIME(6)   NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at      DATETIME(6)   NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
                    ON UPDATE CURRENT_TIMESTAMP(6),
    completed_at    DATETIME(6)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_mysql_url(url: str) -> dict:
    """mysql:// または mysql+aiomysql:// 形式の URL をパースする"""
    normalized = url.replace("mysql+aiomysql://", "mysql://")
    parsed = urlparse(normalized)
    return {
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 3306,
        "user": unquote(parsed.username) if parsed.username else "root",
        "password": unquote(parsed.password) if parsed.password else "",
        "db": parsed.path.lstrip("/"),
    }


# ---------------------------------------------------------------------------
# DB ライフサイクル
# ---------------------------------------------------------------------------


async def init_db() -> None:
    """アプリ起動時にDB接続プールを初期化し、テーブルを作成する"""
    global _pool
    if not _USE_MYSQL:
        logger.info("DATABASE_URL 未設定 → インメモリストアを使用します（開発モード）")
        return

    try:
        import aiomysql
    except ImportError:
        raise RuntimeError(
            "aiomysql がインストールされていません。"
            "pip install aiomysql を実行してください。"
        )

    params = _parse_mysql_url(DATABASE_URL)
    _pool = await aiomysql.create_pool(
        host=params["host"],
        port=params["port"],
        user=params["user"],
        password=params["password"],
        db=params["db"],
        autocommit=True,
        charset="utf8mb4",
        cursorclass=aiomysql.DictCursor,
        minsize=2,
        maxsize=10,
    )

    async with _pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(_CREATE_TABLE_SQL)

    logger.info("MySQL 接続プールを初期化しました（host=%s, db=%s）", params["host"], params["db"])


async def close_db() -> None:
    """アプリ終了時に DB 接続プールをクローズする"""
    global _pool
    if _pool is not None:
        _pool.close()
        await _pool.wait_closed()
        _pool = None
        logger.info("MySQL 接続プールをクローズしました")


# ---------------------------------------------------------------------------
# 行 → dict 変換（MySQL レスポンス用）
# ---------------------------------------------------------------------------


def _row_to_dict(row: dict) -> dict:
    """aiomysql の DictCursor 結果を API レスポンス形式の dict に変換する"""
    steps_raw = row.get("steps")
    if isinstance(steps_raw, str):
        steps = json.loads(steps_raw)
    elif isinstance(steps_raw, (list, dict)):
        steps = steps_raw
    else:
        steps = []

    def _fmt_ts(ts) -> Optional[str]:
        if ts is None:
            return None
        if isinstance(ts, datetime):
            # MySQL の DATETIME は timezone なしで返るので UTC として扱う
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            return ts.isoformat()
        return str(ts)

    return {
        "id": row["id"],
        "csvFileNames": row["csv_file_names"],
        "notebookTitle": row["notebook_title"],
        "instructions": row["instructions"],
        "style": row["style"],
        "format": row["format"],
        "language": row["language"],
        "timeout": row["timeout"],
        "status": row["status"],
        "steps": steps,
        "currentStep": row["current_step"],
        "errorMessage": row["error_message"],
        "callbackUrl": row["callback_url"],
        "createdAt": _fmt_ts(row["created_at"]),
        "updatedAt": _fmt_ts(row["updated_at"]),
        "completedAt": _fmt_ts(row["completed_at"]),
    }


# ---------------------------------------------------------------------------
# CRUD 操作
# ---------------------------------------------------------------------------


async def store_create(job: dict) -> dict:
    """新しいジョブを作成する"""
    if not _USE_MYSQL:
        async with _store_lock:
            _store[job["id"]] = dict(job)
        return dict(job)

    async with _pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO jobs (
                    id, csv_file_names, notebook_title, instructions,
                    style, format, language, timeout,
                    status, steps, current_step, error_message, callback_url,
                    created_at, updated_at, completed_at
                ) VALUES (
                    %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s
                )
                """,
                (
                    job["id"],
                    job["csvFileNames"],
                    job["notebookTitle"],
                    job["instructions"],
                    job.get("style"),
                    job.get("format"),
                    job.get("language"),
                    job.get("timeout"),
                    job.get("status", "pending"),
                    json.dumps(job.get("steps", []), ensure_ascii=False),
                    job.get("currentStep"),
                    job.get("errorMessage"),
                    job.get("callbackUrl"),
                    job["createdAt"],
                    job["updatedAt"],
                    job.get("completedAt"),
                ),
            )
    return job


async def store_get(job_id: str) -> dict:
    """ジョブを1件取得する。存在しない場合は HTTP 404 を raise する"""
    if not _USE_MYSQL:
        async with _store_lock:
            if job_id not in _store:
                from fastapi import HTTPException
                raise HTTPException(
                    status_code=404, detail=f"ジョブが見つかりません: {job_id}"
                )
            return dict(_store[job_id])

    async with _pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT * FROM jobs WHERE id = %s", (job_id,))
            row = await cur.fetchone()

    if row is None:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=404, detail=f"ジョブが見つかりません: {job_id}"
        )
    return _row_to_dict(row)


async def store_list(status: Optional[str] = None) -> list[dict]:
    """ジョブ一覧を取得する（作成日時降順）"""
    if not _USE_MYSQL:
        async with _store_lock:
            jobs = list(_store.values())
        jobs.sort(key=lambda j: j["createdAt"], reverse=True)
        if status and status != "all":
            jobs = [j for j in jobs if j["status"] == status]
        return jobs

    async with _pool.acquire() as conn:
        async with conn.cursor() as cur:
            if status and status != "all":
                await cur.execute(
                    "SELECT * FROM jobs WHERE status = %s ORDER BY created_at DESC",
                    (status,),
                )
            else:
                await cur.execute("SELECT * FROM jobs ORDER BY created_at DESC")
            rows = await cur.fetchall()

    return [_row_to_dict(r) for r in rows]


async def store_update(job_id: str, **kwargs) -> dict:
    """ジョブを部分更新する"""
    if not _USE_MYSQL:
        async with _store_lock:
            if job_id not in _store:
                raise KeyError(f"ジョブが見つかりません: {job_id}")
            _store[job_id].update(kwargs)
            _store[job_id]["updatedAt"] = _now()
            return dict(_store[job_id])

    # camelCase キー → snake_case カラム のマッピング
    _field_map = {
        "status": "status",
        "steps": "steps",
        "currentStep": "current_step",
        "errorMessage": "error_message",
        "completedAt": "completed_at",
    }

    set_clauses: list[str] = []
    params: list = []

    for key, value in kwargs.items():
        col = _field_map.get(key)
        if col is None:
            continue
        if col == "steps":
            value = json.dumps(value, ensure_ascii=False)
        set_clauses.append(f"`{col}` = %s")
        params.append(value)

    if not set_clauses:
        return await store_get(job_id)

    # updated_at は ON UPDATE CURRENT_TIMESTAMP で自動更新されるが、明示的に設定する
    set_clauses.append("`updated_at` = %s")
    params.append(datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f"))
    params.append(job_id)

    query = f"UPDATE jobs SET {', '.join(set_clauses)} WHERE id = %s"
    async with _pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(query, params)

    return await store_get(job_id)


def get_raw_store() -> tuple[dict, asyncio.Lock]:
    """
    後方互換のため in-memory ストアと Lock を返す。
    MySQL モードでは使用しないこと。
    """
    return _store, _store_lock
