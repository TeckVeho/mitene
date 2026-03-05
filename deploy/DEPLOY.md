# NoteVideo AWS デプロイ手順書

## 0. GitHub へのプッシュ（初回のみ）

プロジェクトルート（`notebooklm-csv-to-video/`）に Git リポジトリを作成して push します。

```bash
cd /path/to/notebooklm-csv-to-video

# frontend/ に別途 .git ディレクトリが存在する場合は削除してから push する
# （サブモジュール扱いを避けるため）
rm -rf frontend/.git

git init
git add .
git commit -m "initial commit"
git branch -M main
git remote add origin https://github.com/{org}/{repo}.git
git push -u origin main
```

> **注意**: `backend/uploads/`・`backend/outputs/`・`.venv/`・`.env`・`*.mp4` 等は
> `.gitignore` により除外済みです。機密情報が含まれていないことを確認してから push してください。

---

## 前提条件

- AWS アカウントへのアクセス権（EC2・RDS・S3・IAM の操作権限）
- ドメイン名（Route 53 または外部 DNS で管理）
- GitHub リポジトリへのアクセス権

---

## 1. AWS リソースの作成

### 1-1. S3 バケット

1. AWS コンソール → S3 → 「バケットを作成」
2. **バケット名**: `notevideo-files-prod`（任意、`.env` と合わせること）
3. **リージョン**: `ap-northeast-1`（東京）
4. **パブリックアクセス**: すべてブロック（デフォルトのまま）
5. その他はデフォルト設定で作成

### 1-2. RDS（MySQL）

1. AWS コンソール → RDS → 「データベースを作成」
2. 設定:
   - **エンジン**: MySQL 8.0 以上（または Amazon Aurora MySQL 互換）
   - **テンプレート**: 本番稼働用（または 開発/テスト）
   - **DB インスタンスクラス**: `db.t3.micro`（小規模の場合）
   - **DB インスタンス識別子**: `notevideo-db`
   - **マスターユーザー名**: `notevideo`
   - **マスターパスワード**: 安全なパスワードを設定
   - **最初のデータベース名**: `notevideo`
   - **パブリックアクセス**: なし
3. VPC セキュリティグループ: EC2 のセキュリティグループからポート 3306 を許可
4. 作成後、エンドポイント（例: `notevideo-db.xxxx.ap-northeast-1.rds.amazonaws.com`）を控えておく

### 1-3. IAM ロール

1. AWS コンソール → IAM → 「ロールを作成」
2. **信頼されたエンティティ**: AWS のサービス → EC2
3. **ポリシーを作成**: `deploy/iam_policy.json` の内容を貼り付ける
   - バケット名は実際の名前に変更すること
4. ロール名: `NoteVideoEC2Role`

### 1-4. EC2 インスタンス

1. AWS コンソール → EC2 → 「インスタンスを起動」
2. 設定:
   - **AMI**: Ubuntu Server 22.04 LTS
   - **インスタンスタイプ**: `t3.medium`（Playwright + Chromium 動作のため）
   - **ストレージ**: 30GB gp3
   - **セキュリティグループ**: 22（SSH）・80（HTTP）・443（HTTPS）を開放
   - **IAM インスタンスプロファイル**: `NoteVideoEC2Role`（手順 1-3 で作成）
3. ElasticIP を割り当て、ドメインの DNS に A レコードを設定する

---

## 2. EC2 セットアップ

```bash
# EC2 に SSH でログイン
ssh -i ~/.ssh/your-key.pem ubuntu@{EC2のパブリックIP}

# セットアップスクリプトを実行（初回のみ）
# 事前に deploy/setup.sh の REPO_URL と DOMAIN を編集すること
sudo bash /tmp/setup.sh
```

または手動で以下を実施:

```bash
# システムパッケージ
sudo apt update && sudo apt install -y nginx git python3.12 python3.12-venv python3-pip certbot python3-certbot-nginx

# Node.js 20
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo bash -
sudo apt install -y nodejs

# Playwright 依存
sudo apt install -y libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
  libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 libasound2

# リポジトリのクローン
sudo git clone https://github.com/{org}/{repo}.git /opt/notevideo
sudo chown -R ubuntu:ubuntu /opt/notevideo
```

---

## 3. アプリケーションのデプロイ

### 3-1. バックエンドのセットアップ

```bash
cd /opt/notevideo/backend

# Python 仮想環境
python3.12 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Playwright ブラウザ（Chromium）のインストール
playwright install chromium
playwright install-deps chromium
```

### 3-2. 環境変数の設定

