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

# Submodules must use ``connection._pool``, not ``from .connection import _pool``
# (the latter binds None at import time before init_db runs).
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
