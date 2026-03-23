# mitene（V-learning）

社内 Wiki の Markdown ファイルを Google NotebookLM で AI 解説動画に変換し、エンジニアが視聴できる **E-learning プラットフォーム**です。

## 主な機能

| 機能 | 説明 |
|------|------|
| **動画閲覧** | カテゴリ別・検索で動画を一覧表示し、ストリーミング再生 |
| **視聴履歴** | ログイン済みユーザーの視聴履歴を記録・表示 |
| **あとで見る** | 動画を「あとで見る」リストに追加 |
| **いいね** | お気に入り動画を「いいね」で管理 |
| **多言語対応** | 日本語・ベトナム語の UI 切り替え |
| **ダークモード** | ダーク/ライトテーマ切り替え |
| **Wiki 連携** | Git リポジトリ内の .md を同期し、動画を自動生成 |

---

## システム構成

```
┌─────────────────────────────────────────────────────────────────┐
│  Frontend (Next.js)                                              │
│  / トップ  /videos/[id] 動画再生  /history  /watch-later  /liked  │
│  /jobs ジョブ一覧  /admin 管理  /new 新規作成  /settings          │
└─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│  Backend (FastAPI)                                               │
│  /api  - フロントエンド用（認証: GitHub OAuth / Cookie）            │
│  /api/v1 - 外部 API（認証: X-API-Key）                            │
└─────────────────────────────────────────────────────────────────┘
                                    │
          ┌─────────────────────────┼─────────────────────────┐
          ▼                         ▼                         ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  MySQL (RDS)    │  │  AWS S3         │  │  NotebookLM      │
│  またはインメモリ │  │  またはローカル  │  │  (動画生成)       │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

---

## 前提条件

- **Python 3.10 以上**
- **Node.js 18 以上**（フロントエンド用）
- **ffmpeg / ffprobe**（サムネイル生成用）
- **Google アカウント**（NotebookLM 動画生成用）
- **GitHub アカウント**（OAuth ログイン用）

---

## クイックスタート

### 1. バックエンドのセットアップ

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
brew install ffmpeg  # macOS（ffprobe も含まれる）

# 環境変数（.env.example をコピーして編集）
cp .env.example .env
```

### 2. フロントエンドのセットアップ

```bash
cd frontend
npm install
cp .env.production.example .env.local
# NEXT_PUBLIC_API_URL を http://localhost:8000 に設定
```

### 3. 起動

```bash
# ターミナル1: バックエンド
cd backend && source .venv/bin/activate && uvicorn main:app --reload --port 8000

# ターミナル2: フロントエンド
cd frontend && npm run dev
```

- フロントエンド: http://localhost:3000
- バックエンド API: http://localhost:8000
- API ドキュメント: http://localhost:8000/docs

---

## 認証

### GitHub OAuth（推奨）

1. [GitHub Developer Settings](https://github.com/settings/developers) で OAuth App を作成
2. `backend/.env` に `GITHUB_CLIENT_ID` と `GITHUB_CLIENT_SECRET` を設定
3. `FRONTEND_URL` と `API_BASE_URL` を適切に設定

### NotebookLM 認証（動画生成時）

動画生成には NotebookLM へのログインが必要です。

```bash
cd backend
source .venv/bin/activate
notebooklm login
```

認証情報は `~/.notebooklm/storage_state.json` に保存されます。

---

## 環境変数

### バックエンド (`backend/.env`)

| 変数 | 説明 |
|------|------|
| `DATABASE_URL` | MySQL 接続文字列（未設定時はインメモリ） |
| `S3_BUCKET_NAME` | S3 バケット名（未設定時はローカル保存） |
| `WIKI_GIT_REPO_URL` | Wiki 用 Git リポジトリ URL |
| `WIKI_GIT_LOCAL_PATH` | Wiki クローン先パス |
| `WIKI_BASE_URL` | Wiki サイト URL（動画詳細の元記事リンク用） |
| `GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET` | GitHub OAuth |
| `NOTEVIDEO_API_KEYS` | 外部 API 用キー（カンマ区切り） |
| `SLACK_WEBHOOK_URL` | ジョブ完了時の Slack 通知 |
| `API_BASE_URL` | API ベース URL（`thumbnail_url` の絶対 URL 生成にも使用） |

### フロントエンド (`frontend/.env.local`)

| 変数 | 説明 |
|------|------|
| `NEXT_PUBLIC_API_URL` | バックエンド API のベース URL |

---

## ストレージ

| 種類 | 条件 | 説明 |
|------|------|------|
| **DB** | `DATABASE_URL` 設定 | MySQL（RDS）で永続化 |
| **DB** | 未設定 | インメモリ（開発用、再起動でリセット） |
| **ファイル** | `S3_BUCKET_NAME` 設定 | MP4 を S3 に保存 |
| **ファイル** | 未設定 | `backend/outputs/` にローカル保存 |

---

## 動画生成の流れ

1. **Wiki 同期**: `wiki_sync` が Git リポジトリ内の .md を監視し、変更があった記事を `articles` に登録
2. **ジョブ作成**: 記事ごとに NotebookLM 動画生成ジョブを投入
3. **処理**: ノートブック作成 → ソース追加 → 動画生成 → MP4 保存
4. **配信**: `videos` テーブルに登録され、フロントエンドで閲覧可能に

---

## ディレクトリ構成

```
mitene/
├── backend/           # FastAPI バックエンド
│   ├── main.py        # メインアプリ・ルート定義
│   ├── api_v1.py      # 外部 API v1
│   ├── database.py    # DB 抽象化
│   ├── runner.py      # 動画生成ジョブランナー
│   ├── wiki_sync.py   # Wiki Git 同期
│   └── storage.py     # S3 / ローカルストレージ
├── frontend/          # Next.js フロントエンド
│   ├── app/           # App Router ページ
│   └── components/    # UI コンポーネント
├── deploy/            # デプロイ設定
└── docs/              # ドキュメント
```

---

## 関連ドキュメント

- [デプロイ手順](deploy/DEPLOY.md) - AWS への本番デプロイ
- [外部 API 仕様](docs/external-api.md) - `/api/v1/` の利用方法

---

## 注意事項

- **NotebookLM**: 非公式ライブラリ (notebooklm-py) を使用しています。Google の内部 API 変更により予告なく動作しなくなる可能性があります
- **レート制限**: 短時間の連続リクエストは制限される場合があります
- **認証情報**: `~/.notebooklm/storage_state.json` には Google の認証情報が含まれます。取り扱いに注意してください
