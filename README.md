# notebooklm-csv-to-video: CSV から AI 解説コンテンツを生成する

CSVファイルをアップロードするだけで、AIが解説動画（MP4）または音声解説（WAV）を自動生成する
**NoteVideo** の利用手順書です。

## 生成モード

| モード | エンジン | 出力 | 特徴 |
|--------|---------|------|------|
| **動画生成** | Google NotebookLM (notebooklm-py) | MP4 | ビジュアル付き解説動画 |
| **音声生成** | Google Gemini LLM + TTS | WAV | テキスト原稿生成 → 音声読み上げ |

> **注意**: NotebookLM 動画生成モードは非公式ライブラリ (notebooklm-py) を使用しています。
> Googleの内部APIを利用しているため、予告なく動作しなくなる可能性があります。

---

## 目次

1. [前提条件](#前提条件)
2. [手順1: インストール](#手順1-インストール)
3. [手順2: 認証（動画生成モード）](#手順2-認証-動画生成モードのみ-初回のみ)
4. [手順3: 言語設定 (任意)](#手順3-言語設定-任意)
5. [手順4: ノートブック作成](#手順4-ノートブック作成)
6. [手順5: CSVファイルをソースとして追加](#手順5-csvファイルをソースとして追加)
7. [手順6: 解説動画を生成](#手順6-解説動画を生成)
8. [手順7: MP4ファイルをダウンロード](#手順7-mp4ファイルをダウンロード)
9. [音声生成モード (Gemini API)](#音声生成モード-gemini-api)
10. [Python APIで一括実行する場合](#python-apiで一括実行する場合)
11. [トラブルシューティング](#トラブルシューティング)

---

## 前提条件

- Python **3.10 以上**がインストールされていること
- **Googleアカウント**を持っていること（動画生成モード）
- **Google AI API キー**（音声生成モード: `GEMINI_API_KEY`）
- 対象の **CSVファイル**が手元にあること

---

## 手順1: インストール

初回はブラウザログインが必要なため、`browser` エクストラ付きでインストールします。
Playwright (ブラウザ自動化ツール) も合わせてセットアップします。

```bash
pip install "notebooklm-py[browser]"
playwright install chromium
```

音声生成モードを使う場合は、追加で Gemini SDK をインストールします:

```bash
pip install google-genai
```

インストール確認:

```bash
notebooklm --version
```

---

## 手順2: 認証 (動画生成モードのみ・初回のみ)

Chromiumブラウザが自動で開きます。Googleアカウントでログインし、
完了後にターミナルで **Enter** を押してセッションを保存します。

```bash
notebooklm login
```

認証情報は `~/.notebooklm/storage_state.json` に保存され、以降のコマンドで自動的に利用されます。

- セッションの有効期限は数日〜数週間です
- 期限切れになったら再度 `notebooklm login` を実行してください
- 認証状態を事前確認したい場合: `notebooklm auth check --test`

---

## 手順3: 言語設定 (任意)

生成する動画の言語を日本語にしたい場合、グローバル言語設定を変更します。

```bash
notebooklm language set ja
```

> **注意**: この設定はアカウント内の**全ノートブック**に影響します。
>
> グローバル設定を変更しない場合は、動画生成コマンドに毎回 `--language ja` を明示してください。
> 省略すると英語で生成されることがあります（手順6参照）。

現在の言語設定を確認する場合:

```bash
notebooklm language get
```

---

## 手順4: ノートブック作成

新しいノートブックを作成します。

```bash
notebooklm create "CSV分析レポート"
```

出力例:

```
Created notebook: abc123def456...
```

表示されたノートブックIDをアクティブ（作業対象）として設定します。
部分一致でも指定可能です（例: `abc123` の先頭数文字のみ）。

```bash
notebooklm use <notebook_id>
```

現在の状態を確認する場合:

```bash
notebooklm status
```

---

## 手順5: CSVファイルをソースとして追加

`source add` にCSVファイルのパスを渡します。ファイル種別は自動検出されます。

```bash
notebooklm source add "./data.csv"
```

出力例:

```
Added source: src_xyz789... (data.csv)
```

ソースのインデックス作成（処理）が完了するまで待機する場合は、
表示された source_id を使って以下を実行します:

```bash
notebooklm source wait <source_id>
```

追加済みのソース一覧を確認する場合:

```bash
notebooklm source list
```

---

## 手順6: 解説動画を生成

動画生成を開始します。`--wait` フラグを付けると生成完了までブロックします。

> **重要**: `--language ja` を必ず指定してください。省略すると英語で生成されます。

```bash
notebooklm generate video --language ja --wait
```

> **注意**: `--wait` のデフォルトタイムアウトは約600秒（10分）です。動画生成が30分以上かかる場合は
> タイムアウトで終了しますが、**NotebookLM側の生成は継続されます**。
> タイムアウト後は `artifact poll` でステータスを確認し、完了後に `download video` でダウンロードしてください。
> → [動画生成が途中でタイムアウトする](#動画生成が途中でタイムアウトする) も参照

### 動画の内容を指示する場合

自然言語で指示を追加できます:

```bash
notebooklm generate video "CSVデータの主要な傾向と示唆を解説して" --language ja --wait
```

### スタイル・フォーマットを指定する場合

```bash
notebooklm generate video "データの概要を分かりやすく説明して" \
  --style whiteboard \
  --format explainer \
  --language ja \
  --wait
```

**利用可能なスタイル (`--style`)**:

| スタイル名 | 説明 |
|---|---|
| `auto` | 自動選択（デフォルト） |
| `classic` | クラシック |
| `whiteboard` | ホワイトボード風 |
| `kawaii` | かわいい系 |
| `anime` | アニメ風 |
| `watercolor` | 水彩画風 |
| `retro-print` | レトロプリント風 |
| `heritage` | ヘリテージ風 |
| `paper-craft` | ペーパークラフト風 |

**利用可能なフォーマット (`--format`)**:

| フォーマット名 | 説明 |
|---|---|
| `explainer` | 解説型（デフォルト） |
| `brief` | 短縮版 |

> **所要時間**: 動画生成には数分〜30分以上かかる場合があります。

`--wait` を使わずに非同期で開始し、後から状態確認することも可能です:

```bash
# 非同期で開始（すぐに task_id が返る）
notebooklm generate video --language ja --json

# 後から生成状況を確認
notebooklm artifact poll <task_id>

# 生成完了した artifact の一覧を確認
notebooklm artifact list --type video
```

---

## 手順7: MP4ファイルをダウンロード

生成が完了した動画をMP4形式でダウンロードします。

```bash
notebooklm download video ./output_video.mp4
```

### 主要なオプション

| オプション | 説明 |
|---|---|
| `--latest` | 最新の動画をダウンロード（デフォルト動作） |
| `--all` | 生成済みの全動画をダウンロード |
| `--force` | 同名ファイルが存在する場合に上書き |
| `--dry-run` | 実際にはダウンロードせず対象ファイルを表示 |
| `-a <artifact_id>` | 特定のartifact IDを指定してダウンロード |

特定のartifact IDを指定する場合:

```bash
notebooklm download video ./output_video.mp4 -a <artifact_id>
```

---

## 音声生成モード (Gemini API)

Google NotebookLM を使わず、**Gemini LLM + TTS** でCSVデータの音声解説（WAVファイル）を生成する
モードです。NotebookLM のログインは不要で、Google AI API キーのみで動作します。

### 仕組み

```
CSV読み込み → Gemini LLM で解説原稿を生成 → Gemini TTS で音声生成 → WAV保存
```

### 事前準備

```bash
# Gemini SDK のインストール
pip install google-genai

# 環境変数の設定
export GEMINI_API_KEY="your_api_key_here"
```

API キーは [Google AI Studio](https://aistudio.google.com/apikey) から取得できます。

### 利用可能なボイス

| ボイス名 | 説明 |
|---------|------|
| `Kore` | 落ち着いた女性の声（デフォルト） |
| `Puck` | 活発で明るい男性の声 |
| `Charon` | 深みのある落ち着いた男性の声 |
| `Aoede` | 明るく柔らかい女性の声 |
| `Fenrir` | 力強い男性の声 |
| `Leda` | 穏やかな女性の声 |
| `Orus` | クリアな男性の声 |
| `Zephyr` | 軽やかな明るい声 |

### 出力フォーマット

- 形式: WAV (PCM 24kHz / モノラル / 16bit)
- モデル: `gemini-2.5-flash`（原稿生成）、`gemini-2.5-flash-preview-tts`（音声合成）

---

## Python APIで一括実行する場合

CLIコマンドを順番に手動実行する代わりに、Pythonスクリプトで全工程を自動化できます。

### 複数CSVから動画まで一括生成 (`generate_video_from_csv.py`)

ノートブック作成・ソース追加・動画生成・MP4ダウンロードを一括で行います。
CSVは複数指定可能です。

```bash
# 単一CSVの場合
python3 generate_video_from_csv.py --csvs ./data.csv --output ./output_video.mp4

# 複数CSVをまとめて1つのノートブックに追加して動画生成する場合
python3 generate_video_from_csv.py \
  --csvs file1.csv file2.csv file3.csv \
  --output ./output_video.mp4 \
  --notebook-title "統合分析レポート"
```

### ノートブック作成とソース追加のみ (`create_notebook_from_csvs.py`)

動画生成は行わず、複数CSVをノートブックにまとめてソース追加するだけの場合に使います。

```bash
python3 create_notebook_from_csvs.py \
  --title "分析レポート" \
  --csvs file1.csv file2.csv file3.csv
```

---

## トラブルシューティング

### 認証エラーが発生する

```bash
# セッションの状態を診断
notebooklm auth check --test

# 再認証
notebooklm login
```

### レート制限エラーが発生する

短時間に大量のリクエストを送ると制限される場合があります。
数分待ってから再試行してください。

### 動画生成が途中でタイムアウトする

`--wait` を使わずに非同期で管理する方法に切り替えてください:

```bash
# 生成開始（すぐに返る）
notebooklm generate video --json
# -> {"task_id": "xxxx", "status": "pending"}

# 任意のタイミングで状態確認
notebooklm artifact poll <task_id>
```

### ソースの処理が完了しているか確認したい

```bash
notebooklm source list
# STATUS が READY になっていれば処理完了
```

### 音声生成で `GEMINI_API_KEY が設定されていません` エラーが出る

環境変数 `GEMINI_API_KEY` を設定してください:

```bash
export GEMINI_API_KEY="your_api_key_here"
```

[Google AI Studio](https://aistudio.google.com/apikey) でAPIキーを発行できます。

---

## 注意事項

- **非公式ライブラリ**: notebooklm-py は Googleとの提携はなく、内部APIの変更により予告なく動作しなくなる可能性があります
- **レート制限**: 短時間の連続リクエストは制限される場合があります
- **セッション管理**: `~/.notebooklm/storage_state.json` にはGoogleの認証情報が含まれます。取り扱いに注意してください
- **最新バージョン**: notebooklm-py v0.3.3 (2026年3月3日リリース)
