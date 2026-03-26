"""
外部API v1 ルーター
他システムから本システムの動画生成処理を実行するためのエンドポイント群。

認証: X-API-Key ヘッダー（環境変数 NOTEVIDEO_API_KEYS で設定）
"""

import asyncio
import base64
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import RedirectResponse, FileResponse
from pydantic import BaseModel, field_validator

from auth import verify_api_key
import storage as storage_mod

# ---------------------------------------------------------------------------
# Paths（ローカルストレージモード時に使用）
# ---------------------------------------------------------------------------

_BASE_DIR = Path(__file__).parent
_UPLOADS_DIR = _BASE_DIR / "uploads"
_OUTPUTS_DIR = _BASE_DIR / "outputs"

# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class MdFileInput(BaseModel):
    """Markdownファイルの指定方法（Base64またはサーバーパス）"""

    filename: str
    content_base64: Optional[str] = None
    file_path: Optional[str] = None

    @field_validator("filename")
    @classmethod
    def validate_filename(cls, v: str) -> str:
        if not (v.endswith(".md") or v.endswith(".csv")):
            raise ValueError("ファイル名は .md または .csv で終わる必要があります")
        return v

    def model_post_init(self, __context) -> None:
        if not self.content_base64 and not self.file_path:
            raise ValueError("content_base64 または file_path のいずれかを指定してください")


class ExternalJobRequest(BaseModel):
    """外部APIからのジョブ作成リクエスト（JSON形式）"""

    notebook_title: str = "E-learningコンテンツ"
    instructions: str = "MarkdownドキュメントをわかりやすくAI動画解説してください"
    style: str = "whiteboard"
    format: str = "explainer"
    language: str = "ja"
    timeout: int = 3600
    callback_url: Optional[str] = None
    source_files: list[MdFileInput]


class JobResponse(BaseModel):
    """動画ジョブレスポンス"""

    id: str
    sourceFileNames: str
    notebookTitle: str
    instructions: str
    style: str
    format: str
    language: str
    timeout: int
    status: str
    steps: list[dict]
    currentStep: Optional[str] = None
    errorMessage: Optional[str] = None
    createdAt: str
    updatedAt: str
    completedAt: Optional[str] = None
    callbackUrl: Optional[str] = None


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter(
    prefix="/api/v1",
    tags=["External API v1"],
    dependencies=[Depends(verify_api_key)],
)

_store_fns: dict = {}


