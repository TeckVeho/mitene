"""
音声生成バックグラウンドジョブランナー

処理ステップ:
  1. read_csv        - CSV 読み込み
  2. generate_script - Gemini LLM で解説原稿を生成
  3. generate_audio  - Gemini TTS で音声ファイルを生成
  4. download_ready  - ダウンロード準備完了

環境変数:
  GEMINI_API_KEY - Google AI Gemini API キー（必須）
"""

import asyncio
import logging
import os
import traceback
import wave
from pathlib import Path
from typing import Callable, Awaitable, Optional

import storage as storage_mod
from webhook import send_webhook

logger = logging.getLogger(__name__)

AUDIO_STEP_IDS = [
    "read_csv",
    "generate_script",
    "generate_audio",
    "download_ready",
]

GEMINI_API_KEY: Optional[str] = os.environ.get("GEMINI_API_KEY")

StoreUpdateFn = Callable[..., Awaitable[dict]]


def _write_wav(path: Path, pcm_data: bytes, channels: int = 1, rate: int = 24000, sample_width: int = 2) -> None:
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        wf.writeframes(pcm_data)


async def _set_step_status(
    store_update: StoreUpdateFn,
    job_id: str,
    current_steps: list[dict],
    step_id: str,
    step_status: str,
    message: str | None = None,
) -> list[dict]:
    updated = []
    for s in current_steps:
        if s["id"] == step_id:
            s = {**s, "status": step_status}
            if message is not None:
                s["message"] = message
        updated.append(s)
    await store_update(job_id, steps=updated, currentStep=step_id)
    return updated


async def _fail_job(
    store_update: StoreUpdateFn,
    job_id: str,
    steps: list[dict],
    failed_step: str,
    error_message: str,
) -> None:
    steps = await _set_step_status(store_update, job_id, steps, failed_step, "error", error_message)
    await store_update(
        job_id,
        status="error",
        steps=steps,
        errorMessage=error_message,
    )


