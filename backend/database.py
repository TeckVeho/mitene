"""
ジョブストア + E-learning データ抽象化モジュール

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
import uuid
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

# E-learning in-memory stores
_articles_store: dict[str, dict] = {}
_videos_store: dict[str, dict] = {}
_categories_store: dict[str, dict] = {}
_users_store: dict[str, dict] = {}
_watch_history_store: list[dict] = []
_watch_later_store: list[dict] = []
_liked_videos_store: list[dict] = []
_comments_store: dict[str, dict] = {}
_comment_likes_store: list[dict] = []
_elearning_lock = asyncio.Lock()

# ---------------------------------------------------------------------------
# MySQL 接続プール（本番用）
# ---------------------------------------------------------------------------

_pool = None

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS jobs (
    id               VARCHAR(32)   PRIMARY KEY,
    job_type         VARCHAR(16)   NOT NULL DEFAULT 'video',
    source_file_names TEXT         NOT NULL,
    notebook_title   TEXT          NOT NULL,
    instructions     TEXT          NOT NULL,
    style            VARCHAR(32),
    format           VARCHAR(32),
    language         VARCHAR(8),
    timeout          INTEGER,
    status           VARCHAR(16)   NOT NULL DEFAULT 'pending',
    steps            JSON          NOT NULL,
    current_step     VARCHAR(32),
    error_message    TEXT,
    callback_url     TEXT,
    created_at       DATETIME(6)   NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at       DATETIME(6)   NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
                     ON UPDATE CURRENT_TIMESTAMP(6),
    completed_at     DATETIME(6)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
"""