def register_store_functions(
    store_create_fn,
    store_get_fn,
    store_list_fn,
    store_update_fn,
    initial_steps_fn,
    run_job_fn,
    semaphore: asyncio.Semaphore,
    audio_initial_steps_fn=None,
    run_audio_job_fn=None,
    raw_store: dict | None = None,
    raw_lock: asyncio.Lock | None = None,
) -> None:
    """main.py の起動時にストア関数を登録する"""
    _store_fns["create"] = store_create_fn
    _store_fns["get"] = store_get_fn
    _store_fns["list"] = store_list_fn
    _store_fns["update"] = store_update_fn
    _store_fns["initial_steps"] = initial_steps_fn
    _store_fns["run_job"] = run_job_fn
    _store_fns["semaphore"] = semaphore


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/jobs",
    response_model=JobResponse,
    status_code=201,
    summary="ジョブ作成（JSON形式）",
    description=(
        "MarkdownファイルをBase64エンコードまたはサーバーパスで指定し、動画生成ジョブを作成します。\n\n"
        "ジョブIDを返します。完了通知が必要な場合は `callback_url` を指定してください。"
    ),
)
async def create_job_v1(
    request: ExternalJobRequest,
    background_tasks: BackgroundTasks,
    _api_key: str = Depends(verify_api_key),
) -> JobResponse:
    if not request.source_files:
        raise HTTPException(status_code=400, detail="source_files を1つ以上指定してください")

    job_id = f"job_{uuid.uuid4().hex[:12]}"
    now = _now()

    source_paths: list[Path] = []
    file_names: list[str] = []

    for file_input in request.source_files:
        safe_name = file_input.filename.replace("/", "_").replace("\\", "_")

        if file_input.content_base64:
            try:
                content = base64.b64decode(file_input.content_base64)
            except Exception:
                raise HTTPException(
                    status_code=400,
                    detail=f"{safe_name}: content_base64 のデコードに失敗しました。",
                )
            local_path = storage_mod.save_file_locally(_UPLOADS_DIR, job_id, safe_name, content)
            storage_mod.upload_csv_to_s3(job_id, safe_name, content)

        elif file_input.file_path:
            src = Path(file_input.file_path)
            if not src.exists():
                raise HTTPException(
                    status_code=400,
                    detail=f"指定されたファイルが見つかりません: {file_input.file_path}",
                )
            local_path = _UPLOADS_DIR / f"{job_id}_{safe_name}"
            shutil.copy2(src, local_path)
            content = local_path.read_bytes()
            storage_mod.upload_csv_to_s3(job_id, safe_name, content)
        else:
            raise HTTPException(status_code=400, detail=f"{safe_name}: ファイル内容が指定されていません")

        source_paths.append(local_path)
        file_names.append(safe_name)

    output_path = _OUTPUTS_DIR / f"{job_id}.mp4"

    initial_steps = _store_fns["initial_steps"]()
    job: dict = {
        "id": job_id,
        "sourceFileNames": ",".join(file_names),
        "notebookTitle": request.notebook_title,
        "instructions": request.instructions,
        "style": request.style,
        "format": request.format,
        "language": request.language,
        "timeout": request.timeout,
        "status": "pending",
        "steps": initial_steps,
        "currentStep": None,
        "errorMessage": None,
        "createdAt": now,
        "updatedAt": now,
        "completedAt": None,
        "callbackUrl": request.callback_url,
    }

    await _store_fns["create"](job)

    background_tasks.add_task(
        _store_fns["run_job"],
        job_id=job_id,
        source_paths=source_paths,
        output_path=output_path,
        notebook_title=request.notebook_title,
        instructions=request.instructions,
        style=request.style,
        video_format=request.format,
        language=request.language,
        timeout=request.timeout,
        store_update=_store_fns["update"],
        callback_url=request.callback_url,
        semaphore=_store_fns["semaphore"],
    )

    return JobResponse(**job)


@router.get(
    "/jobs",
    response_model=list[JobResponse],
    summary="ジョブ一覧取得",
)
async def get_jobs_v1(
    status: Optional[str] = None,
    _api_key: str = Depends(verify_api_key),
) -> list[JobResponse]:
    jobs = await _store_fns["list"](status)
    result = []
    for j in jobs:
        j_copy = dict(j)
        if "csvFileNames" in j_copy:
            j_copy["sourceFileNames"] = j_copy.pop("csvFileNames")
        result.append(JobResponse(**j_copy))
    return result


@router.get(
    "/jobs/{job_id}",
    response_model=JobResponse,
    summary="ジョブ状態取得",
)
async def get_job_v1(
    job_id: str,
    _api_key: str = Depends(verify_api_key),
) -> JobResponse:
    job = await _store_fns["get"](job_id)
    j_copy = dict(job)
    if "csvFileNames" in j_copy:
        j_copy["sourceFileNames"] = j_copy.pop("csvFileNames")
    return JobResponse(**j_copy)


@router.get(
    "/jobs/{job_id}/download",
    summary="動画ダウンロード",
    responses={
        200: {"content": {"video/mp4": {}}, "description": "MP4動画ファイル（ローカルモード）"},
        302: {"description": "S3 署名付き URL へリダイレクト"},
        400: {"description": "動画がまだ準備できていない"},
        404: {"description": "ジョブまたは動画ファイルが見つからない"},
    },
)
async def download_job_v1(
    job_id: str,
    _api_key: str = Depends(verify_api_key),
):
    job = await _store_fns["get"](job_id)
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="動画はまだ準備ができていません")

    if storage_mod.is_s3_enabled():
        url = storage_mod.generate_mp4_download_url(job_id)
        if url is None:
            raise HTTPException(status_code=500, detail="ダウンロード URL の生成に失敗しました")
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url=url, status_code=302)

    output_path = _OUTPUTS_DIR / f"{job_id}.mp4"
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="動画ファイルが見つかりません")

    title = job.get("notebookTitle", job_id)
    safe_title = title.replace("/", "_").replace("\\", "_")
    return FileResponse(
        path=str(output_path),
        media_type="video/mp4",
        filename=f"{safe_title}.mp4",
    )
