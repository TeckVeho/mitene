"""
Wiki同期モジュール

Gitリポジトリ内の .md ファイルを監視し、変更があった場合に:
1. articles テーブルを更新
2. NotebookLM 動画生成ジョブを自動投入
3. Slack 通知（モック）を送信

環境変数:
  WIKI_GIT_REPO_URL   - Git リポジトリ URL
  WIKI_GIT_LOCAL_PATH - ローカルクローン先パス（デフォルト: ./wiki-repo）
  WIKI_GIT_BRANCH     - ブランチ名（デフォルト: main）

resolve_storage_kind()==gcs のとき、wiki .md は GCS_BUCKET 上の固定プレフィックス ``wiki-repo/`` 配下（例: gs://.../wiki-repo/security/guide.md）。
"""

import asyncio
import logging
import os
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path
from typing import Optional
from urllib.parse import urlsplit, urlunsplit

import storage as storage_mod
from resolve_storage import resolve_storage_kind

logger = logging.getLogger(__name__)

WIKI_GIT_REPO_URL: Optional[str] = os.environ.get("WIKI_GIT_REPO_URL")
WIKI_GIT_LOCAL_PATH: str = os.environ.get("WIKI_GIT_LOCAL_PATH", "./wiki-repo")
WIKI_GIT_BRANCH: str = os.environ.get("WIKI_GIT_BRANCH", "main")
WIKI_GIT_TOKEN: Optional[str] = os.environ.get("WIKI_GIT_TOKEN")
WIKI_GIT_HTTP_USERNAME: str = os.environ.get("WIKI_GIT_HTTP_USERNAME", "x-access-token")

# GCS wiki モード時のオブジェクトキー先頭（環境変数では変更しない）
WIKI_GCS_OBJECT_PREFIX: str = "wiki-repo/"

# カテゴリマッピング: ディレクトリ名 → カテゴリスラッグ・名前
CATEGORY_MAP: dict[str, tuple[str, str]] = {
    "security": ("security", "セキュリティ"),
    "development": ("development", "開発規約"),
    "dev": ("development", "開発規約"),
    "infrastructure": ("infrastructure", "インフラ"),
    "infra": ("infrastructure", "インフラ"),
    "communication": ("communication", "コミュニケーション"),
    "misc": ("misc", "その他"),
    "general": ("misc", "その他"),
}


def _wiki_uses_gcs() -> bool:
    """GCS_BUCKET 設定済みで resolve_storage_kind が gcs のとき True（Cloud Run 等）。"""
    return resolve_storage_kind() == "gcs"


def _list_all_md_rel_paths_gcs() -> list[str]:
    """GCS 上のプレフィックス配下の .md を相対パス一覧で返す。"""
    prefix = WIKI_GCS_OBJECT_PREFIX
    keys = storage_mod.gcs_list_object_keys_under_prefix(prefix)
    rels: list[str] = []
    for k in keys:
        if not k.endswith(".md"):
            continue
        rel = k[len(prefix) :].replace("\\", "/")
        if rel:
            rels.append(rel)
    return rels


def _gcs_object_key_for_rel(rel_path: str) -> str:
    rel = rel_path.strip().lstrip("/").replace("\\", "/")
    return WIKI_GCS_OBJECT_PREFIX + rel


def _build_wiki_directories_from_md_files(md_files: list[str]) -> list[dict]:
    """get_wiki_directories と同形式のディレクトリ一覧を .md 相対パスから構築する。"""
    if not md_files:
        return []

    dir_counts: dict[str, int] = {}
    dir_files: dict[str, list[dict[str, str]]] = {}
    for rel_path in md_files:
        parts = Path(rel_path).parts
        if len(parts) == 1:
            dir_key = ""
        else:
            dir_key = parts[0]
        dir_counts[dir_key] = dir_counts.get(dir_key, 0) + 1
        dir_files.setdefault(dir_key, []).append(
            {
                "fileName": Path(rel_path).name,
                "path": rel_path,
            }
        )

    result = []
    if "" in dir_counts:
        result.append(
            {
                "path": "",
                "label": "ルート",
                "count": dir_counts[""],
                "files": sorted(dir_files.get("", []), key=lambda f: f["path"]),
            }
        )
    for d in sorted(dir_counts.keys()):
        if d:
            result.append(
                {
                    "path": d,
                    "label": d,
                    "count": dir_counts[d],
                    "files": sorted(dir_files.get(d, []), key=lambda f: f["path"]),
                }
            )
    return result


