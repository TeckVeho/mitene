# mitene フロントエンド

E-learning プラットフォーム「mitene」の Next.js フロントエンドです。

## 技術スタック

- **Next.js 14** (App Router)
- **React**
- **Tailwind CSS**

## 開発

```bash
npm install
npm run dev
```

http://localhost:3000 で起動します。バックエンドは `http://localhost:8000` で動作している必要があります。

## 環境変数

| 変数 | 説明 |
|------|------|
| `NEXT_PUBLIC_API_URL` | バックエンド API のベース URL（例: `http://localhost:8000`） |

`.env.production.example` を参考に `.env.local` を作成してください。

## 主なページ

| パス | 説明 |
|------|------|
| `/` | トップ（動画一覧・カテゴリ） |
| `/videos/[id]` | 動画再生・詳細 |
| `/history` | 視聴履歴 |
| `/watch-later` | あとで見る |
| `/liked` | いいねした動画 |
| `/jobs` | ジョブ一覧 |
| `/jobs/[id]` | ジョブ詳細 |
| `/new` | 新規コンテンツ作成 |
| `/admin` | 管理画面（記事・動画状況） |
| `/settings` | 設定（API キー等） |
| `/login` | GitHub OAuth ログイン |

## ビルド

```bash
npm run build
npm start
```
