# cursor-shared-skills

**Languages:** [日本語](#日本語-ja) · [Tiếng Việt](#tiếng-việt-vi)

---

## 日本語 (JA)

Cursor IDE のカスタムコマンド・スキルを git submodule として提供するリポジトリです。
複数プロジェクトから共有・一元管理できるアーキテクチャを実現します。

### コマンド一覧

| コマンド | ファイル | 概要 |
|---------|---------|------|
| `/issue` | `commands/issue.md` | GitHub Issue 取得・ブランチ作成・issue.md 保存 |
| `/plan` | `commands/plan.md` | 実装計画 (plan.md) の作成 |
| `/breakdown` | `commands/breakdown.md` | Issue を FE/BE に分解して子 Issue を作成 |
| `/dev` | `commands/dev.md` | 実装フェーズの AI エージェント指示 |
| `/test` | `commands/test.md` | テスト実行・証跡保存 |
| `/pr` | `commands/pr.md` | コミット・PR 作成・Issue 自動リンク |

### スキル一覧

Cursor エージェントは `.cursor/skills/` 内の `SKILL.md` を自動発見し、会話の内容に応じて適切なスキルを自動適用します。明示的なコマンド実行は不要です。

| スキル名 | ディレクトリ | 概要 | 自動適用トリガー |
|---------|------------|------|----------------|
| `sp-estimation` | `skills/sp-estimation/` | GitHub Issue の SP 見積り (1 SP = 1時間、6軸フレームワーク) | `/breakdown` 実行時、「SP」「見積り」「ストーリーポイント」を含む会話 |

### アーキテクチャ

```
<project-root>/
├── .cursor-shared-skills/  ← このリポジトリ (submodule)
│   ├── commands/
│   ├── skills/
│   ├── script/
│   ├── utils/
│   └── setup.sh
└── .cursor/
    ├── commands/           ← symlink → ../.cursor-shared-skills/commands/
    └── skills/
        └── sp-estimation/  ← symlink → ../../.cursor-shared-skills/skills/sp-estimation/
```

Cursor IDE は `.cursor/commands/` 内の `.md` ファイルをコマンドとして認識します。
Cursor IDE は `.cursor/skills/` 内の `SKILL.md` をスキルとして認識し、エージェントが自動適用します。
`setup.sh` がこれらの symlink を作成します。

### 前提条件

| ツール | インストール方法 | 用途 |
|--------|----------------|------|
| `gh` CLI (ログイン済み) | [cli.github.com](https://cli.github.com) → `gh auth login` | GitHub API 呼び出し |
| `jq` | `brew install jq` (macOS) / `apt install jq` (Linux) | `setsp` スクリプト内の JSON 処理 |

#### 導入手順

**1. サブモジュールとして追加**

```bash
git submodule add https://github.com/TeckVeho/cursor-shared-skills.git .cursor-shared-skills
```

**2. セットアップ実行 (symlink 作成)**

```bash
bash .cursor-shared-skills/setup.sh
```

**3. .gitignore に追記**

symlink 自体はプロジェクト固有の追跡が不要なため除外します。

```bash
echo ".cursor/commands" >> .gitignore
echo ".cursor/skills" >> .gitignore
```

**4. コミット**

```bash
git add .gitmodules .cursor-shared-skills .gitignore
git commit -m "chore: add cursor-shared-skills submodule"
```

> **Note:** `.cursor/commands` および `.cursor/skills` は `.gitignore` で除外済みのためコミット不要です。

#### 更新手順

コマンド・スキルの改善が submodule リポジトリに push された後、各プロジェクトで以下を実行します。

```bash
# submodule を最新コミットに更新
cd .cursor-shared-skills
git pull origin main
cd ..

# setup.sh を再実行 (新しいスキルの symlink を追加)
bash .cursor-shared-skills/setup.sh

# 親プロジェクトに新しいコミットハッシュを記録
git add .cursor-shared-skills
git commit -m "chore: update cursor-shared-skills submodule"
```

#### 初回クローン後の初期化

他のメンバーがリポジトリをクローンした際:

```bash
git clone https://github.com/TeckVeho/cursor-shared-skills.git
git submodule update --init --recursive
bash .cursor-shared-skills/setup.sh
```

#### ファイル構成

```
cursor-shared-skills/
├── commands/
│   ├── issue.md
│   ├── plan.md
│   ├── breakdown.md
│   ├── dev.md
│   ├── test.md
│   └── pr.md
├── skills/
│   └── sp-estimation/
│       └── SKILL.md
├── script/
│   ├── setsp.ps
│   └── setsp.ps1
├── utils/
│   └── issue-cache.js
├── setup.sh
├── .gitignore
└── README.md
```

#### setup.sh の動作

1. `.cursor/` ディレクトリが存在しない場合は作成
2. `.cursor/commands` が既存の場合はタイムスタンプ付きでバックアップ
3. `.cursor/commands` → `../.cursor-shared-skills/commands` の相対 symlink を作成
4. `script/` 内のスクリプトに実行権限を付与
5. `.cursor/skills/` ディレクトリを作成し、`skills/*/` を走査してスキルごとに個別 symlink を作成
   - 既存の同名 symlink はタイムスタンプ付きでバックアップ
   - 各プロジェクト固有のスキルと共有スキルが `.cursor/skills/` 内で共存可能

---

## Tiếng Việt (VI)

Kho lưu trữ cung cấp lệnh tùy chỉnh và skill cho Cursor IDE dưới dạng git submodule.
Kiến trúc cho phép chia sẻ và quản lý tập trung từ nhiều dự án.

### Danh sách lệnh

| Lệnh | Tệp | Mô tả |
|------|-----|--------|
| `/issue` | `commands/issue.md` | Lấy GitHub Issue, tạo nhánh, lưu issue.md |
| `/plan` | `commands/plan.md` | Tạo kế hoạch triển khai (plan.md) |
| `/breakdown` | `commands/breakdown.md` | Tách Issue thành FE/BE và tạo Issue con |
| `/dev` | `commands/dev.md` | Hướng dẫn agent AI cho giai đoạn triển khai |
| `/test` | `commands/test.md` | Chạy test và lưu bằng chứng |
| `/pr` | `commands/pr.md` | Commit, tạo PR, liên kết Issue tự động |

### Danh sách skill

Agent Cursor tự động phát hiện `SKILL.md` trong `.cursor/skills/` và áp dụng skill phù hợp theo nội dung hội thoại. Không cần gọi lệnh một cách tường minh.

| Tên skill | Thư mục | Mô tả | Kích hoạt tự động |
|-----------|---------|--------|-------------------|
| `sp-estimation` | `skills/sp-estimation/` | Ước lượng SP cho GitHub Issue (1 SP = 1 giờ, khung 6 trục) | Khi chạy `/breakdown` hoặc hội thoại có «SP», «ước lượng», «story point» |

### Kiến trúc

```
<project-root>/
├── .cursor-shared-skills/  ← kho này (submodule)
│   ├── commands/
│   ├── skills/
│   ├── script/
│   ├── utils/
│   └── setup.sh
└── .cursor/
    ├── commands/           ← symlink → ../.cursor-shared-skills/commands/
    └── skills/
        └── sp-estimation/  ← symlink → ../../.cursor-shared-skills/skills/sp-estimation/
```

Cursor IDE nhận diện tệp `.md` trong `.cursor/commands/` là lệnh.
Cursor IDE nhận diện `SKILL.md` trong `.cursor/skills/` là skill và agent áp dụng tự động.
`setup.sh` tạo các symlink này.

### Điều kiện tiên quyết

| Công cụ | Cách cài | Mục đích |
|---------|----------|----------|
| `gh` CLI (đã đăng nhập) | [cli.github.com](https://cli.github.com) → `gh auth login` | Gọi GitHub API |
| `jq` | `brew install jq` (macOS) / `apt install jq` (Linux) | Xử lý JSON trong script `setsp` |

#### Cài đặt

**1. Thêm submodule**

```bash
git submodule add https://github.com/TeckVeho/cursor-shared-skills.git .cursor-shared-skills
```

**2. Chạy setup (tạo symlink)**

```bash
bash .cursor-shared-skills/setup.sh
```

**3. Thêm vào .gitignore**

Bỏ qua symlink vì không cần theo dõi riêng theo từng dự án.

```bash
echo ".cursor/commands" >> .gitignore
echo ".cursor/skills" >> .gitignore
```

**4. Commit**

```bash
git add .gitmodules .cursor-shared-skills .gitignore
git commit -m "chore: add cursor-shared-skills submodule"
```

> **Lưu ý:** `.cursor/commands` và `.cursor/skills` đã nằm trong `.gitignore` nên không cần commit.

#### Cập nhật

Sau khi cải tiến lệnh/skill được push lên kho submodule, trên mỗi dự án chạy:

```bash
cd .cursor-shared-skills
git pull origin main
cd ..

bash .cursor-shared-skills/setup.sh

git add .cursor-shared-skills
git commit -m "chore: update cursor-shared-skills submodule"
```

#### Sau lần clone đầu tiên

Khi thành viên clone kho:

```bash
git clone https://github.com/TeckVeho/cursor-shared-skills.git
git submodule update --init --recursive
bash .cursor-shared-skills/setup.sh
```

#### Cấu trúc tệp

```
cursor-shared-skills/
├── commands/
│   ├── issue.md
│   ├── plan.md
│   ├── breakdown.md
│   ├── dev.md
│   ├── test.md
│   └── pr.md
├── skills/
│   └── sp-estimation/
│       └── SKILL.md
├── script/
│   ├── setsp.ps
│   └── setsp.ps1
├── utils/
│   └── issue-cache.js
├── setup.sh
├── .gitignore
└── README.md
```

#### Hành vi của setup.sh

1. Tạo `.cursor/` nếu chưa có
2. Nếu đã có `.cursor/commands` thì sao lưu kèm timestamp
3. Tạo symlink tương đối `.cursor/commands` → `../.cursor-shared-skills/commands`
4. Gán quyền thực thi cho script trong `script/`
5. Tạo `.cursor/skills/`, duyệt `skills/*/` và tạo symlink riêng cho từng skill
   - Symlink trùng tên được sao lưu kèm timestamp
   - Skill riêng dự án và skill chia sẻ có thể cùng tồn tại trong `.cursor/skills/`
