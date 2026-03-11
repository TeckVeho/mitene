"""
外部API v1 ルーター
他システムから本システムのCSV→動画生成・音声生成処理を実行するためのエンドポイント群。

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
from fastapi.responses import RedirectResponse, FileResponse, Response
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


class CsvFileInput(BaseModel):
    """CSVファイルの指定方法（Base64またはサーバーパス）"""

    filename: str
    content_base64: Optional[str] = None
    """Base64エンコードされたCSVファイルの内容"""
    file_path: Optional[str] = None
    """サーバー上の絶対パス（サーバー側にファイルが存在する場合）"""

    @field_validator("filename")
    @classmethod
    def validate_filename(cls, v: str) -> str:
        if not v.endswith(".csv"):
            raise ValueError("ファイル名は .csv で終わる必要があります")
        return v

    def model_post_init(self, __context) -> None:
        if not self.content_base64 and not self.file_path:
            raise ValueError("content_base64 または file_path のいずれかを指定してください")


class ExternalJobRequest(BaseModel):
    """外部APIからのジョブ作成リクエスト（JSON形式）"""

    notebook_title: str = "CSV分析レポート"
    instructions: str = "CSVデータの主要な傾向と示唆を分かりやすく解説してください"
    style: str = "whiteboard"
    format: str = "explainer"
    language: str = "ja"
    timeout: int = 1800
    callback_url: Optional[str] = None
    """完了・エラー時にWebhookで通知するURL（任意）"""
    csv_files: list[CsvFileInput]


class ExternalAudioJobRequest(BaseModel):
    """外部APIからの音声ジョブ作成リクエスト（JSON形式）"""

    title: str = "CSV音声解説"
    instructions: str = "CSVデータの主要な傾向と示唆を分かりやすく解説してください"
    voice_name: str = "Kore"
    """Gemini TTS ボイス名（例: Kore / Charon / Fenrir / Aoede / Puck）"""
    language: str = "ja"
    timeout: int = 600
    callback_url: Optional[str] = None
    """完了・エラー時にWebhookで通知するURL（任意）"""
    csv_files: list[CsvFileInput]


class JobResponse(BaseModel):
    """動画ジョブレスポンス"""

    id: str
    csvFileNames: str
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


class AudioJobResponse(BaseModel):
    """音声ジョブレスポンス"""

    id: str
    jobType: str
    csvFileNames: str
    notebookTitle: str
    instructions: str
    language: str
    timeout: int
    voiceName: Optional[str] = None
    generatedScript: Optional[str] = None
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

# store 関数は main.py の起動時に register_store_functions() でインジェクトされる
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
    if audio_initial_steps_fn is not None:
        _store_fns["audio_initial_steps"] = audio_initial_steps_fn
    if run_audio_job_fn is not None:
        _store_fns["run_audio_job"] = run_audio_job_fn


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
        "CSVファイルをBase64エンコードまたはサーバーパスで指定し、動画生成ジョブを作成します。\n\n"
        "- `content_base64`: CSVファイルの内容をBase64エンコードした文字列\n"
        "- `file_path`: サーバー上の絶対パス（同一サーバーにファイルがある場合）\n\n"
        "ジョブIDを返します。完了通知が必要な場合は `callback_url` を指定してください。"
    ),
)
async def create_job_v1(
    request: ExternalJobRequest,
    background_tasks: BackgroundTasks,
    _api_key: str = Depends(verify_api_key),
) -> JobResponse:
    if not request.csv_files:
        raise HTTPException(status_code=400, detail="csv_files を1つ以上指定してください")

    job_id = f"job_{uuid.uuid4().hex[:12]}"
    now = _now()

    csv_paths: list[Path] = []
    file_names: list[str] = []

    for csv_input in request.csv_files:
        safe_name = csv_input.filename.replace("/", "_").replace("\\", "_")

        if csv_input.content_base64:
            try:
                content = base64.b64decode(csv_input.content_base64)
            except Exception:
                raise HTTPException(
                    status_code=400,
                    detail=f"{safe_name}: content_base64 のデコードに失敗しました。正しいBase64文字列を指定してください。",
                )
            local_path = storage_mod.save_csv_locally(_UPLOADS_DIR, job_id, safe_name, content)
            storage_mod.upload_csv_to_s3(job_id, safe_name, content)

        elif csv_input.file_path:
            src = Path(csv_input.file_path)
            if not src.exists():
                raise HTTPException(
                    status_code=400,
                    detail=f"指定されたファイルが見つかりません: {csv_input.file_path}",
                )
            import shutil
            local_path = _UPLOADS_DIR / f"{job_id}_{safe_name}"
            shutil.copy2(src, local_path)
            content = local_path.read_bytes()
            storage_mod.upload_csv_to_s3(job_id, safe_name, content)
        else:
            raise HTTPException(status_code=400, detail=f"{safe_name}: ファイル内容が指定されていません")

        csv_paths.append(local_path)
        file_names.append(safe_name)

    output_path = _OUTPUTS_DIR / f"{job_id}.mp4"

    initial_steps = _store_fns["initial_steps"]()
    job: dict = {
        "id": job_id,
        "csvFileNames": ",".join(file_names),
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
        csv_paths=csv_paths,
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
    description="ジョブの一覧を返します。`?status=processing` でフィルタ可能です。",
)
async def get_jobs_v1(
    status: Optional[str] = None,
    _api_key: str = Depends(verify_api_key),
) -> list[JobResponse]:
    jobs = await _store_fns["list"](status)
    return [JobResponse(**j) for j in jobs]


@router.get(
    "/jobs/{job_id}",
    response_model=JobResponse,
    summary="ジョブ状態取得",
    description=(
        "指定ジョブの現在の状態を返します。\n\n"
        "`status` フィールドは `pending` / `processing` / `completed` / `error` のいずれか。\n"
        "`steps` フィールドで各処理ステップの進捗を確認できます。"
    ),
)
async def get_job_v1(
    job_id: str,
    _api_key: str = Depends(verify_api_key),
) -> JobResponse:
    job = await _store_fns["get"](job_id)
    return JobResponse(**job)


@router.get(
    "/jobs/{job_id}/download",
    summary="動画ダウンロード",
    description=(
        "完了したジョブの動画（MP4）をダウンロードします。\n\n"
        "S3 が有効な場合は署名付き URL（有効期限1時間）へリダイレクトします。\n"
        "ジョブが `completed` 状態でない場合は 400 エラーを返します。"
    ),
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

    # S3 モード: 署名付き URL にリダイレクト
    if storage_mod.is_s3_enabled():
        url = storage_mod.generate_mp4_download_url(job_id)
        if url is None:
            raise HTTPException(status_code=500, detail="ダウンロード URL の生成に失敗しました")
        return RedirectResponse(url=url, status_code=302)

    # ローカルモード: ファイルを直接返す
    output_path = _OUTPUTS_DIR / f"{job_id}.mp4"
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="動画ファイルが見つかりません")

    safe_title = job["notebookTitle"].replace("/", "_").replace("\\", "_")
    return FileResponse(
        path=str(output_path),
        media_type="video/mp4",
        filename=f"{safe_title}.mp4",
    )


# ---------------------------------------------------------------------------
# Audio job endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/audio-jobs",
    response_model=AudioJobResponse,
    status_code=201,
    summary="音声ジョブ作成（JSON形式）",
    description=(
        "CSVファイルをBase64エンコードまたはサーバーパスで指定し、音声解説生成ジョブを作成します。\n\n"
        "処理ステップ:\n"
        "1. CSV読み込み\n"
        "2. Gemini LLMで解説原稿を生成\n"
        "3. Gemini TTSでWAV音声を生成\n"
        "4. ダウンロード準備完了\n\n"
        "必要な環境変数: `GEMINI_API_KEY`\n\n"
        "利用可能なボイス名: `Kore` / `Charon` / `Fenrir` / `Aoede` / `Puck`"
    ),
)
async def create_audio_job_v1(
    request: ExternalAudioJobRequest,
    background_tasks: BackgroundTasks,
    _api_key: str = Depends(verify_api_key),
) -> AudioJobResponse:
    if "run_audio_job" not in _store_fns:
        raise HTTPException(status_code=503, detail="音声ジョブ機能が初期化されていません")
    if not request.csv_files:
        raise HTTPException(status_code=400, detail="csv_files を1つ以上指定してください")

    job_id = f"job_{uuid.uuid4().hex[:12]}"
    now = _now()

    csv_paths: list[Path] = []
    file_names: list[str] = []

    for csv_input in request.csv_files:
        safe_name = csv_input.filename.replace("/", "_").replace("\\", "_")

        if csv_input.content_base64:
            try:
                content = base64.b64decode(csv_input.content_base64)
            except Exception:
                raise HTTPException(
                    status_code=400,
                    detail=f"{safe_name}: content_base64 のデコードに失敗しました。正しいBase64文字列を指定してください。",
                )
            local_path = storage_mod.save_csv_locally(_UPLOADS_DIR, job_id, safe_name, content)
            storage_mod.upload_csv_to_s3(job_id, safe_name, content)

        elif csv_input.file_path:
            src = Path(csv_input.file_path)
            if not src.exists():
                raise HTTPException(
                    status_code=400,
                    detail=f"指定されたファイルが見つかりません: {csv_input.file_path}",
                )
            local_path = _UPLOADS_DIR / f"{job_id}_{safe_name}"
            shutil.copy2(src, local_path)
            content = local_path.read_bytes()
            storage_mod.upload_csv_to_s3(job_id, safe_name, content)
        else:
            raise HTTPException(status_code=400, detail=f"{safe_name}: ファイル内容が指定されていません")

        csv_paths.append(local_path)
        file_names.append(safe_name)

    output_path = _OUTPUTS_DIR / f"{job_id}.wav"

    initial_steps = _store_fns["audio_initial_steps"]()
    job: dict = {
        "id": job_id,
        "jobType": "audio",
        "csvFileNames": ",".join(file_names),
        "notebookTitle": request.title,
        "instructions": request.instructions,
        "style": None,
        "format": None,
        "language": request.language,
        "timeout": request.timeout,
        "voiceName": request.voice_name,
        "generatedScript": None,
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
        _store_fns["run_audio_job"],
        job_id=job_id,
        csv_paths=csv_paths,
        output_path=output_path,
        title=request.title,
        instructions=request.instructions,
        voice_name=request.voice_name,
        language=request.language,
        timeout=request.timeout,
        store_update=_store_fns["update"],
        callback_url=request.callback_url,
        semaphore=_store_fns["semaphore"],
    )

    return AudioJobResponse(**job)


@router.get(
    "/audio-jobs/{job_id}",
    response_model=AudioJobResponse,
    summary="音声ジョブ状態取得",
    description=(
        "指定した音声ジョブの現在の状態を返します。\n\n"
        "`status` が `completed` になると `generatedScript` フィールドに生成された解説原稿テキストが入ります。\n\n"
        "ポーリング推奨間隔: 10〜15秒"
    ),
)
async def get_audio_job_v1(
    job_id: str,
    _api_key: str = Depends(verify_api_key),
) -> AudioJobResponse:
    job = await _store_fns["get"](job_id)
    if job.get("jobType") != "audio":
        raise HTTPException(status_code=404, detail="音声ジョブが見つかりません")
    return AudioJobResponse(**job)


@router.get(
    "/audio-jobs/{job_id}/download",
    summary="音声ダウンロード",
    description=(
        "完了した音声ジョブのWAVファイルをダウンロードします。\n\n"
        "S3 が有効な場合は署名付き URL（有効期限1時間）へリダイレクトします。\n"
        "ジョブが `completed` 状態でない場合は 400 エラーを返します。"
    ),
    responses={
        200: {"content": {"audio/wav": {}}, "description": "WAV音声ファイル（ローカルモード）"},
        302: {"description": "S3 署名付き URL へリダイレクト"},
        400: {"description": "音声がまだ準備できていない"},
        404: {"description": "ジョブまたは音声ファイルが見つからない"},
    },
)
async def download_audio_job_v1(
    job_id: str,
    _api_key: str = Depends(verify_api_key),
):
    job = await _store_fns["get"](job_id)
    if job.get("jobType") != "audio":
        raise HTTPException(status_code=404, detail="音声ジョブが見つかりません")
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="音声はまだ準備ができていません")

    # S3 モード: S3 からバイト列を取得して直接返す
    if storage_mod.is_s3_enabled():
        audio_bytes = storage_mod.download_audio_from_s3(job_id, suffix=".wav")
        if audio_bytes is None:
            raise HTTPException(status_code=500, detail="音声ファイルの取得に失敗しました")

        safe_title = job["notebookTitle"].replace("/", "_").replace("\\", "_")
        return Response(
            content=audio_bytes,
            media_type="audio/wav",
            headers={"Content-Disposition": f'attachment; filename="{safe_title}.wav"'},
        )

    # ローカルモード: ファイルを直接返す
    output_path = _OUTPUTS_DIR / f"{job_id}.wav"
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="音声ファイルが見つかりません")

    safe_title = job["notebookTitle"].replace("/", "_").replace("\\", "_")
    return FileResponse(
        path=str(output_path),
        media_type="audio/wav",
        filename=f"{safe_title}.wav",
    )
