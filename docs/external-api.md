# 外部API 実装手順書

本ドキュメントは、NoteVideo バックエンドを外部システムから利用するための外部API（`/api/v1/`）の仕様・実装内容・利用方法をまとめたものです。

---

## 目次

1. [概要・アーキテクチャ](#概要アーキテクチャ)
2. [実装済みファイル一覧](#実装済みファイル一覧)
3. [セットアップ](#セットアップ)
4. [認証](#認証)
5. [エンドポイント仕様](#エンドポイント仕様)
6. [Webhook通知](#webhook通知)
7. [利用例（cURL）](#利用例curl)
8. [既存フロントエンドAPIとの共存](#既存フロントエンドapiとの共存)

---

## 概要・アーキテクチャ

外部システムからCSVファイルを送信すると、Google NotebookLM を使って AI 解説動画（MP4）を自動生成し、ダウンロード可能にする API です。

```
外部システム
  │
  │  POST /api/v1/jobs  (X-API-Key + JSON)
  ▼
FastAPI Backend  ─── バックグラウンド処理 ───►  NotebookLM
  │                                               │
  │  GET /api/v1/jobs/{id}  (ポーリング)          │ 動画生成完了
  ◄──────────────────────────────────────         │
  │                                               │
  │◄──── POST callback_url (Webhook通知) ─────────┘
  │
  │  GET /api/v1/jobs/{id}/download
  ▼
MP4ダウンロード
```

**処理の流れ**

1. 外部システムが `POST /api/v1/jobs` でCSVと設定を送信
2. API がジョブを作成し `job_id` を即時返却（非同期処理開始）
3. バックグラウンドで NotebookLM へCSVをアップロード → 動画生成 → MP4保存
4. 完了/エラー時に `callback_url` へ Webhook 通知（指定した場合）
5. 外部システムが `GET /api/v1/jobs/{id}/download` でMP4を取得

---

## 実装済みファイル一覧

| ファイル | 種別 | 概要 |
|---------|------|------|
| `backend/auth.py` | 新規 | APIキー認証（`X-API-Key` ヘッダー検証） |
| `backend/webhook.py` | 新規 | Webhook通知（httpx、リトライ付き） |
| `backend/api_v1.py` | 新規 | 外部API v1 ルーター（全エンドポイント定義） |
| `backend/main.py` | 修正 | v1ルーター登録、CORS環境変数化、OpenAPI説明追加 |
| `backend/runner.py` | 修正 | `callback_url` 引数追加、Webhook呼び出し統合 |
| `backend/requirements.txt` | 修正 | `httpx` 追加 |

---

## セットアップ

### 1. 依存パッケージのインストール

```bash
cd backend
pip install -r requirements.txt
```

### 2. 環境変数の設定

```bash
# APIキーを設定（カンマ区切りで複数指定可）
export NOTEVIDEO_API_KEYS=your_secret_key_here,another_key

# CORS許可オリジンを追加する場合（デフォルト: localhost:3000）
export CORS_ALLOWED_ORIGINS=http://localhost:3000,https://your-external-system.example.com
```

> **注意**: `NOTEVIDEO_API_KEYS` が未設定の場合、認証なしでアクセス可能になります（開発環境用）。本番環境では必ず設定してください。

### 3. サーバー起動

```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. APIドキュメント確認

サーバー起動後、以下のURLでインタラクティブなAPIドキュメントを確認できます。

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 認証

外部API（`/api/v1/`）はすべてのリクエストに `X-API-Key` ヘッダーが必要です。

```
X-API-Key: your_secret_key_here
```

| 状況 | レスポンス |
|------|-----------|
| `NOTEVIDEO_API_KEYS` 未設定 | 認証スキップ（開発用フリーアクセス） |
| キーが一致する | 正常処理 |
| キーが一致しない / ヘッダーなし | `401 Unauthorized` |

---

## エンドポイント仕様

### POST `/api/v1/jobs` — ジョブ作成

CSVファイルを送信して動画生成ジョブを作成します。

**リクエストヘッダー**

```
Content-Type: application/json
X-API-Key: <your-api-key>
```

**リクエストボディ**

```json
{
  "notebook_title": "CSV分析レポート",
  "instructions": "CSVデータの主要な傾向と示唆を分かりやすく解説してください",
  "style": "whiteboard",
  "format": "explainer",
  "language": "ja",
  "timeout": 1800,
  "callback_url": "https://your-system/webhooks/notevideo",
  "csv_files": [
    {
      "filename": "data.csv",
      "content_base64": "<Base64エンコードされたCSVの内容>"
    }
  ]
}
```

**パラメータ詳細**

| フィールド | 型 | デフォルト | 説明 |
|-----------|-----|-----------|------|
| `notebook_title` | string | `"CSV分析レポート"` | 生成するNotebookのタイトル |
| `instructions` | string | `"CSVデータの...解説..."` | 動画の内容に関する指示 |
| `style` | string | `"whiteboard"` | 動画スタイル（下表参照） |
| `format` | string | `"explainer"` | 動画フォーマット（`explainer` / `brief`） |
| `language` | string | `"ja"` | 生成言語（`ja` / `en` 等） |
| `timeout` | integer | `1800` | タイムアウト秒数（最大待機時間） |
| `callback_url` | string | `null` | 完了・エラー時のWebhook通知先URL（任意） |
| `csv_files` | array | 必須 | CSVファイルの配列（1つ以上） |

**`csv_files` の各要素**

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `filename` | string | ファイル名（`.csv` 拡張子必須） |
| `content_base64` | string | CSVファイルをBase64エンコードした文字列 |
| `file_path` | string | サーバー上の絶対パス（サーバーにファイルがある場合） |

> `content_base64` または `file_path` のいずれか一方を必ず指定してください。

**動画スタイル一覧**

| 値 | 説明 |
|----|------|
| `auto` | AIが最適なスタイルを自動選択 |
| `classic` | シンプルで落ち着いたスタイル |
| `whiteboard` | ホワイトボード風の手書き表現 |
| `kawaii` | かわいらしいイラストスタイル |
| `anime` | 日本のアニメ風スタイル |
| `watercolor` | 柔らかい水彩画風表現 |
| `retro-print` | レトロな印刷物風スタイル |
| `heritage` | クラシックな伝統的スタイル |
| `paper-craft` | 紙工作風の温かみのある表現 |

**レスポンス（201 Created）**

```json
{
  "id": "job_a1b2c3d4e5f6",
  "csvFileNames": "data.csv",
  "notebookTitle": "CSV分析レポート",
  "instructions": "CSVデータの主要な傾向と示唆を分かりやすく解説してください",
  "style": "whiteboard",
  "format": "explainer",
  "language": "ja",
  "timeout": 1800,
  "status": "pending",
  "steps": [
    {"id": "create_notebook", "label": "ノートブック作成", "status": "pending"},
    {"id": "add_source",      "label": "CSVソース追加",    "status": "pending"},
    {"id": "generate_video",  "label": "動画生成開始",     "status": "pending"},
    {"id": "wait_completion", "label": "生成完了待機",     "status": "pending"},
    {"id": "download_ready",  "label": "ダウンロード準備完了", "status": "pending"}
  ],
  "currentStep": null,
  "errorMessage": null,
  "createdAt": "2026-03-04T10:00:00.000000+00:00",
  "updatedAt": "2026-03-04T10:00:00.000000+00:00",
  "completedAt": null,
  "callbackUrl": "https://your-system/webhooks/notevideo"
}
```

---

### GET `/api/v1/jobs` — ジョブ一覧取得

**クエリパラメータ**

| パラメータ | 説明 |
|-----------|------|
| `status` | フィルタ（`pending` / `processing` / `completed` / `error` / `all`） |

```
GET /api/v1/jobs?status=processing
```

---

### GET `/api/v1/jobs/{job_id}` — ジョブ状態取得

ポーリングで進捗を確認する際に使用します。

**`status` フィールドの値**

| 値 | 説明 |
|----|------|
| `pending` | 処理待ち |
| `processing` | 処理中 |
| `completed` | 完了（動画ダウンロード可能） |
| `error` | エラー発生 |

**`steps[].status` の値**

| 値 | 説明 |
|----|------|
| `pending` | 未着手 |
| `in_progress` | 実行中 |
| `completed` | 完了 |
| `error` | エラー |

---

### GET `/api/v1/jobs/{job_id}/download` — 動画ダウンロード

ジョブが `completed` 状態のときのみダウンロード可能です。

**レスポンス**

- `200 OK` — `Content-Type: video/mp4` でMP4ファイルを返す
- `400 Bad Request` — ジョブがまだ完了していない
- `404 Not Found` — ジョブIDが存在しない、またはファイルが見つからない

---

## Webhook通知

`callback_url` を指定した場合、ジョブが完了またはエラーになった時点で指定URLにPOSTリクエストを送信します。

**仕様**

| 項目 | 内容 |
|------|------|
| メソッド | `POST` |
| Content-Type | `application/json` |
| タイムアウト | 10秒 |
| リトライ回数 | 最大3回 |
| リトライ間隔 | 5秒 → 15秒 → 45秒（指数バックオフ） |

**完了時のペイロード**

```json
{
  "event": "job.completed",
  "job_id": "job_a1b2c3d4e5f6",
  "status": "completed",
  "completed_at": "2026-03-04T10:30:00.000000+00:00"
}
```

**エラー時のペイロード**

```json
{
  "event": "job.error",
  "job_id": "job_a1b2c3d4e5f6",
  "status": "error",
  "error_message": "予期しないエラーが発生しました: [ExceptionType] ..."
}
```

---

## 利用例（cURL）

### ステップ1: CSVをBase64エンコード

```bash
CSV_BASE64=$(base64 -i ./your_data.csv)
```

### ステップ2: ジョブ作成

```bash
RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/jobs \
  -H "X-API-Key: your_secret_key_here" \
  -H "Content-Type: application/json" \
  -d "{
    \"notebook_title\": \"売上分析レポート 2026年3月\",
    \"instructions\": \"月次売上の傾向と前月比較を解説してください\",
    \"style\": \"whiteboard\",
    \"format\": \"explainer\",
    \"language\": \"ja\",
    \"callback_url\": \"https://your-system/webhooks/notevideo\",
    \"csv_files\": [{
      \"filename\": \"sales_202603.csv\",
      \"content_base64\": \"${CSV_BASE64}\"
    }]
  }")

JOB_ID=$(echo $RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
echo "ジョブID: $JOB_ID"
```

### ステップ3: ステータスをポーリング

```bash
while true; do
  STATUS=$(curl -s http://localhost:8000/api/v1/jobs/$JOB_ID \
    -H "X-API-Key: your_secret_key_here" \
    | python3 -c "import sys, json; print(json.load(sys.stdin)['status'])")
  echo "ステータス: $STATUS"
  if [ "$STATUS" = "completed" ] || [ "$STATUS" = "error" ]; then
    break
  fi
  sleep 30
done
```

### ステップ4: MP4をダウンロード

```bash
curl -o output.mp4 http://localhost:8000/api/v1/jobs/$JOB_ID/download \
  -H "X-API-Key: your_secret_key_here"
echo "ダウンロード完了: output.mp4"
```

### Python利用例

```python
import base64
import time
import httpx

BASE_URL = "http://localhost:8000/api/v1"
HEADERS = {"X-API-Key": "your_secret_key_here"}

# CSVをBase64エンコード
with open("data.csv", "rb") as f:
    csv_b64 = base64.b64encode(f.read()).decode()

# ジョブ作成
resp = httpx.post(f"{BASE_URL}/jobs", headers=HEADERS, json={
    "notebook_title": "分析レポート",
    "csv_files": [{"filename": "data.csv", "content_base64": csv_b64}],
    "callback_url": "https://your-system/webhook",
})
resp.raise_for_status()
job_id = resp.json()["id"]
print(f"ジョブ作成: {job_id}")

# ポーリングで完了を待つ
while True:
    job = httpx.get(f"{BASE_URL}/jobs/{job_id}", headers=HEADERS).json()
    print(f"ステータス: {job['status']} / ステップ: {job['currentStep']}")
    if job["status"] in ("completed", "error"):
        break
    time.sleep(30)

# MP4ダウンロード
if job["status"] == "completed":
    video = httpx.get(f"{BASE_URL}/jobs/{job_id}/download", headers=HEADERS)
    with open("output.mp4", "wb") as f:
        f.write(video.content)
    print("動画保存完了: output.mp4")
else:
    print(f"エラー: {job['errorMessage']}")
```

---

## 既存フロントエンドAPIとの共存

外部API（`/api/v1/`）は既存のフロントエンド用API（`/api/`）と**完全に独立**しています。

| | フロントエンド用 `/api/` | 外部API `/api/v1/` |
|---|---|---|
| 認証 | なし | `X-API-Key` ヘッダー必須 |
| CSVの渡し方 | `multipart/form-data` | JSON（Base64 or サーバーパス） |
| Webhook | なし | `callback_url` で指定可 |
| 対象 | ブラウザUI | 外部システム・スクリプト |

既存のフロントエンド動作に影響はありません。ジョブストアは共通のため、フロントエンドUI上でも外部APIから作成したジョブを確認できます。