def _run_git(cmd: list[str], cwd: str) -> subprocess.CompletedProcess:
    """gitコマンドを実行する"""
    return subprocess.run(
        ["git"] + cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=60,
    )


def _redact_url_for_log(url: str) -> str:
    """URL内の認証情報をマスクしてログ出力用に返す。"""
    try:
        parsed = urlsplit(url)
        if parsed.username is None and parsed.password is None:
            return url
        host = parsed.hostname or ""
        if parsed.port is not None:
            host = f"{host}:{parsed.port}"
        redacted_netloc = f"***:***@{host}" if host else "***:***"
        return urlunsplit((parsed.scheme, redacted_netloc, parsed.path, parsed.query, parsed.fragment))
    except Exception:
        return "***"


def _auth_url_for_git_operations(repo_url: str) -> str:
    """HTTPS URL にトークン認証情報を付与したURLを返す。"""
    token = (WIKI_GIT_TOKEN or "").strip()
    if not repo_url or not token:
        return repo_url

    try:
        parsed = urlsplit(repo_url)
    except Exception:
        return repo_url

    if parsed.scheme not in ("http", "https"):
        return repo_url

    # URL 既存認証情報がある場合は上書きしない
    if parsed.username is not None:
        return repo_url

    host = parsed.hostname or ""
    if not host:
        return repo_url

    if parsed.port is not None:
        host = f"{host}:{parsed.port}"

    username = (WIKI_GIT_HTTP_USERNAME or "x-access-token").strip()
    netloc = f"{username}:{token}@{host}"
    return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))


def _get_commit_hash(repo_path: str, quiet: bool = False) -> Optional[str]:
    """現在の HEAD commit hash を返す"""
    try:
        result = _run_git(["rev-parse", "HEAD"], repo_path)
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception as e:
        if not quiet:
            logger.warning("commit hash 取得失敗: %s", e)
    return None


