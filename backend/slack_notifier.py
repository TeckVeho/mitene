"""
Slack通知モジュール

動画生成完了時にSlackへ通知する。
SLACK_MOCK=true の場合はログ出力のみ（モック動作）。

環境変数:
  SLACK_WEBHOOK_URL - Slack Incoming Webhook URL
  SLACK_MOCK        - "true" の場合はモック動作（デフォルト: true）
  APP_BASE_URL      - アプリのベースURL（通知リンクに使用）
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

SLACK_WEBHOOK_URL: Optional[str] = os.environ.get("SLACK_WEBHOOK_URL")
SLACK_MOCK: bool = os.environ.get("SLACK_MOCK", "true").lower() != "false"
APP_BASE_URL: str = os.environ.get("APP_BASE_URL", "http://localhost:3000")


async def notify_video_ready(
    video_id: str,
    title: str,
    category_name: Optional[str] = None,
    article_git_path: Optional[str] = None,
) -> None:
    """
    動画生成完了をSlackに通知する。

    Args:
        video_id: 動画ID
        title: 動画タイトル
        category_name: カテゴリ名
        article_git_path: 元の記事のGitパス
    """
    video_url = f"{APP_BASE_URL}/videos/{video_id}"
    category_text = f"カテゴリ: {category_name}" if category_name else ""
    source_text = f"ソース: `{article_git_path}`" if article_git_path else ""

    message = (
        f"📚 新しいE-learning動画が公開されました！\n"
        f"*{title}*\n"
        f"{category_text}\n"
        f"{source_text}\n"
        f"👉 視聴はこちら: {video_url}"
    ).strip()

    if SLACK_MOCK:
        logger.info("[Slack通知モック] %s", message)
        return

    if not SLACK_WEBHOOK_URL:
        logger.warning("SLACK_WEBHOOK_URL が設定されていないため Slack 通知をスキップします")
        return

    try:
        import httpx
        payload = {
            "text": message,
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"📚 *新しいE-learning動画が公開されました！*",
                    },
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*タイトル*\n{title}"},
                        {"type": "mrkdwn", "text": f"*カテゴリ*\n{category_name or '—'}"},
                    ],
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "動画を視聴する"},
                            "url": video_url,
                            "style": "primary",
                        }
                    ],
                },
            ],
        }

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(SLACK_WEBHOOK_URL, json=payload)
            if resp.status_code < 400:
                logger.info("Slack通知送信成功: %s", title)
            else:
                logger.warning("Slack通知送信失敗 (status=%d): %s", resp.status_code, title)

    except ImportError:
        logger.error("httpx がインストールされていません。pip install httpx を実行してください。")
    except Exception as exc:
        logger.error("Slack通知エラー: %s", exc)
