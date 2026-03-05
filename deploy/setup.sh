#!/bin/bash
# NoteVideo EC2 セットアップスクリプト（Ubuntu 22.04 LTS）
# 使用方法: sudo bash setup.sh
#
# 前提: EC2 に IAM ロール（NoteVideoS3Access + RDS アクセス）がアタッチ済みであること

set -euo pipefail

REPO_URL="https://github.com/{org}/{repo}.git"  # 実際のリポジトリ URL に変更
DEPLOY_DIR="/opt/notevideo"
DOMAIN="{ドメイン名}"  # 実際のドメインに変更
PYTHON_VERSION="3.12"

echo "=== [1/7] システムパッケージのインストール ==="
apt-get update -y
apt-get install -y \
    nginx \
    git \
    curl \
    certbot \
    python3-certbot-nginx \
    python3-pip \
    python3-venv \
    python${PYTHON_VERSION} \
    python${PYTHON_VERSION}-venv

# Node.js 20.x のインストール
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt-get install -y nodejs

# Playwright / Chromium 依存ライブラリ
apt-get install -y \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpangocairo-1.0-0 \
    libpango-1.0-0 \
    libcairo2

echo "=== [2/7] アプリケーションコードのデプロイ ==="
if [ -d "$DEPLOY_DIR" ]; then
    cd "$DEPLOY_DIR" && git pull
else
    git clone "$REPO_URL" "$DEPLOY_DIR"
fi
chown -R ubuntu:ubuntu "$DEPLOY_DIR"

echo "=== [3/7] バックエンド Python 環境のセットアップ ==="
cd "$DEPLOY_DIR/backend"
sudo -u ubuntu python${PYTHON_VERSION} -m venv .venv
sudo -u ubuntu .venv/bin/pip install --upgrade pip
sudo -u ubuntu .venv/bin/pip install -r requirements.txt

# Playwright ブラウザのインストール（Chromium のみ）
sudo -u ubuntu .venv/bin/playwright install chromium

echo "=== [4/7] フロントエンドのビルド ==="
cd "$DEPLOY_DIR/frontend"

# 本番用 .env.production を配置（事前に作成しておくこと）
if [ ! -f ".env.production" ]; then
    echo "NEXT_PUBLIC_USE_MOCK=false" > .env.production
    echo "NEXT_PUBLIC_API_URL=https://${DOMAIN}/api" >> .env.production
fi

sudo -u ubuntu npm ci
sudo -u ubuntu npm run build

echo "=== [5/7] systemd サービスの登録 ==="
cp "$DEPLOY_DIR/deploy/notevideo-backend.service" /etc/systemd/system/
cp "$DEPLOY_DIR/deploy/notevideo-frontend.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable notevideo-backend notevideo-frontend

echo "=== [6/7] Nginx の設定 ==="
cp "$DEPLOY_DIR/deploy/nginx.conf" /etc/nginx/sites-available/notevideo
ln -sf /etc/nginx/sites-available/notevideo /etc/nginx/sites-enabled/notevideo
rm -f /etc/nginx/sites-enabled/default
nginx -t

echo "=== [7/7] SSL 証明書の取得（Let's Encrypt） ==="
certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos -m admin@${DOMAIN}

echo ""
echo "========================================"
echo "セットアップ完了！"
echo ""
echo "次の手順:"
echo "1. /opt/notevideo/backend/.env を作成・編集する（環境変数を設定）"
echo "2. sudo systemctl start notevideo-backend"
echo "3. sudo systemctl start notevideo-frontend"
echo "4. sudo systemctl reload nginx"
echo "5. notebooklm login で Google 認証を行う"
echo "========================================"
