# Bootstrap — GCS bucket for Terraform remote state

The Terraform `gcs` backend **requires an existing bucket** before `terraform init` can use it. This stack creates that bucket **once**, usually in the **common** project (where state lives in the dev / stg / prod / common model).

## How to run it

### Option A — Terraform stack (uses **local** state here)

1. In this directory, copy `terraform.tfvars.example` → `terraform.tfvars` and set `project_id` (common) and `state_bucket_name`.
2. `terraform init` (no remote backend in this stack — default local state).
3. `terraform apply` — creates the bucket.
4. Other stacks (`common/`, `network/`, app) configure `backend "gcs" { bucket = "<state_bucket_name>" ... }` to point at that bucket.

### Option B — Create the bucket manually (Console / gcloud)

Example:

```bash
gcloud storage buckets create gs://YOUR_COMMON_PROJECT-terraform-state \
  --project=YOUR_COMMON_PROJECT_ID \
  --location=asia-northeast1 \
  --uniform-bucket-level-access
gcloud storage buckets update gs://YOUR_COMMON_PROJECT-terraform-state --versioning
```

You can skip the `bootstrap/` stack if your team prefers manual operations.

## Bucket naming

Use a **globally unique** name, e.g. `{common_project_id}-terraform-state` (matches the hints in app and network `backend.tf.example` files).

## Overall order (multi-project)

1. (Optional) **bootstrap** — state bucket.
2. **common** — Artifact Registry + IAM readers for dev/stg/prod app projects.
3. **network** — one `prefix` per env (`network/dev`, …).
4. **app** — one `prefix` per env (`app/dev`, …); set `container_image` to the common registry if `create_artifact_registry = false` in the app stack.