def _clone_or_pull(
    repo_url: str, local_path: str, branch: str, quiet: bool = False
) -> tuple[bool, Optional[str]]:
    """
    リポジトリをcloneまたはpullする。
    Returns: (成功フラグ, 新しいcommit hash or None)
    """
    path = Path(local_path)

    if not shutil.which("git"):
        if not quiet:
            logger.warning("git コマンドが見つかりません。wiki 同期をスキップします。")
        if not path.exists():
            return False, None
        old_hash = _get_commit_hash(str(path), quiet=quiet)
        return True, old_hash

    auth_repo_url = _auth_url_for_git_operations(repo_url)

    if not path.exists():
        if not repo_url:
            if not quiet:
                logger.warning(
                    "WIKI_GIT_REPO_URL が設定されていないため、既存ディレクトリを使用します"
                )
            return False, None
        if not quiet:
            logger.info(
                "Git リポジトリをクローン中: %s → %s",
                _redact_url_for_log(auth_repo_url),
                local_path,
            )
        path.parent.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            ["git", "clone", "--branch", branch, auth_repo_url, str(path)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            if not quiet:
                logger.error("git clone 失敗: %s", result.stderr)
            return False, None
        # clone 後は origin をクリーンURLに戻し、token を .git/config に残さない
        if auth_repo_url != repo_url:
            set_url_result = _run_git(["remote", "set-url", "origin", repo_url], str(path))
            if set_url_result.returncode != 0 and not quiet:
                logger.warning("git remote set-url 失敗: %s", set_url_result.stderr)
        return True, _get_commit_hash(str(path), quiet=quiet)

    # 既存リポジトリを同期(fetch & reset --hard)
    old_hash = _get_commit_hash(str(path), quiet=quiet)
    if not quiet:
        logger.info("Git 同期実行中: %s (branch: %s)", local_path, branch)
    pull_target = auth_repo_url if auth_repo_url else "origin"
    if pull_target != "origin" and not quiet:
        logger.info("Git fetch 実行先: %s", _redact_url_for_log(pull_target))
    
    fetch_result = _run_git(["fetch", pull_target, branch], str(path))
    if fetch_result.returncode != 0:
        if not quiet:
            logger.warning("git fetch 失敗（オフラインまたは権限エラー）: %s", fetch_result.stderr)
        return True, old_hash  # エラーでも既存ファイルを処理
    
    reset_result = _run_git(["reset", "--hard", "FETCH_HEAD"], str(path))
    if reset_result.returncode != 0:
        if not quiet:
            logger.warning("git reset 失敗: %s", reset_result.stderr)
        return True, old_hash

    new_hash = _get_commit_hash(str(path), quiet=quiet)
    return True, new_hash


def _extract_title(content: str, filename: str) -> str:
    """Markdownの最初の見出しをタイトルとして抽出する"""
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
    return Path(filename).stem.replace("-", " ").replace("_", " ").title()


def _infer_category(git_path: str) -> tuple[str, str]:
    """ファイルパスからカテゴリスラッグと名前を推定する"""
    parts = Path(git_path).parts
    if len(parts) > 1:
        dir_name = parts[0].lower()
        if dir_name in CATEGORY_MAP:
            return CATEGORY_MAP[dir_name]
    return ("misc", "その他")


_sync_status: dict = {
    "last_sync_at": None,
    "last_hash": None,
    "total_articles": 0,
    "is_syncing": False,
    "wiki_source_syncing": False,
    "error": None,
}

_sync_from_git_lock = threading.Lock()


def get_sync_status() -> dict:
    """現在の同期状態を返す（is_syncing はディレクトリ同期と Git ソース同期のいずれかで True）。"""
    out = dict(_sync_status)
    out["is_syncing"] = bool(
        _sync_status["is_syncing"] or _sync_status.get("wiki_source_syncing")
    )
    out.pop("wiki_source_syncing", None)
    return out


def _get_all_md_files(repo_path: str) -> list[str]:
    """リポジトリ内の全 .md ファイルの相対パスを返す"""
    result = _run_git(["ls-files", "*.md"], repo_path)
    if result.returncode == 0 and result.stdout.strip():
        return [f for f in result.stdout.strip().split("\n") if f.endswith(".md")]
    md_files = list(Path(repo_path).rglob("*.md"))
    return [str(f.relative_to(repo_path)) for f in md_files]


def _filter_md_files_by_directory(md_files: list[str], relative_dir: str) -> list[str]:
    """
    指定ディレクトリ配下の .md ファイルのみを返す。
    relative_dir が "" の場合はルート直下の .md のみ。
    relative_dir が "security" の場合は security/ 配下の .md のみ。
    """
    if not relative_dir or relative_dir == ".":
        return [f for f in md_files if "/" not in f and f.endswith(".md")]
    prefix = relative_dir.rstrip("/") + "/"
    return [f for f in md_files if f.startswith(prefix) and f.endswith(".md")]


def _normalize_sync_path(path_value: str) -> str:
    """sync API の path を正規化する（先頭/末尾の余分な区切りを除去）。"""
    if not path_value:
        return ""
    normalized = path_value.strip().replace("\\", "/")
    normalized = normalized.lstrip("/")
    if normalized != ".":
        normalized = normalized.rstrip("/")
    return "" if normalized == "." else normalized


def _resolve_target_md_files(md_files: list[str], path_input: str) -> tuple[list[str], str]:
    """
    path_input から対象 .md ファイルを解決する。
    戻り値: (target_files, mode) where mode is "directory" or "single_file"
    """
    normalized = _normalize_sync_path(path_input)
    if normalized.endswith(".md"):
        return ([normalized] if normalized in md_files else []), "single_file"
    return _filter_md_files_by_directory(md_files, normalized), "directory"


def get_wiki_directories() -> list[dict]:
    """
    リポジトリ内の .md を含むディレクトリ一覧を返す。
    返却形式: [{"path": "", "label": "ルート", "count": 2}, {"path": "security", "label": "security", "count": 5}, ...]

    Git モード: 一覧取得のたびに clone または pull（管理画面アクセス時に最新化。負荷は管理ユーザー少数を想定）。
    GCS モード: プレフィックス配下を列挙（オブジェクトストレージがソース）。
    """
    if _wiki_uses_gcs():
        md_files = _list_all_md_rel_paths_gcs()
        return _build_wiki_directories_from_md_files(md_files)

    local_path = os.path.abspath(WIKI_GIT_LOCAL_PATH)
    # 一覧取得のたびに clone/pull（ログは quiet で抑制）
    _clone_or_pull(WIKI_GIT_REPO_URL or "", local_path, WIKI_GIT_BRANCH, quiet=True)
    if not Path(local_path).exists():
        return []

    md_files = _get_all_md_files(local_path)
    return _build_wiki_directories_from_md_files(md_files)


def sync_wiki_from_git_source() -> dict:
    """
    管理画面「Wiki を Git から同期」用。
    - Git モード: WIKI_GIT_LOCAL_PATH で clone/pull。
    - GCS モード: 一時ディレクトリに clone/pull し、追跡 .md を wiki-repo/ にアップロード。
    """
    repo_url = (WIKI_GIT_REPO_URL or "").strip()
    if not repo_url:
        msg = "WIKI_GIT_REPO_URL が設定されていません"
        _sync_status["error"] = msg
        return {"ok": False, "message": msg}

    with _sync_from_git_lock:
        if _sync_status["is_syncing"] or _sync_status.get("wiki_source_syncing"):
            return {"ok": False, "message": "同期が既に実行中です"}
        _sync_status["wiki_source_syncing"] = True
        _sync_status["error"] = None

    try:

        if _wiki_uses_gcs():
            with tempfile.TemporaryDirectory(prefix="wiki-git-") as tmp:
                tmp_repo = os.path.join(tmp, "repo")
                ok, commit_hash = _clone_or_pull(
                    repo_url, tmp_repo, WIKI_GIT_BRANCH, quiet=True
                )
                if not ok or not Path(tmp_repo).exists():
                    msg = "Git clone/pull に失敗しました"
                    _sync_status["error"] = msg
                    return {"ok": False, "message": msg}

                md_files = _get_all_md_files(tmp_repo)
                uploaded = 0
                for rel in md_files:
                    rel_posix = rel.replace("\\", "/")
                    full = Path(tmp_repo) / rel_posix
                    if not full.is_file():
                        continue
                    data = full.read_bytes()
                    key = WIKI_GCS_OBJECT_PREFIX + rel_posix
                    storage_mod.gcs_upload_bytes(
                        key, data, content_type="text/markdown"
                    )
                    uploaded += 1
                    logger.debug("GCS wiki upload: %s", key)

                _sync_status["last_sync_at"] = _now()
                _sync_status["last_hash"] = commit_hash
                logger.info(
                    "wiki Git→GCS 同期完了: %s 件 gs://%s/%s*",
                    uploaded,
                    getattr(storage_mod, "GCS_BUCKET", ""),
                    WIKI_GCS_OBJECT_PREFIX,
                )
                return {
                    "ok": True,
                    "message": f"{uploaded} 件の .md を GCS に反映しました",
                    "uploaded": uploaded,
                    "hash": commit_hash,
                }

        local_path = os.path.abspath(WIKI_GIT_LOCAL_PATH)
        ok, commit_hash = _clone_or_pull(repo_url, local_path, WIKI_GIT_BRANCH, quiet=True)
        if not ok and not Path(local_path).exists():
            msg = "Wiki リポジトリの取得に失敗しました"
            _sync_status["error"] = msg
            return {"ok": False, "message": msg}

        _sync_status["last_sync_at"] = _now()
        _sync_status["last_hash"] = commit_hash
        return {
            "ok": True,
            "message": "Git の wiki を取得しました",
            "hash": commit_hash,
        }

    except Exception as exc:
        err = str(exc)
        _sync_status["error"] = err
        logger.exception("sync_wiki_from_git_source 失敗")
        return {"ok": False, "message": err}
    finally:
        with _sync_from_git_lock:
            _sync_status["wiki_source_syncing"] = False


async def sync_wiki_from_directory(
    relative_dir: str,
    target_paths: Optional[list[str]] = None,
    store_update_fn=None,
    run_job_fn=None,
    dispatch_video_job_fn=None,
    semaphore=None,
    outputs_dir: Optional[Path] = None,
    sync_id: Optional[str] = None,
) -> dict:
    """
    指定 path 配下、または target_paths で指定した .md ファイルを同期し、動画生成ジョブを投入する。
    relative_dir はディレクトリまたは .md ファイルの相対 path を受け取る。
    """
    import database as db

    if _sync_status["is_syncing"] or _sync_status.get("wiki_source_syncing"):
        return {"status": "already_running", "message": "同期が既に実行中です"}

    _sync_status["is_syncing"] = True
    _sync_status["error"] = None

    try:
        local_path = os.path.abspath(WIKI_GIT_LOCAL_PATH)
        normalized_path = _normalize_sync_path(relative_dir)
        normalized_target_paths = [
            _normalize_sync_path(p) for p in (target_paths or []) if _normalize_sync_path(p).endswith(".md")
        ]
        if _wiki_uses_gcs():
            # GCS モードでは Git commit SHA の代わりに固定値を保存する
            new_hash = "gcs"
            all_md = _list_all_md_rel_paths_gcs()
            if not all_md:
                _sync_status["is_syncing"] = False
                return {"status": "skipped", "message": "GCS に .md がありません"}
        else:
            success, new_hash = _clone_or_pull(
                WIKI_GIT_REPO_URL or "", local_path, WIKI_GIT_BRANCH, quiet=True
            )

            if not success and not Path(local_path).exists():
                msg = f"Wiki リポジトリが見つかりません: {local_path}"
                _sync_status["error"] = msg
                _sync_status["is_syncing"] = False
                return {"status": "error", "message": msg}

            if not Path(local_path).exists():
                _sync_status["is_syncing"] = False
                return {"status": "skipped", "message": "リポジトリが存在しません"}

            all_md = _get_all_md_files(local_path)
        if normalized_target_paths:
            all_md_set = set(all_md)
            deduped_paths = list(dict.fromkeys(normalized_target_paths))
            target_files = [p for p in deduped_paths if p in all_md_set]
            sync_mode = "multi_file"
        else:
            target_files, sync_mode = _resolve_target_md_files(all_md, normalized_path)
        if not target_files:
            _sync_status["is_syncing"] = False
            if sync_mode == "multi_file":
                dir_label = "選択ファイル"
            else:
                dir_label = "ルート" if not normalized_path else normalized_path
            return {
                "status": "no_files",
                "message": f"{dir_label} に .md ファイルがありません",
                "mode": sync_mode,
            }

        processed = 0
        jobs_created = 0

        for rel_path in target_files:
            if _wiki_uses_gcs():
                try:
                    raw = storage_mod.gcs_download_bytes(_gcs_object_key_for_rel(rel_path))
                except Exception:
                    continue
            else:
                full_path = Path(local_path) / rel_path
                if not full_path.exists():
                    continue
                try:
                    raw = full_path.read_bytes()
                except Exception:
                    continue

            try:
                content = raw.decode("utf-8", errors="replace")
                title = _extract_title(content, rel_path)
                cat_slug, cat_name = _infer_category(rel_path)

                cat = await db.upsert_category(cat_slug, cat_name)
                cat_id = cat["id"]

                article = await db.upsert_article(
                    git_path=rel_path,
                    title=title,
                    content_md=content,
                    git_hash=new_hash or "unknown",
                    category_id=cat_id,
                )
                processed += 1

                if store_update_fn and outputs_dir and (dispatch_video_job_fn or run_job_fn):
                    import uuid as _uuid
                    from datetime import datetime, timezone

                    uploads_dir = outputs_dir.parent / "uploads"
                    uploads_dir.mkdir(exist_ok=True)
                    md_filename = Path(rel_path).name

                    INSTRUCTIONS: dict[str, str] = {
                        "ja": f"{title}の内容をわかりやすくAI動画解説してください。要点を整理してエンジニアが理解しやすいように説明してください。",
                        "vi": f"Hãy giải thích nội dung của {title} một cách dễ hiểu bằng video AI. Sắp xếp các điểm chính và giải thích rõ ràng để kỹ sư dễ nắm bắt.",
                    }
                    DESCRIPTIONS: dict[str, str] = {
                        "ja": f"{title}に関する社内ルール解説動画",
                        "vi": f"Video giải thích quy tắc nội bộ về {title}",
                    }

                    for lang in ("ja", "vi"):
                        job_id = f"job_{_uuid.uuid4().hex[:12]}"
                        now = datetime.now(timezone.utc).isoformat()

                        local_md_path = uploads_dir / f"{job_id}_{md_filename}"
                        local_md_path.write_bytes(raw)
                        output_path = outputs_dir / f"{job_id}.mp4"

                        initial_steps = [
                            {"id": "create_notebook", "label": "ノートブック作成", "status": "pending"},
                            {"id": "add_source", "label": "ドキュメント追加", "status": "pending"},
                            {"id": "generate_video", "label": "動画生成開始", "status": "pending"},
                            {"id": "wait_completion", "label": "生成完了待機", "status": "pending"},
                            {"id": "download_ready", "label": "ダウンロード準備完了", "status": "pending"},
                        ]

                        job: dict = {
                            "id": job_id,
                            "jobType": "video",
                            "csvFileNames": md_filename,
                            "notebookTitle": title,
                            "instructions": INSTRUCTIONS[lang],
                            "style": "whiteboard",
                            "format": "explainer",
                            "language": lang,
                            "timeout": 3600,
                            "status": "pending",
                            "steps": initial_steps,
                            "currentStep": None,
                            "errorMessage": None,
                            "createdAt": now,
                            "updatedAt": now,
                            "completedAt": None,
                            "callbackUrl": None,
                        }

                        await db.store_create(job)

                        await db.create_video(
                            article_id=article["id"],
                            job_id=job_id,
                            title=title,
                            description=DESCRIPTIONS[lang],
                            style="whiteboard",
                            language=lang,
                        )

                        if dispatch_video_job_fn:
                            await dispatch_video_job_fn(
                                job_id=job_id,
                                run_job_fn=run_job_fn,
                                store_update=store_update_fn,
                                source_paths=[local_md_path],
                                output_path=output_path,
                                notebook_title=title,
                                instructions=job["instructions"],
                                style="whiteboard",
                                video_format="explainer",
                                language=lang,
                                timeout=3600,
                                callback_url=None,
                                semaphore=semaphore,
                            )
                        elif run_job_fn:
                            asyncio.create_task(
                                run_job_fn(
                                    job_id=job_id,
                                    source_paths=[local_md_path],
                                    output_path=output_path,
                                    notebook_title=title,
                                    instructions=job["instructions"],
                                    style="whiteboard",
                                    video_format="explainer",
                                    language=lang,
                                    timeout=3600,
                                    store_update=store_update_fn,
                                    semaphore=semaphore,
                                )
                            )
                        jobs_created += 1

            except Exception:
                pass

        _sync_status["last_sync_at"] = _now()
        _sync_status["last_hash"] = new_hash
        _sync_status["total_articles"] = processed
        _sync_status["is_syncing"] = False

        return {
            "status": "success",
            "processed": processed,
            "jobs_created": jobs_created,
            "hash": new_hash,
            "mode": sync_mode,
            "path": normalized_path,
            "paths": target_files if sync_mode == "multi_file" else None,
        }

    except Exception as exc:
        _sync_status["error"] = str(exc)
        _sync_status["is_syncing"] = False
        return {"status": "error", "message": str(exc)}


def _now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()
