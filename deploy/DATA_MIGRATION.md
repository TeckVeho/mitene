# Mitene — Data migration reference (AWS → GCP)

This document complements [CLOUD_RUN.md](CLOUD_RUN.md) and [DEPLOY.md](DEPLOY.md). **MySQL and object storage migration from AWS (RDS, S3) to GCP (Cloud SQL, GCS) is performed manually by the operator**; the repo does not prescribe step-by-step dump/sync commands. Use the sections below for **app-level keys, env vars, and checks** after your own migration.

---

## 日本語

### MySQL・DB

- **環境変数:** `DATABASE_URL`（MySQL 接続文字列）。Terraform で Cloud SQL を有効にした場合は Secret Manager 経由で注入されることがあります（[infra/terraform/README.md](../infra/terraform/README.md)）。
- **移行作業:** export/import は運用者が実施。移行後は API のスモーク（`/docs`、主要エンドポイント）や必要なら行数・スポットクエリで整合性を確認してください。
- **ロールバック:** 切り替え前のダンプ／スナップショットと旧 `DATABASE_URL` を保持し、手順に沿って復旧できるようにします。

### オブジェクトストレージ（S3 / GCS）

アプリが使うキー構成（[backend/storage.py](../backend/storage.py)）:

| 用途 | キー例 |
|------|--------|
| アップロード | `uploads/{job_id}/{filename}` |
| 動画 | `outputs/{job_id}.mp4` |
| サムネイル | `outputs/{job_id}.jpg` |

- **環境変数:** **`resolve_storage_kind`**（[backend/resolve_storage.py](../backend/resolve_storage.py)）に従い **`GCS_BUCKET` 優先**、次に **`S3_BUCKET_NAME` + `AWS_REGION`**、任意で **`STORAGE_BACKEND`**（`gcs` / `s3` / `local`）。アップロード・署名付き URL は [backend/storage.py](../backend/storage.py) が GCS / S3 のいずれかに振り分けます。
- **移行作業:** オブジェクトのコピー・検証は運用者が実施。プレフィックスとジョブ ID の対応を保ったままバケット間で移すと、アプリの期待と一致しやすいです。

### NotebookLM（`storage_state.json`）と Cloud Run

- **機密:** `storage_state.json` には Google セッション情報が含まれます。リポジトリにコミットしないでください（[.gitignore](../.gitignore) 参照）。
- **GCS 同期（推奨）:** Terraform で `enable_gcs` により **`GCS_BUCKET`** が Cloud Run に渡り、かつ **Cloud Run / App Engine** 上で動いている場合（`K_SERVICE` または `GAE_SERVICE`）、アプリは既定で **`gs://<GCS_BUCKET>/notebooklm/storage_state.json`** とローカルファイルを同期します。起動時に GCS から取得し、リモートログインで保存した直後に GCS へアップロードします。**`NOTEBOOKLM_STORAGE_STATE` は未設定でよい**（既定は `/tmp/.notebooklm/storage_state.json`）。オブジェクトキーは **`NOTEBOOKLM_GCS_OBJECT_KEY`** で変更可能（デフォルト `notebooklm/storage_state.json`）。無効化は **`NOTEBOOKLM_DISABLE_GCS_SYNC=true`**。GKE などでは **`NOTEBOOKLM_FORCE_GCS_SYNC=true`** で同じ同期を有効化できます。
- **手動パス上書き:** **`NOTEBOOKLM_STORAGE_STATE`** を指定すると、そのパスをローカルファイルとして使いつつ、上記 GCS 同期が有効ならアップロード/ダウンロード対象は同じです。
- **再ログイン:** 管理 UI のリモートブラウザログイン（[backend/app/services/remote_browser.py](../backend/app/services/remote_browser.py)）または従来の `notebooklm login`。セッション切れ時は同様に再認証します。
- **タイムアウト・長時間ジョブ:** [CLOUD_RUN.md](CLOUD_RUN.md) の運用メモと issue #33 を参照してください。

---

## Tiếng Việt

### MySQL / DB

- **Biến môi trường:** `DATABASE_URL`. Khi bật Cloud SQL bằng Terraform, giá trị có thể được inject qua Secret Manager ([infra/terraform/README.md](../infra/terraform/README.md)).
- **Di chuyển dữ liệu:** Do operator tự thực hiện (export/import). Sau khi chuyển, nên smoke test API (`/docs`, các endpoint chính) và kiểm tra tùy chọn (row count, query mẫu).
- **Rollback:** Giữ bản dump/snapshot và `DATABASE_URL` cũ để có thể quay lại theo quy trình nội bộ.

### Object storage (S3 / GCS)

Cấu trúc key ứng dụng dùng ([backend/storage.py](../backend/storage.py)):

| Mục đích | Ví dụ key |
|----------|-----------|
| Upload | `uploads/{job_id}/{filename}` |
| Video | `outputs/{job_id}.mp4` |
| Thumbnail | `outputs/{job_id}.jpg` |

- **Biến môi trường:** **`resolve_storage_kind`** ([backend/resolve_storage.py](../backend/resolve_storage.py)): ưu tiên **`GCS_BUCKET`**, sau đó S3 (`S3_BUCKET_NAME` + `AWS_REGION`), tùy chọn **`STORAGE_BACKEND`**. [storage.py](../backend/storage.py) hỗ trợ upload và signed URL cho GCS hoặc S3.
- **Di chuyển:** Copy/verify do operator làm thủ công; giữ nguyên prefix và `job_id` để khớp hành vi app.

### NotebookLM (`storage_state.json`) và Cloud Run

- **Bảo mật:** File chứa session Google — không commit.
- **Đồng bộ GCS (khuyến nghị):** Khi Terraform bật `enable_gcs` và Cloud Run có **`GCS_BUCKET`**, và service chạy trên **Cloud Run / App Engine** (`K_SERVICE` hoặc `GAE_SERVICE`), app mặc định **đồng bộ** với **`gs://<GCS_BUCKET>/notebooklm/storage_state.json`**: lúc khởi động tải xuống, sau remote login upload lên. **Không cần set `NOTEBOOKLM_STORAGE_STATE`** (mặc định local: `/tmp/.notebooklm/storage_state.json`). Đổi key object: **`NOTEBOOKLM_GCS_OBJECT_KEY`**. Tắt: **`NOTEBOOKLM_DISABLE_GCS_SYNC=true`**. Trên GKE: **`NOTEBOOKLM_FORCE_GCS_SYNC=true`**.
- **Ghi đè đường dẫn local:** Set **`NOTEBOOKLM_STORAGE_STATE`** nếu cần path khác; nếu đồng bộ GCS bật, vẫn dùng cùng object trên bucket.
- **Đăng nhập lại:** Remote browser hoặc `notebooklm login`; hết session thì làm lại.
- **Timeout / job dài:** Xem [CLOUD_RUN.md](CLOUD_RUN.md) và issue #33.

---

## Related links

- [CLOUD_RUN.md](CLOUD_RUN.md) — Cloud Build, Terraform, smoke checks
- [DEPLOY.md](DEPLOY.md) — AWS EC2 / RDS / S3 (legacy)
- [infra/terraform/README.md](../infra/terraform/README.md) — outputs (bucket, Cloud SQL, URLs)
