"""
Webhook通知モジュール
ジョブ完了・エラー時に外部システムへPOSTリクエストで通知する。
リトライ付き（指数バックオフ: 5秒, 15秒, 45秒）。
"""

import asyncio
import logging

logger = logging.getLogger(__name__)


async def send_webhook(
    callback_url: str,
    payload: dict,
    max_retries: int = 3,
) -> None:
    """
    指定URLにWebhookペイロードをPOSTする。

    Args:
        callback_url: 送信先URL
        payload: JSON送信するdict
        max_retries: 最大リトライ回数（デフォルト3回）

    リトライ間隔: 5秒 → 15秒 → 45秒（指数バックオフ）
    レスポンスが4xx/5xxの場合もリトライする。
    """
    try:
        import httpx
    except ImportError:
        logger.error("httpx がインストールされていません。pip install httpx を実行してください。")
        return

    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(callback_url, json=payload)
                if resp.status_code < 400:
                    logger.info(
                        "Webhook送信成功: %s (status=%d, attempt=%d)",
                        callback_url,
                        resp.status_code,
                        attempt + 1,
                    )
                    return
                logger.warning(
                    "Webhook送信失敗 (status=%d, attempt=%d/%d): %s",
                    resp.status_code,
                    attempt + 1,
                    max_retries,
                    callback_url,
                )
        except Exception as exc:
            logger.warning(
                "Webhook送信エラー (attempt=%d/%d): %s - %s",
                attempt + 1,
                max_retries,
                callback_url,
                exc,
            )

        if attempt < max_retries - 1:
            wait_sec = 5 * (3 ** attempt)  # 5, 15, 45秒
            logger.info("Webhookリトライまで %d 秒待機...", wait_sec)
            await asyncio.sleep(wait_sec)

    logger.error(
        "Webhook送信を %d 回試みましたが失敗しました: %s",
        max_retries,
        callback_url,
    )