_CREATE_CATEGORIES_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS categories (
    id          VARCHAR(36)   PRIMARY KEY,
    name        VARCHAR(128)  NOT NULL,
    slug        VARCHAR(128)  NOT NULL UNIQUE,
    description TEXT,
    sort_order  INTEGER       NOT NULL DEFAULT 0,
    created_at  DATETIME(6)   NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
"""

_CREATE_ARTICLES_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS articles (
    id          VARCHAR(36)   PRIMARY KEY,
    title       VARCHAR(256)  NOT NULL,
    content_md  LONGTEXT      NOT NULL,
    git_path    VARCHAR(512)  NOT NULL UNIQUE,
    git_hash    VARCHAR(40),
    category_id VARCHAR(36),
    created_at  DATETIME(6)   NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at  DATETIME(6)   NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
                ON UPDATE CURRENT_TIMESTAMP(6),
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
"""

_CREATE_VIDEOS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS videos (
    id            VARCHAR(36)   PRIMARY KEY,
    article_id    VARCHAR(36),
    job_id        VARCHAR(32),
    title         VARCHAR(256)  NOT NULL,
    description   TEXT,
    thumbnail_url TEXT,
    duration_sec  INTEGER,
    style         VARCHAR(32),
    language      VARCHAR(8)    NOT NULL DEFAULT 'ja',
    status        VARCHAR(16)   NOT NULL DEFAULT 'generating',
    published_at  DATETIME(6),
    created_at    DATETIME(6)   NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at    DATETIME(6)   NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
                  ON UPDATE CURRENT_TIMESTAMP(6),
    FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
"""

_CREATE_USERS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id           VARCHAR(36)   PRIMARY KEY,
    email        VARCHAR(256)  NOT NULL UNIQUE,
    display_name VARCHAR(128)  NOT NULL,
    created_at   DATETIME(6)   NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
"""

_CREATE_WATCH_HISTORY_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS watch_history (
    id         VARCHAR(36)   PRIMARY KEY,
    user_id    VARCHAR(36)   NOT NULL,
    video_id   VARCHAR(36)   NOT NULL,
    completed  TINYINT(1)    NOT NULL DEFAULT 1,
    watched_at DATETIME(6)   NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE,
    UNIQUE KEY uq_user_video (user_id, video_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
"""

_CREATE_WATCH_LATER_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS watch_later (
    id         VARCHAR(36)   PRIMARY KEY,
    user_id    VARCHAR(36)   NOT NULL,
    video_id   VARCHAR(36)   NOT NULL,
    created_at DATETIME(6)   NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE,
    UNIQUE KEY uq_user_video (user_id, video_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
"""

_CREATE_LIKED_VIDEOS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS liked_videos (
    id         VARCHAR(36)   PRIMARY KEY,
    user_id    VARCHAR(36)   NOT NULL,
    video_id   VARCHAR(36)   NOT NULL,
    created_at DATETIME(6)   NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE,
    UNIQUE KEY uq_user_video (user_id, video_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
"""

_CREATE_COMMENTS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS comments (
    id         VARCHAR(36)   PRIMARY KEY,
    video_id   VARCHAR(36)   NOT NULL,
    user_id    VARCHAR(36)   NOT NULL,
    parent_id  VARCHAR(36),
    text       TEXT          NOT NULL,
    created_at DATETIME(6)   NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_id) REFERENCES comments(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
"""

_CREATE_COMMENT_LIKES_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS comment_likes (
    id          VARCHAR(36)   PRIMARY KEY,
    comment_id  VARCHAR(36)   NOT NULL,
    user_id     VARCHAR(36)   NOT NULL,
    created_at  DATETIME(6)   NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    FOREIGN KEY (comment_id) REFERENCES comments(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY uq_comment_user (comment_id, user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
"""

_ALTER_TABLE_SQLS = [
    "ALTER TABLE jobs ADD COLUMN source_file_names TEXT",
    "ALTER TABLE jobs ADD COLUMN csv_file_names TEXT",
    "ALTER TABLE videos ADD COLUMN language VARCHAR(8) NOT NULL DEFAULT 'ja'",
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_mysql_url(url: str) -> dict:
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
        _init_in_memory_defaults()
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
            await cur.execute(_CREATE_CATEGORIES_TABLE_SQL)
            await cur.execute(_CREATE_ARTICLES_TABLE_SQL)
            await cur.execute(_CREATE_VIDEOS_TABLE_SQL)
            await cur.execute(_CREATE_USERS_TABLE_SQL)
            await cur.execute(_CREATE_WATCH_HISTORY_TABLE_SQL)
            await cur.execute(_CREATE_WATCH_LATER_TABLE_SQL)
            await cur.execute(_CREATE_LIKED_VIDEOS_TABLE_SQL)
            await cur.execute(_CREATE_COMMENTS_TABLE_SQL)
            await cur.execute(_CREATE_COMMENT_LIKES_TABLE_SQL)
            for sql in _ALTER_TABLE_SQLS:
                try:
                    await cur.execute(sql)
                except Exception:
                    pass

    logger.info("MySQL 接続プールを初期化しました（host=%s, db=%s）", params["host"], params["db"])


def _init_in_memory_defaults():
    """開発用: デフォルトのカテゴリとサンプルデータを初期化"""
    default_categories = [
        {"id": "cat_001", "name": "セキュリティ", "slug": "security", "description": "情報セキュリティに関する社内ルール", "sort_order": 1},
        {"id": "cat_002", "name": "開発規約", "slug": "development", "description": "コーディング規約・開発プロセス", "sort_order": 2},
        {"id": "cat_003", "name": "インフラ", "slug": "infrastructure", "description": "インフラ・クラウド運用ルール", "sort_order": 3},
        {"id": "cat_004", "name": "コミュニケーション", "slug": "communication", "description": "チームコミュニケーションルール", "sort_order": 4},
        {"id": "cat_005", "name": "その他", "slug": "misc", "description": "その他の社内ルール", "sort_order": 99},
    ]
    for cat in default_categories:
        cat["created_at"] = _now()
        _categories_store[cat["id"]] = cat

    # サンプル記事・動画
    sample_articles = [
        {
            "id": "art_001",
            "title": "GitHubセキュリティ運用ガイドライン",
            "content_md": "# GitHubセキュリティ運用ガイドライン\n\n## 概要\n本ガイドラインはGitHub利用時のセキュリティルールを定めます。\n\n## アクセス管理\n- 2FA必須\n- Personal Access Tokenの適切な管理\n",
            "git_path": "security/github-security.md",
            "git_hash": "abc123",
            "category_id": "cat_001",
            "created_at": _now(),
            "updated_at": _now(),
        },
        {
            "id": "art_002",
            "title": "コードレビュー規約",
            "content_md": "# コードレビュー規約\n\n## 目的\n品質の高いコードを維持するためのレビュープロセスです。\n\n## レビュー基準\n- 機能の正確性\n- コードの可読性\n- テストの網羅性\n",
            "git_path": "development/code-review.md",
            "git_hash": "def456",
            "category_id": "cat_002",
            "created_at": _now(),
            "updated_at": _now(),
        },
        {
            "id": "art_003",
            "title": "AWSリソース命名規則",
            "content_md": "# AWSリソース命名規則\n\n## 基本原則\nすべてのAWSリソースは統一した命名規則に従います。\n\n## フォーマット\n`{環境}-{サービス}-{リソース種別}-{連番}`\n",
            "git_path": "infrastructure/aws-naming.md",
            "git_hash": "ghi789",
            "category_id": "cat_003",
            "created_at": _now(),
            "updated_at": _now(),
        },
    ]
    for art in sample_articles:
        _articles_store[art["id"]] = art

    sample_videos = [
        {
            "id": "vid_001",
            "article_id": "art_001",
            "job_id": "job_sample_001",
            "language": "ja",
            "title": "GitHubセキュリティ運用ガイドライン",
            "description": "GitHub利用時のセキュリティルール・2FAの設定・アクセストークン管理について解説します。",
            "thumbnail_url": None,
            "duration_sec": 180,
            "style": "whiteboard",
            "status": "ready",
            "published_at": _now(),
            "created_at": _now(),
            "updated_at": _now(),
            "category_id": "cat_001",
            "category_name": "セキュリティ",
            "category_slug": "security",
        },
        {
            "id": "vid_002",
            "article_id": "art_002",
            "job_id": "job_sample_002",
            "language": "ja",
            "title": "コードレビュー規約",
            "description": "品質の高いコードを維持するためのレビュープロセスと基準を解説します。",
            "thumbnail_url": None,
            "duration_sec": 240,
            "style": "classic",
            "status": "ready",
            "published_at": _now(),
            "created_at": _now(),
            "updated_at": _now(),
            "category_id": "cat_002",
            "category_name": "開発規約",
            "category_slug": "development",
        },
        {
            "id": "vid_003",
            "article_id": "art_003",
            "job_id": "job_sample_003",
            "language": "ja",
            "title": "AWSリソース命名規則",
            "description": "統一したAWSリソース命名規則の定義と実例を解説します。",
            "thumbnail_url": None,
            "duration_sec": 150,
            "style": "whiteboard",
            "status": "generating",
            "published_at": None,
            "created_at": _now(),
            "updated_at": _now(),
            "category_id": "cat_003",
            "category_name": "インフラ",
            "category_slug": "infrastructure",
        },
    ]
    for vid in sample_videos:
        _videos_store[vid["id"]] = vid


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
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            return ts.isoformat()
        return str(ts)

    source_names = row.get("source_file_names") or row.get("csv_file_names", "")

    return {
        "id": row["id"],
        "jobType": row.get("job_type", "video"),
        "csvFileNames": source_names,
        "notebookTitle": row["notebook_title"],
        "instructions": row["instructions"],
        "style": row.get("style"),
        "format": row.get("format"),
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
# Jobs CRUD
# ---------------------------------------------------------------------------


async def store_create(job: dict) -> dict:
    if not _USE_MYSQL:
        async with _store_lock:
            _store[job["id"]] = dict(job)
        return dict(job)

    source_names = job.get("csvFileNames") or job.get("sourceFileNames", "")

    async with _pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO jobs (
                    id, job_type, source_file_names, notebook_title, instructions,
                    style, format, language, timeout,
                    status, steps, current_step, error_message, callback_url,
                    created_at, updated_at, completed_at
                ) VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s
                )
                """,
                (
                    job["id"],
                    job.get("jobType", "video"),
                    source_names,
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


async def store_list(status: Optional[str] = None, job_type: Optional[str] = None) -> list[dict]:
    if not _USE_MYSQL:
        async with _store_lock:
            jobs = list(_store.values())
        jobs.sort(key=lambda j: j.get("createdAt", ""), reverse=True)
        if status and status != "all":
            jobs = [j for j in jobs if j["status"] == status]
        if job_type and job_type != "all":
            jobs = [j for j in jobs if j.get("jobType", "video") == job_type]
        return jobs

    conditions: list[str] = []
    params: list = []
    if status and status != "all":
        conditions.append("status = %s")
        params.append(status)
    if job_type and job_type != "all":
        conditions.append("job_type = %s")
        params.append(job_type)

    async with _pool.acquire() as conn:
        async with conn.cursor() as cur:
            where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
            await cur.execute(
                f"SELECT * FROM jobs {where} ORDER BY created_at DESC",
                params,
            )
            rows = await cur.fetchall()

    return [_row_to_dict(r) for r in rows]


async def store_update(job_id: str, **kwargs) -> dict:
    if not _USE_MYSQL:
        async with _store_lock:
            if job_id not in _store:
                raise KeyError(f"ジョブが見つかりません: {job_id}")
            _store[job_id].update(kwargs)
            _store[job_id]["updatedAt"] = _now()
            return dict(_store[job_id])

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

    set_clauses.append("`updated_at` = %s")
    params.append(datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f"))
    params.append(job_id)

    query = f"UPDATE jobs SET {', '.join(set_clauses)} WHERE id = %s"
    async with _pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(query, params)

    return await store_get(job_id)


def get_raw_store() -> tuple[dict, asyncio.Lock]:
    return _store, _store_lock


# ---------------------------------------------------------------------------
# Categories CRUD
# ---------------------------------------------------------------------------


async def get_categories(language: Optional[str] = None) -> list[dict]:
    if not _USE_MYSQL:
        async with _elearning_lock:
            cats = sorted(_categories_store.values(), key=lambda c: c.get("sort_order", 0))
        result = []
        for cat in cats:
            video_count = sum(
                1 for v in _videos_store.values()
                if v.get("category_id") == cat["id"]
                and v.get("status") == "ready"
                and (language is None or v.get("language", "ja") == language)
            )
            result.append({**cat, "videoCount": video_count})
        return result

    lang_filter = " AND v.language = %s" if language else ""
    params = [language] if language else []

    async with _pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"""
                SELECT c.*, COUNT(v.id) as video_count
                FROM categories c
                LEFT JOIN articles a ON a.category_id = c.id
                LEFT JOIN videos v ON v.article_id = a.id AND v.status = 'ready'{lang_filter}
                GROUP BY c.id
                ORDER BY c.sort_order ASC
                """,
                tuple(params) if params else (),
            )
            rows = await cur.fetchall()

    return [
        {
            "id": r["id"],
            "name": r["name"],
            "slug": r["slug"],
            "description": r.get("description"),
            "sortOrder": r.get("sort_order", 0),
            "videoCount": r.get("video_count", 0),
            "createdAt": str(r.get("created_at", "")),
        }
        for r in rows
    ]


async def get_category_by_slug(slug: str) -> Optional[dict]:
    if not _USE_MYSQL:
        async with _elearning_lock:
            for cat in _categories_store.values():
                if cat["slug"] == slug:
                    return dict(cat)
        return None

    async with _pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT * FROM categories WHERE slug = %s", (slug,))
            row = await cur.fetchone()
    return row


async def upsert_category(slug: str, name: str, description: Optional[str] = None) -> dict:
    if not _USE_MYSQL:
        async with _elearning_lock:
            for cat in _categories_store.values():
                if cat["slug"] == slug:
                    return dict(cat)
            cat_id = f"cat_{uuid.uuid4().hex[:8]}"
            sort_order = len(_categories_store) + 1
            new_cat = {
                "id": cat_id,
                "name": name,
                "slug": slug,
                "description": description,
                "sort_order": sort_order,
                "created_at": _now(),
            }
            _categories_store[cat_id] = new_cat
            return dict(new_cat)

    async with _pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT * FROM categories WHERE slug = %s", (slug,))
            existing = await cur.fetchone()
            if existing:
                return dict(existing)
            cat_id = str(uuid.uuid4())
            sort_order_q = "SELECT COALESCE(MAX(sort_order), 0) + 1 as next_order FROM categories"
            await cur.execute(sort_order_q)
            sort_row = await cur.fetchone()
            sort_order = sort_row["next_order"] if sort_row else 1
            await cur.execute(
                "INSERT INTO categories (id, name, slug, description, sort_order) VALUES (%s, %s, %s, %s, %s)",
                (cat_id, name, slug, description, sort_order),
            )
            await cur.execute("SELECT * FROM categories WHERE id = %s", (cat_id,))
            return dict(await cur.fetchone())


# ---------------------------------------------------------------------------
# Articles CRUD
# ---------------------------------------------------------------------------


async def upsert_article(git_path: str, title: str, content_md: str, git_hash: str, category_id: Optional[str] = None) -> dict:
    if not _USE_MYSQL:
        async with _elearning_lock:
            for art in _articles_store.values():
                if art["git_path"] == git_path:
                    art.update({
                        "title": title,
                        "content_md": content_md,
                        "git_hash": git_hash,
                        "category_id": category_id,
                        "updated_at": _now(),
                    })
                    return dict(art)
            art_id = f"art_{uuid.uuid4().hex[:8]}"
            new_art = {
                "id": art_id,
                "title": title,
                "content_md": content_md,
                "git_path": git_path,
                "git_hash": git_hash,
                "category_id": category_id,
                "created_at": _now(),
                "updated_at": _now(),
            }
            _articles_store[art_id] = new_art
            return dict(new_art)

    async with _pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT * FROM articles WHERE git_path = %s", (git_path,))
            existing = await cur.fetchone()
            now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")
            if existing:
                await cur.execute(
                    "UPDATE articles SET title=%s, content_md=%s, git_hash=%s, category_id=%s, updated_at=%s WHERE git_path=%s",
                    (title, content_md, git_hash, category_id, now_str, git_path),
                )
                await cur.execute("SELECT * FROM articles WHERE git_path = %s", (git_path,))
                return dict(await cur.fetchone())
            art_id = str(uuid.uuid4())
            await cur.execute(
                "INSERT INTO articles (id, title, content_md, git_path, git_hash, category_id, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (art_id, title, content_md, git_path, git_hash, category_id, now_str, now_str),
            )
            await cur.execute("SELECT * FROM articles WHERE id = %s", (art_id,))
            return dict(await cur.fetchone())


async def get_article_by_git_path(git_path: str) -> Optional[dict]:
    if not _USE_MYSQL:
        async with _elearning_lock:
            for art in _articles_store.values():
                if art["git_path"] == git_path:
                    return dict(art)
        return None

    async with _pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT * FROM articles WHERE git_path = %s", (git_path,))
            row = await cur.fetchone()
    return dict(row) if row else None


async def list_articles() -> list[dict]:
    if not _USE_MYSQL:
        async with _elearning_lock:
            arts = sorted(_articles_store.values(), key=lambda a: a.get("updated_at", ""), reverse=True)
        result = []
        for art in arts:
            cat = _categories_store.get(art.get("category_id", "")) if art.get("category_id") else None
            vid_list = [v for v in _videos_store.values() if v.get("article_id") == art["id"]]
            latest_video = sorted(vid_list, key=lambda v: v.get("created_at", ""), reverse=True)[0] if vid_list else None
            result.append({
                **art,
                "categoryName": cat["name"] if cat else None,
                "latestVideoId": latest_video["id"] if latest_video else None,
                "latestVideoStatus": latest_video["status"] if latest_video else None,
            })
        return result

    async with _pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("""
                SELECT a.*, c.name as category_name,
                       (SELECT v.id FROM videos v WHERE v.article_id = a.id ORDER BY v.created_at DESC LIMIT 1) as latest_video_id,
                       (SELECT v.status FROM videos v WHERE v.article_id = a.id ORDER BY v.created_at DESC LIMIT 1) as latest_video_status
                FROM articles a
                LEFT JOIN categories c ON c.id = a.category_id
                ORDER BY a.updated_at DESC
            """)
            rows = await cur.fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Videos CRUD
# ---------------------------------------------------------------------------


async def create_video(
    article_id: Optional[str],
    job_id: str,
    title: str,
    description: Optional[str] = None,
    style: Optional[str] = None,
    language: str = "ja",
) -> dict:
    if not _USE_MYSQL:
        async with _elearning_lock:
            vid_id = f"vid_{uuid.uuid4().hex[:8]}"
            cat_id = None
            cat_name = None
            cat_slug = None
            if article_id and article_id in _articles_store:
                art = _articles_store[article_id]
                cat_id = art.get("category_id")
                if cat_id and cat_id in _categories_store:
                    cat = _categories_store[cat_id]
                    cat_name = cat["name"]
                    cat_slug = cat["slug"]
            new_vid = {
                "id": vid_id,
                "article_id": article_id,
                "job_id": job_id,
                "title": title,
                "description": description,
                "thumbnail_url": None,
                "duration_sec": None,
                "style": style,
                "language": language,
                "status": "generating",
                "published_at": None,
                "created_at": _now(),
                "updated_at": _now(),
                "category_id": cat_id,
                "category_name": cat_name,
                "category_slug": cat_slug,
            }
            _videos_store[vid_id] = new_vid
            return dict(new_vid)

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")
    vid_id = str(uuid.uuid4())
    async with _pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO videos (id, article_id, job_id, title, description, style, language, status, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s, 'generating', %s, %s)",
                (vid_id, article_id, job_id, title, description, style, language, now_str, now_str),
            )
            await cur.execute("SELECT v.*, c.id as category_id, c.name as category_name, c.slug as category_slug FROM videos v LEFT JOIN articles a ON a.id = v.article_id LEFT JOIN categories c ON c.id = a.category_id WHERE v.id = %s", (vid_id,))
            return dict(await cur.fetchone())


async def update_video(video_id: str, **kwargs) -> Optional[dict]:
    if not _USE_MYSQL:
        async with _elearning_lock:
            if video_id not in _videos_store:
                return None
            _videos_store[video_id].update(kwargs)
            _videos_store[video_id]["updated_at"] = _now()
            return dict(_videos_store[video_id])

    allowed_fields = {"status", "duration_sec", "thumbnail_url", "published_at", "description"}
    set_clauses = []
    params = []
    for k, v in kwargs.items():
        if k in allowed_fields:
            set_clauses.append(f"`{k}` = %s")
            params.append(v)
    if not set_clauses:
        return await get_video(video_id)
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")
    set_clauses.append("`updated_at` = %s")
    params.append(now_str)
    params.append(video_id)
    async with _pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(f"UPDATE videos SET {', '.join(set_clauses)} WHERE id = %s", params)
    return await get_video(video_id)


async def get_video(video_id: str) -> Optional[dict]:
    if not _USE_MYSQL:
        async with _elearning_lock:
            vid = _videos_store.get(video_id)
            if not vid:
                return None
            result = dict(vid)
            # article の git_path を付与
            art_id = vid.get("article_id")
            if art_id and art_id in _articles_store:
                result["article_git_path"] = _articles_store[art_id].get("git_path")
            return result

    async with _pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("""
                SELECT v.*, c.id as category_id, c.name as category_name, c.slug as category_slug,
                       a.git_path as article_git_path
                FROM videos v
                LEFT JOIN articles a ON a.id = v.article_id
                LEFT JOIN categories c ON c.id = a.category_id
                WHERE v.id = %s
            """, (video_id,))
            row = await cur.fetchone()
    return dict(row) if row else None


async def get_video_by_job_id(job_id: str) -> Optional[dict]:
    if not _USE_MYSQL:
        async with _elearning_lock:
            for vid in _videos_store.values():
                if vid.get("job_id") == job_id:
                    return dict(vid)
        return None

    async with _pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT * FROM videos WHERE job_id = %s", (job_id,))
            row = await cur.fetchone()
    return dict(row) if row else None


async def list_videos(
    category_slug: Optional[str] = None,
    search: Optional[str] = None,
    status: Optional[str] = "ready",
    limit: int = 50,
    offset: int = 0,
    user_id: Optional[str] = None,
    language: Optional[str] = None,
    published_after: Optional[str] = None,
) -> list[dict]:
    if not _USE_MYSQL:
        async with _elearning_lock:
            vids = list(_videos_store.values())
        if status:
            vids = [v for v in vids if v.get("status") == status]
        if language:
            vids = [v for v in vids if v.get("language", "ja") == language]
        if category_slug:
            vids = [v for v in vids if v.get("category_slug") == category_slug]
        if search:
            s = search.lower()
            vids = [v for v in vids if s in v.get("title", "").lower() or s in (v.get("description") or "").lower()]
        if published_after:
            vids = [v for v in vids if (v.get("published_at") or v.get("created_at", "")) >= published_after]
        vids.sort(key=lambda v: v.get("published_at") or v.get("created_at", ""), reverse=True)
        vids = vids[offset: offset + limit]
        # article の git_path を付与
        for v in vids:
            art_id = v.get("article_id")
            if art_id and art_id in _articles_store:
                v["article_git_path"] = _articles_store[art_id].get("git_path")
        if user_id:
            watched_ids = {h["video_id"] for h in _watch_history_store if h["user_id"] == user_id}
            for v in vids:
                v["watched"] = v["id"] in watched_ids
        return vids

    conditions = []
    params = []
    if status:
        conditions.append("v.status = %s")
        params.append(status)
    if language:
        conditions.append("v.language = %s")
        params.append(language)
    if category_slug:
        conditions.append("c.slug = %s")
        params.append(category_slug)
    if search:
        conditions.append("(v.title LIKE %s OR v.description LIKE %s)")
        params.extend([f"%{search}%", f"%{search}%"])
    if published_after:
        conditions.append("COALESCE(v.published_at, v.created_at) >= %s")
        params.append(published_after)

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    async with _pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(f"""
                SELECT v.*, c.id as category_id, c.name as category_name, c.slug as category_slug,
                       a.git_path as article_git_path
                FROM videos v
                LEFT JOIN articles a ON a.id = v.article_id
                LEFT JOIN categories c ON c.id = a.category_id
                {where}
                ORDER BY v.published_at DESC, v.created_at DESC
                LIMIT %s OFFSET %s
            """, params + [limit, offset])
            rows = await cur.fetchall()

    result = [dict(r) for r in rows]
    if user_id:
        async with _pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT video_id FROM watch_history WHERE user_id = %s", (user_id,))
                watched_rows = await cur.fetchall()
        watched_ids = {r["video_id"] for r in watched_rows}
        for v in result:
            v["watched"] = v["id"] in watched_ids
    return result


# ---------------------------------------------------------------------------
# Users CRUD
# ---------------------------------------------------------------------------


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

    async with _pool.acquire() as conn:
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

    async with _pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            row = await cur.fetchone()
    return dict(row) if row else None


# ---------------------------------------------------------------------------
# Watch History CRUD
# ---------------------------------------------------------------------------


async def record_watch(user_id: str, video_id: str, completed: bool = True) -> dict:
    if not _USE_MYSQL:
        async with _elearning_lock:
            for record in _watch_history_store:
                if record["user_id"] == user_id and record["video_id"] == video_id:
                    record["completed"] = completed
                    record["watched_at"] = _now()
                    return dict(record)
            record_id = str(uuid.uuid4())
            new_record = {
                "id": record_id,
                "user_id": user_id,
                "video_id": video_id,
                "completed": completed,
                "watched_at": _now(),
            }
            _watch_history_store.append(new_record)
            return dict(new_record)

    record_id = str(uuid.uuid4())
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")
    async with _pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """INSERT INTO watch_history (id, user_id, video_id, completed, watched_at) VALUES (%s, %s, %s, %s, %s)
                   ON DUPLICATE KEY UPDATE completed = %s, watched_at = %s""",
                (record_id, user_id, video_id, completed, now_str, completed, now_str),
            )
    return {"id": record_id, "user_id": user_id, "video_id": video_id, "completed": completed, "watched_at": now_str}


async def get_watch_history(user_id: str, limit: int = 50) -> list[dict]:
    if not _USE_MYSQL:
        async with _elearning_lock:
            history = [h for h in _watch_history_store if h["user_id"] == user_id]
        history.sort(key=lambda h: h["watched_at"], reverse=True)
        history = history[:limit]
        result = []
        for h in history:
            vid = _videos_store.get(h["video_id"])
            if vid:
                result.append({
                    **h,
                    "videoTitle": vid["title"],
                    "videoStatus": vid["status"],
                    "categoryName": vid.get("category_name"),
                    "categorySlug": vid.get("category_slug"),
                })
        return result

    async with _pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("""
                SELECT wh.*, v.title as video_title, v.status as video_status,
                       c.name as category_name, c.slug as category_slug
                FROM watch_history wh
                JOIN videos v ON v.id = wh.video_id
                LEFT JOIN articles a ON a.id = v.article_id
                LEFT JOIN categories c ON c.id = a.category_id
                WHERE wh.user_id = %s
                ORDER BY wh.watched_at DESC
                LIMIT %s
            """, (user_id, limit))
            rows = await cur.fetchall()
    return [dict(r) for r in rows]


async def get_video_watch_counts(video_id: str) -> tuple[int, int]:
    """動画の視聴者数（ユニークユーザー数）と視聴回数を返す"""
    if not _USE_MYSQL:
        async with _elearning_lock:
            records = [h for h in _watch_history_store if h["video_id"] == video_id]
        count = len(records)
        return (count, count)  # user_video is unique, so same

    async with _pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT COUNT(*) as cnt FROM watch_history WHERE video_id = %s",
                (video_id,),
            )
            row = await cur.fetchone()
    cnt = row["cnt"] if row else 0
    return (cnt, cnt)  # user_video unique → viewer = view count


# ---------------------------------------------------------------------------
# Watch Later CRUD
# ---------------------------------------------------------------------------


async def toggle_watch_later(user_id: str, video_id: str) -> bool:
    """後で見るをトグル。追加ならTrue、削除ならFalseを返す"""
    if not _USE_MYSQL:
        async with _elearning_lock:
            existing = next((r for r in _watch_later_store if r["user_id"] == user_id and r["video_id"] == video_id), None)
            if existing:
                _watch_later_store.remove(existing)
                return False
            _watch_later_store.append({
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "video_id": video_id,
                "created_at": _now(),
            })
            return True

    async with _pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT id FROM watch_later WHERE user_id = %s AND video_id = %s", (user_id, video_id))
            row = await cur.fetchone()
            if row:
                await cur.execute("DELETE FROM watch_later WHERE user_id = %s AND video_id = %s", (user_id, video_id))
                return False
            record_id = str(uuid.uuid4())
            now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")
            await cur.execute(
                "INSERT INTO watch_later (id, user_id, video_id, created_at) VALUES (%s, %s, %s, %s)",
                (record_id, user_id, video_id, now_str),
            )
            return True


async def get_watch_later_ids(user_id: str) -> set[str]:
    if not _USE_MYSQL:
        async with _elearning_lock:
            return {r["video_id"] for r in _watch_later_store if r["user_id"] == user_id}

    async with _pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT video_id FROM watch_later WHERE user_id = %s", (user_id,))
            rows = await cur.fetchall()
    return {r["video_id"] for r in rows}


async def get_watch_later_videos(user_id: str, limit: int = 100) -> list[dict]:
    if not _USE_MYSQL:
        async with _elearning_lock:
            wl = [r for r in _watch_later_store if r["user_id"] == user_id]
            wl.sort(key=lambda r: r["created_at"], reverse=True)
            result = []
            for r in wl[:limit]:
                vid = _videos_store.get(r["video_id"])
                if vid:
                    vid_copy = dict(vid)
                    vid_copy["watch_later_at"] = r["created_at"]
                    result.append(vid_copy)
            return result

    async with _pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("""
                SELECT v.*, c.id as category_id, c.name as category_name, c.slug as category_slug,
                       a.git_path as article_git_path, wl.created_at as watch_later_at
                FROM watch_later wl
                JOIN videos v ON v.id = wl.video_id
                LEFT JOIN articles a ON a.id = v.article_id
                LEFT JOIN categories c ON c.id = a.category_id
                WHERE wl.user_id = %s
                ORDER BY wl.created_at DESC
                LIMIT %s
            """, (user_id, limit))
            rows = await cur.fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Liked Videos CRUD
# ---------------------------------------------------------------------------


async def toggle_liked_video(user_id: str, video_id: str) -> bool:
    """高く評価をトグル。追加ならTrue、削除ならFalseを返す"""
    if not _USE_MYSQL:
        async with _elearning_lock:
            existing = next((r for r in _liked_videos_store if r["user_id"] == user_id and r["video_id"] == video_id), None)
            if existing:
                _liked_videos_store.remove(existing)
                return False
            _liked_videos_store.append({
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "video_id": video_id,
                "created_at": _now(),
            })
            return True

    async with _pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT id FROM liked_videos WHERE user_id = %s AND video_id = %s", (user_id, video_id))
            row = await cur.fetchone()
            if row:
                await cur.execute("DELETE FROM liked_videos WHERE user_id = %s AND video_id = %s", (user_id, video_id))
                return False
            record_id = str(uuid.uuid4())
            now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")
            await cur.execute(
                "INSERT INTO liked_videos (id, user_id, video_id, created_at) VALUES (%s, %s, %s, %s)",
                (record_id, user_id, video_id, now_str),
            )
            return True


async def get_liked_video_ids(user_id: str) -> set[str]:
    if not _USE_MYSQL:
        async with _elearning_lock:
            return {r["video_id"] for r in _liked_videos_store if r["user_id"] == user_id}

    async with _pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT video_id FROM liked_videos WHERE user_id = %s", (user_id,))
            rows = await cur.fetchall()
    return {r["video_id"] for r in rows}


async def get_liked_videos(user_id: str, limit: int = 100) -> list[dict]:
    if not _USE_MYSQL:
        async with _elearning_lock:
            liked = [r for r in _liked_videos_store if r["user_id"] == user_id]
            liked.sort(key=lambda r: r["created_at"], reverse=True)
            result = []
            for r in liked[:limit]:
                vid = _videos_store.get(r["video_id"])
                if vid:
                    result.append(dict(vid))
            return result

    async with _pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("""
                SELECT v.*, c.id as category_id, c.name as category_name, c.slug as category_slug,
                       a.git_path as article_git_path
                FROM liked_videos lv
                JOIN videos v ON v.id = lv.video_id
                LEFT JOIN articles a ON a.id = v.article_id
                LEFT JOIN categories c ON c.id = a.category_id
                WHERE lv.user_id = %s
                ORDER BY lv.created_at DESC
                LIMIT %s
            """, (user_id, limit))
            rows = await cur.fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------


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

    async with _pool.acquire() as conn:
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
    async with _pool.acquire() as conn:
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
            async with _pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        "SELECT video_id FROM comments WHERE id = %s", (parent_id,)
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
    async with _pool.acquire() as conn:
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
    async with _pool.acquire() as conn:
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
        async with _pool.acquire() as conn:
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
        async with _pool.acquire() as conn:
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
