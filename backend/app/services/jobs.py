"""Job pipeline step definitions."""

from datetime import datetime, timezone


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def initial_steps() -> list[dict]:
    return [
        {"id": "create_notebook", "label": "ノートブック作成", "status": "pending"},
        {"id": "add_source", "label": "ドキュメント追加", "status": "pending"},
        {"id": "generate_video", "label": "動画生成開始", "status": "pending"},
        {"id": "wait_completion", "label": "生成完了待機", "status": "pending"},
        {"id": "download_ready", "label": "ダウンロード準備完了", "status": "pending"},
    ]