```bash
# サンプルからコピー
cp /opt/notevideo/backend/.env.example /opt/notevideo/backend/.env

# 実際の値を編集
nano /opt/notevideo/backend/.env
```

以下の値を設定する:

```env
AWS_REGION=ap-northeast-1
S3_BUCKET_NAME=notevideo-files-prod
DATABASE_URL=mysql://notevideo:{パスワード}@{RDSエンドポイント}:3306/notevideo
NOTEVIDEO_API_KEYS={任意のAPIキー}
CORS_ALLOWED_ORIGINS=https://{ドメイン名}
```

### 3-3. フロントエンドのビルド

```bash
cd /opt/notevideo/frontend

# 本番用環境変数
cp .env.production.example .env.production
# NEXT_PUBLIC_API_URL を実際のドメインに編集
nano .env.production

npm ci
npm run build
```

### 3-4. systemd サービスの登録

```bash
sudo cp /opt/notevideo/deploy/notevideo-backend.service /etc/systemd/system/
sudo cp /opt/notevideo/deploy/notevideo-frontend.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable notevideo-backend notevideo-frontend
sudo systemctl start notevideo-backend
sudo systemctl start notevideo-frontend
```

### 3-5. Nginx の設定

```bash
# ドメイン名を置き換えてコピー
sudo sed 's/{ドメイン名}/your-domain.com/g' /opt/notevideo/deploy/nginx.conf \
  > /etc/nginx/sites-available/notevideo
sudo ln -sf /etc/nginx/sites-available/notevideo /etc/nginx/sites-enabled/notevideo
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t

# SSL 証明書取得（Let's Encrypt）
sudo certbot --nginx -d your-domain.com

# Nginx 再起動
sudo systemctl restart nginx
```

---

## 4. Google NotebookLM 認証（重要）

本サービスは `notebooklm-py` 経由で Google NotebookLM を操作するため、
**EC2 上で Google アカウントにログインする必要があります。**

認証情報はサーバーの `~ubuntu/.notebooklm/storage_state.json` に保存されます。

### 初回ログイン手順

```bash
# EC2 に SSH でログイン中に実行
source /opt/notevideo/backend/.venv/bin/activate
notebooklm login
```

> **注意**: `notebooklm login` はブラウザを開きます。
> EC2 は GUI がないため、X11 フォワーディング（`ssh -X`）か、
> または SSH ポートフォワーディングを使って手元のブラウザを使う方法が必要です。
>
> SSH ポートフォワーディング例:
> ```bash
> # ローカル端末で実行
> ssh -L 8080:localhost:8080 ubuntu@{EC2のIP}
> # EC2 上で実行
> notebooklm login --port 8080
> ```

### 認証状態の確認

ブラウザでフロントエンドを開き、ヘッダーの認証バッジが `Authenticated` になれば OK。

または API で確認:
```bash
curl https://your-domain.com/api/auth/status
# → {"status": "authenticated"}
```

### セッション有効期限切れ時

Google のセッションは定期的に期限切れになります。
フロントエンドのヘッダーに「再ログインが必要」と表示されたら、
再度 `notebooklm login` を実行してください。

---

## 5. 動作確認チェックリスト

- [ ] `https://{ドメイン}` にアクセスできること（HTTPS）
- [ ] フロントエンドのヘッダーに `Authenticated` バッジが表示されること
- [ ] フロントエンドからジョブを作成し、完了まで動作すること
- [ ] S3 バケットに `uploads/` と `outputs/` フォルダが作成されること
- [ ] RDS の `jobs` テーブルにレコードが作成されること
- [ ] EC2 再起動後もジョブ履歴が保持されること（RDS 永続化の確認）
- [ ] 完了ジョブの「ダウンロード」ボタンで MP4 が取得できること（S3 署名付き URL）
- [ ] 外部 API（`POST /api/v1/jobs`）がエラーなく動作すること

---

## 6. 更新デプロイ手順（コード更新時）

```bash
cd /opt/notevideo
git pull

# バックエンド: 依存関係に変更がある場合
source backend/.venv/bin/activate
pip install -r backend/requirements.txt

# フロントエンド: 再ビルド
cd frontend && npm ci && npm run build

# サービス再起動
sudo systemctl restart notevideo-backend notevideo-frontend
```

---

## 7. ログ確認コマンド

```bash
# バックエンドログ
sudo journalctl -u notevideo-backend -f --since "1 hour ago"

# フロントエンドログ
sudo journalctl -u notevideo-frontend -f

# Nginx アクセスログ
sudo tail -f /var/log/nginx/access.log

# Nginx エラーログ
sudo tail -f /var/log/nginx/error.log
```
