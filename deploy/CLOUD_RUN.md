# Mitene — Deploy on Google Cloud Run (GCP)

This document describes the **recommended order** to deploy Mitene using **Cloud Build**, **Artifact Registry**, and **Terraform**, aligned with issue #31 and the [kumu](../../../kumu/infra/terraform/README.md) patterns.

For **AWS EC2** deployment, see [DEPLOY.md](DEPLOY.md).

## 1. Prerequisites

- GCP project with billing enabled
- `gcloud` CLI and `terraform` installed
- `gcloud auth login` and `gcloud auth application-default login`
- For private Cloud SQL: apply the **network** stack first — [infra/terraform/network/README.md](../infra/terraform/network/README.md)

## 2. Build and push container images

From the **Mitene repository root** (not `backend/` alone):

1. **API (FastAPI)** — push `mitene-api` to Artifact Registry:

   ```bash
   gcloud builds submit --config=cloudbuild/cloudbuild.dev.api.yaml .
   ```

2. **Web (Next.js)** — set `NEXT_PUBLIC_API_URL` to your **API** public URL (including `/api` suffix):

   ```bash
   gcloud builds submit --config=cloudbuild/cloudbuild.dev.web.yaml \
     --substitutions=_NEXT_PUBLIC_API_URL=https://YOUR-API-SERVICE-URL.run.app/api
   ```

See [cloudbuild/README.md](../cloudbuild/README.md) for substitutions (`_REGION`, `_REPO`, `_TAG`).

After the first successful build, note the image URLs, for example:

`asia-northeast1-docker.pkg.dev/PROJECT_ID/mitene-docker/mitene-api:dev`

## 3. Terraform (infrastructure)

```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars   # edit: project_id, container_image, env_vars, …
terraform init    # configure remote GCS backend in backend.tf if desired
terraform plan
terraform apply
```

- Set `container_image` (and `web_container_image` if `enable_web = true`) to the URLs from step 2.
- When `enable_cloud_sql = true`, set `network_remote_state_bucket` and `network_remote_state_prefix` to match the **network** stack state.
- Do **not** commit `terraform.tfvars` or `terraform.tfstate`.

Details: [infra/terraform/README.md](../infra/terraform/README.md).

## 4. Secrets and environment variables

- **Secret Manager** (recommended): GitHub OAuth secrets, API keys, `DATABASE_URL` overrides (if not using Terraform-managed Cloud SQL secret), NotebookLM-related secrets, etc.
- Use `gcloud run services update SERVICE_NAME --set-secrets=...` or Terraform `secret_key_ref` patterns as your org prefers.
- Never commit secrets to the repository.

## 5. Smoke checks

- Open the Cloud Run **API** URL `/health` (`{"status":"ok"}`) and `/docs` (OpenAPI).
- Open the **Web** URL; confirm the UI loads and calls the API (check browser network tab for `NEXT_PUBLIC_API_URL`).
- **`NEXT_PUBLIC_*`:** Set at **docker build** time (Cloud Build substitutions for web); they are baked into the client bundle, not read from Terraform `web_env_vars` at runtime for browser code.

## 6. Operational notes

- **Data migration (MySQL, object storage, NotebookLM on Cloud Run):** [DATA_MIGRATION.md](DATA_MIGRATION.md) — with `GCS_BUCKET` from Terraform, the API **syncs** `storage_state.json` to `gs://…/notebooklm/storage_state.json` on startup and after remote login (no `NOTEBOOKLM_STORAGE_STATE` required on Cloud Run). AWS→GCP data movement is performed manually by the operator; the doc is a reference only.
- **NotebookLM / long HTTP:** Terraform sets **`cloud_run_timeout`** (default `900s`) and **`cloud_run_max_concurrency`** (default `10`) on the API service — see [infra/terraform/variables.tf](../infra/terraform/variables.tf). Background jobs still need app-level limits; request timeout mainly affects long-lived HTTP (e.g. admin remote login).
- Default Terraform **`allow_unauthenticated`** is **false**; grant `roles/run.invoker` to users or services if you do not use public `allUsers` access.
