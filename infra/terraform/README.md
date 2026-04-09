# Terraform — Mitene on GCP (Artifact Registry, Cloud Run, GCS, Cloud SQL)

One Terraform **stack** per **environment** (dev **or** prod): set `env_suffix`, `container_image`, and feature flags. Two environments = two separate applies (two `tfvars`, two workspaces, or two state prefixes).

Conceptually aligned with the **kumu** module; see [kumu/infra/terraform/README.md](../../../kumu/infra/terraform/README.md) for the full flow. This copy uses **Mitene** defaults (`mitene-docker`, `mitene-api-dev`, `mitene-web-dev`, `mitene-database-url-*`, …).

## What this module creates

| Component | Default | Notes |
|-----------|---------|--------|
| Artifact Registry (Docker) | On | `mitene-docker` (default `artifact_repo_id`) |
| Cloud Run API | On | FastAPI image from Cloud Build |
| Cloud Run Web (Next.js) | Off | `enable_web = true` |
| GCS uploads bucket | On (`enable_gcs`) | Name includes `project_id` + `env_suffix` |
| Cloud SQL MySQL | Off (`enable_cloud_sql`) | Private IP; requires **network** stack + remote state — [network/README.md](network/README.md) |

Database schema: apply via Mitene app startup / manual SQL (no Prisma; no migrate Cloud Run Job in this stack).

Build images: [mitene/cloudbuild/README.md](../../cloudbuild/README.md).

## Prerequisites

- Terraform `>= 1.5`
- `gcloud auth application-default login`
- For Cloud SQL: billing enabled, APIs enabled

## Suggested order

1. If using Cloud SQL: apply **`network/`** first; configure GCS backend for state; set `network_remote_state_bucket` and `network_remote_state_prefix` in app `tfvars`.
2. `terraform init` / `terraform apply` (Artifact Registry + Cloud Run may be first slice).
3. Run Cloud Build to push `mitene-api` / `mitene-web` images.
4. Set `container_image` / `web_container_image` to the pushed URLs.
5. Enable `enable_cloud_sql` when ready; re-apply.

Default **`allow_unauthenticated`** / **`allow_unauthenticated_web`** are **false**. Set **true** only if org policy allows `allUsers` as Cloud Run invoker.

## Important variables

| Variable | Purpose |
|----------|---------|
| `env_suffix` | `dev` / `prod` — used in bucket names, secrets, SQL instance name |
| `enable_gcs` | Create bucket + IAM for default compute SA |
| `enable_cloud_sql` | MySQL + Secret `DATABASE_URL` + `/cloudsql` volume + VPC connector on API |
| `network_remote_state_*` | Required when `enable_cloud_sql = true` |
| `cloud_run_timeout` | API request timeout (default `900s`); not a substitute for app-side job limits |
| `cloud_run_max_concurrency` | Requests per instance (default `10`; tune for Playwright/NotebookLM memory) |

When `enable_cloud_sql = true`, do **not** put `DATABASE_URL` in `env_vars` (Terraform injects it from Secret Manager).

## Outputs

`cloud_run_url`, `gcs_uploads_bucket`, `cloud_sql_connection_name`, `secret_database_url_id`, `vpc_access_connector`, etc.

## State

Use a **remote GCS backend** for team use. Do not commit `terraform.tfstate` or secrets.

## Related docs

- [mitene/deploy/CLOUD_RUN.md](../../deploy/CLOUD_RUN.md)
- [kumu/infra/terraform/README.md](../../../kumu/infra/terraform/README.md) (reference)
