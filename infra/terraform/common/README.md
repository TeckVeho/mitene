# Common stack — shared Artifact Registry

Creates a **Docker Artifact Registry** in the **common** project so dev / stg / prod **pull** from the same host (`asia-northeast1-docker.pkg.dev/<common-project>/mitene-docker/...`) without cross-project IAM between environment projects beyond reader grants managed here.

## Variables

| Variable | Purpose |
|----------|---------|
| `project_id` | Common GCP project |
| `reader_project_ids` | App project IDs (dev, stg, prod) — Terraform grants `roles/artifactregistry.reader` to each project’s default runtime service account |
| `additional_artifact_registry_reader_members` | Extra members with `roles/artifactregistry.reader` |
| `additional_artifact_registry_writer_members` | Members with `roles/artifactregistry.writer` (e.g. Cloud Build SAs that `docker push` to this repo) |
| `artifact_cleanup_keep_count` | Minimum newest versions to keep per Docker image name |
| `artifact_cleanup_policy_dry_run` | If **true**, cleanup only logs deletes — set **false** after checking Artifact Registry → Cleanup in Console |
| `artifact_cleanup_keep_tag_prefixes` | Optional tag prefixes always kept (e.g. `prod`, `dev`) |
| `artifact_cleanup_delete_untagged_after_days` | Delete untagged versions older than N days |

## Order of operations

1. (Optional) [`../bootstrap/`](../bootstrap/) — create the state bucket if needed.
2. Apply this stack (`common/`).
3. Apply [`../network/`](../network/) and the app stack with `create_artifact_registry = false` and `container_image` pointing at the URL prefix from output `docker_repository_url_prefix`.

## Backend

Copy [`backend.tf.example`](backend.tf.example) → `backend.tf`, set `bucket`, and keep `prefix = "common/main"` (or equivalent).