async def run_audio_job(
    *,
    job_id: str,
    csv_paths: list[Path],
    output_path: Path,
    title: str,
    instructions: str,
    voice_name: str,
    language: str,
    timeout: int,
    store_update: StoreUpdateFn,
    style_prompt: str = "",
    callback_url: Optional[str] = None,
    semaphore: asyncio.Semaphore | None = None,
) -> None:
    """
    音声生成ジョブを非同期バックグラウンドで実行する。

    ステップ:
      1. CSV 読み込み
      2. Gemini LLM で解説原稿を生成
      3. Gemini TTS で音声ファイルを生成（WAV → S3 or ローカル保存）
      4. ダウンロード準備完了
    """
    if semaphore is not None:
        await semaphore.acquire()

    if not GEMINI_API_KEY:
        await store_update(
            job_id,
            status="error",
            errorMessage=(
                "GEMINI_API_KEY が設定されていません。"
                "環境変数 GEMINI_API_KEY に Google AI API キーを設定してください。"
            ),
        )
        if semaphore is not None:
            semaphore.release()
        return

    try:
        from google import genai
        from google.genai import types as genai_types
    except ImportError:
        await store_update(
            job_id,
            status="error",
            errorMessage=(
                "google-genai がインストールされていません。"
                "pip install google-genai を実行してください。"
            ),
        )
        if semaphore is not None:
            semaphore.release()
        return

    job = await store_update(job_id, status="processing")
    steps: list[dict] = job["steps"]

    try:
        # ── Step 1: CSV 読み込み ──────────────────────────────────────
        steps = await _set_step_status(
            store_update, job_id, steps, "read_csv", "in_progress",
            message="CSVファイルを読み込み中..."
        )

        csv_content_parts: list[str] = []
        for csv_path in csv_paths:
            try:
                text = csv_path.read_text(encoding="utf-8-sig")
            except UnicodeDecodeError:
                text = csv_path.read_text(encoding="shift-jis", errors="replace")
            csv_content_parts.append(f"=== {csv_path.name} ===\n{text}")

        csv_content = "\n\n".join(csv_content_parts)

        steps = await _set_step_status(
            store_update, job_id, steps, "read_csv", "completed"
        )

        # ── Step 2: Gemini LLM で解説原稿を生成 ─────────────────────
        steps = await _set_step_status(
            store_update, job_id, steps, "generate_script", "in_progress",
            message="Gemini AIで解説原稿を生成中..."
        )

        client = genai.Client(api_key=GEMINI_API_KEY)

        lang_hint = "日本語" if language == "ja" else language
        prompt = (
            f"あなたはデータアナリストのナレーターです。\n"
            f"以下のCSVデータを分析し、音声読み上げ用の解説原稿を{lang_hint}で作成してください。\n\n"
            f"## ユーザーからの指示\n"
            f"{instructions}\n\n"
            f"## 原稿作成のルール\n"
            f"- 原稿は自然な話し言葉で書いてください\n"
            f"- 見出しや箇条書き記号（#、*、- など）は一切使わないでください\n"
            f"- 読み上げやすい連続した文章にしてください\n"
            f"- データから読み取れる具体的な数値や傾向を必ず含めてください\n"
            f"- 冒頭で「本日は〜についてご説明します」のように話題を導入し、"
            f"末尾は「以上です」などで自然に締めくくってください\n"
            f"- 数字は聞いて分かるよう「パーセント」「回」「件」など単位を言葉で読み上げられるように表現してください\n"
            f"- 原稿全体の文字数は300文字以上350文字以内にしてください（音声で約1分になる分量です）\n\n"
            f"## CSVデータ\n"
            f"{csv_content}"
        )

        script_response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    top_p=1.0,
                ),
            ),
        )
        script = script_response.text

        await store_update(job_id, generatedScript=script)
        steps = await _set_step_status(
            store_update, job_id, steps, "generate_script", "completed"
        )

        # ── Step 3: Gemini TTS で音声生成 ────────────────────────────
        steps = await _set_step_status(
            store_update, job_id, steps, "generate_audio", "in_progress",
            message=f"Gemini TTS で音声を生成中... (ボイス: {voice_name})"
        )

        tts_input = f"{style_prompt} {script}".strip() if style_prompt else script

        def _build_tts_config() -> genai_types.GenerateContentConfig:
            return genai_types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=genai_types.SpeechConfig(
                    voice_config=genai_types.VoiceConfig(
                        prebuilt_voice_config=genai_types.PrebuiltVoiceConfig(
                            voice_name=voice_name,
                        )
                    )
                ),
            )

        tts_response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: client.models.generate_content(
                model="gemini-2.5-flash-preview-tts",
                contents=tts_input,
                config=_build_tts_config(),
            ),
        )

        audio_data: bytes = tts_response.candidates[0].content.parts[0].inline_data.data

        # WAV ファイルとして保存（PCM 24kHz mono 16bit）
        _write_wav(output_path, audio_data)

        # S3 が有効な場合: ローカルに保存後 S3 にアップロードし一時ファイル削除
        if storage_mod.is_s3_enabled():
            steps = await _set_step_status(
                store_update, job_id, steps, "generate_audio", "in_progress",
                message="音声ファイルを S3 にアップロード中..."
            )
            await asyncio.get_event_loop().run_in_executor(
                None, storage_mod.upload_audio_to_s3, job_id, output_path
            )

        steps = await _set_step_status(
            store_update, job_id, steps, "generate_audio", "completed"
        )

        # ── Step 4: ダウンロード準備完了 ────────────────────────────
        steps = await _set_step_status(
            store_update, job_id, steps, "download_ready", "completed"
        )

        # ローカル CSV 一時ファイルを削除
        storage_mod.cleanup_local_csv(csv_paths)

        from datetime import datetime, timezone
        completed_at = datetime.now(timezone.utc).isoformat()
        await store_update(
            job_id,
            status="completed",
            steps=steps,
            completedAt=completed_at,
        )

        if callback_url:
            await send_webhook(
                callback_url,
                {
                    "event": "job.completed",
                    "job_id": job_id,
                    "status": "completed",
                    "completed_at": completed_at,
                },
            )

    except Exception as exc:
        current_step = "read_csv"
        for s in steps:
            if s["status"] == "in_progress":
                current_step = s["id"]
                break

        exc_type = type(exc).__name__
        exc_msg = str(exc).split("\n")[0]
        error_detail = f"[{exc_type}] {exc_msg}"
        tb = traceback.format_exc()

        print(f"\n[AUDIO RUNNER ERROR] Job {job_id} failed at step '{current_step}'")
        print(f"[AUDIO RUNNER ERROR] {error_detail}")
        print(f"[AUDIO RUNNER ERROR] Traceback:\n{tb}", flush=True)

        logger.error("Audio job %s failed at step '%s': %s", job_id, current_step, error_detail)

        error_message = f"予期しないエラーが発生しました: {error_detail}"
        await _fail_job(store_update, job_id, steps, current_step, error_message)

        if callback_url:
            await send_webhook(
                callback_url,
                {
                    "event": "job.error",
                    "job_id": job_id,
                    "status": "error",
                    "error_message": error_message,
                },
            )
    finally:
        if semaphore is not None:
            semaphore.release()
