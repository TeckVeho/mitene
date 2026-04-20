# Terraform — Artifact Registry, Cloud Run, GCS, Cloud SQL (Mitene / GCP)

One Terraform **stack** for **one** environment (dev **or** prod): set `env_suffix`, `container_image`, and toggle resources. **Two environments** = two configurations (two `tfvars` files, two workspaces, or two states) — there is no single `apply` that creates dev and prod together from this module.

## Four-project layout (dev / stg / prod / common)

Recommended layout when splitting GCP projects by environment:

| Stack (directory) | GCP project | State GCS `prefix` (examples) |
|---------------------|-------------|-------------------------------|
| [`bootstrap/`](bootstrap/) (optional) | common | — (local state for this stack only) |
| [`common/`](common/) | common | `common/main` |
| [`network/`](network/) | dev, stg, or prod | `network/dev`, `network/stg`, `network/prod` |
| App (this directory) | dev, stg, or prod | `app/dev`, `app/stg`, `app/prod` |

1. Create the state bucket (bootstrap or manually), then copy [`backend.tf.example`](backend.tf.example) → `backend.tf` with the correct `prefix` per environment.
2. Apply [`common/`](common/) — shared Artifact Registry; set `reader_project_ids` to your app projects so Cloud Run runtime identities get `roles/artifactregistry.reader`.
3. Apply **network** per environment (same module, different `project_id` + backend prefix).
4. In the app stack set **`create_artifact_registry = false`** and point `container_image` / `web_container_image` at `REGION-docker.pkg.dev/<common-project>/mitene-docker/...`.

VPC and application data (SQL, GCS uploads) stay in **each** dev/stg/prod project; **common** holds the shared registry (and optionally the state bucket / CI per your org).

## What this module includes

| Component | Default | Notes |
|-----------|---------|--------|
| Artifact Registry (Docker) | On (`create_artifact_registry`) | `mitene-docker`; turn off when using the registry in [`common/`](common/) |
| Cloud Run API | On | Images from Cloud Build (`:dev` / `:prod`) |
| Cloud Run Web (Next.js) | Off | `enable_web = true` |
| **GCS uploads bucket** | **On** (`enable_gcs`) | Name includes `project_id` + `env_suffix`; IAM `objectAdmin` for Cloud Run runtime SA |
| **Cloud SQL MySQL** | **Off** (`enable_cloud_sql`) | Enable when needed: **private IP** (org policy), **separate network stack** + remote state — see [`network/README.md`](network/README.md) |
| **Cloud Run Job (migrate)** | — | *Not used for Mitene* (no Prisma). Run DB migrations manually or add a job later if needed. |
| **Cloud SQL schedule (JST)** | Off (`enable_sql_night_weekend_schedule`) | Use only for **dev**: Cloud Scheduler + Gen2 Functions set `activation_policy` NEVER/ALWAYS — [`sql_schedule.tf`](sql_schedule.tf); code [`../functions/sql-activation/`](../functions/sql-activation/) |
| **VPC (separate stack)** | Outside this module | [`network/`](network/): VPC + Private Service Access + subnet for **Direct VPC egress** to Cloud SQL (no Serverless VPC Access Connector; **no Cloud NAT** needed for `PRIVATE_RANGES_ONLY` + private SQL) |

Build images: [`cloudbuild/`](../../cloudbuild/) + [`scripts/gcp/README.md`](../../scripts/gcp/README.md) (preferred: Cloud Build + substitutions).

## Build and push container images

Cloud Run reads **`container_image`** and **`web_container_image`** from your tfvars (e.g. `asia-northeast1-docker.pkg.dev/<common-project>/mitene-docker/mitene-api:dev`). The image **must exist** in that Artifact Registry repository with that **path and tag** — otherwise Terraform/Cloud Run returns **Image not found**.

### Recommended: Cloud Build

From the **repository root**, use `gcloud builds submit` with [`cloudbuild/cloudbuild.dev.yaml`](../../cloudbuild/cloudbuild.dev.yaml) (or prod). Set `_AR_PROJECT_ID` to the **common** project when the registry lives there. See **[`scripts/gcp/README.md`](../../scripts/gcp/README.md)** for commands, substitutions (`_NEXT_PUBLIC_API_URL`, `_NEXT_PUBLIC_BASE_URL`), and IAM (`artifactregistry.writer`).

### Manual Docker (local `docker build` + `docker push`)

1. Authenticate Docker to Artifact Registry:

   ```bash
   gcloud auth configure-docker asia-northeast1-docker.pkg.dev
   ```

2. **API (FastAPI)** — typically `backend/Dockerfile` (or Cloud Build `Dockerfile.dev` for cache-friendly CI builds).

   ```bash
   export IMAGE="asia-northeast1-docker.pkg.dev/<COMMON_PROJECT_ID>/mitene-docker/mitene-api:dev"
   docker build -t "$IMAGE" -f backend/Dockerfile backend
   docker push "$IMAGE"
   ```

3. **Web (Next.js)** — `NEXT_PUBLIC_*` values are **baked in at `npm run build`**. Pass your real API and web base URLs (Cloud Run URLs or custom domains):

   ```bash
   export IMAGE="asia-northeast1-docker.pkg.dev/<COMMON_PROJECT_ID>/mitene-docker/mitene-web:dev"
   docker build -t "$IMAGE" \
     --build-arg NEXT_PUBLIC_API_URL="https://<api-host>/api" \
     --build-arg NEXT_PUBLIC_BASE_URL="https://<web-host>" \
     -f frontend/Dockerfile \
     frontend
   docker push "$IMAGE"
   ```

Replace `<COMMON_PROJECT_ID>` (your common / app project id) and URL placeholders so they match what users will use in the browser. After pushing, **`terraform apply`** can update Cloud Run; no need to change tfvars if the image URL/tag is already correct.

## Prerequisites

- Terraform `>= 1.5`
- `gcloud auth application-default login`
- Cloud SQL: billing enabled, `sqladmin` API, Secret Manager; instance creation takes a few minutes.
- Local `terraform.tfvars` / `terraform.tfvars.*` are **gitignored** — do not commit them. If they were ever committed, run `git rm --cached` on those paths and **rotate** any exposed secrets.

### Wiki naming & project labels

- **Cloud SQL instance id:** default **`mitene-mysql-{env_suffix}`** (e.g. `mitene-mysql-dev`). If you already have an instance under another pattern, set **`sql_instance_name`** to that id so Terraform does not try to replace it.
- **GCP project label `tier`:** set **`manage_gcp_project_labels = true`** and set **`label_tier`** and/or **`resource_tier`** (non-empty). Because the project already exists, run once before apply:
  ```bash
  terraform import 'google_project.wiki_labels[0]' YOUR_PROJECT_ID
  ```
  Billing account and org/folder are **ignored** in Terraform lifecycle to avoid accidental changes; labels are updated on apply.

## Dev / production workflows

- **Option A:** `terraform.tfvars.dev` and `terraform.tfvars.prod`, run `terraform apply -var-file=terraform.tfvars.dev` (or `prod`).
- **Option B:** Terraform workspace + matching `*.auto.tfvars`.

Adjust `env_suffix`, `cloud_run_service_name`, `container_image` (tag), and `web_*` as needed. For GCS/SQL, bucket and instance names include `env_suffix` so environments do not collide.

## Recommended apply order

1. **If `enable_cloud_sql = true`:** apply the **network** stack first ([`network/`](network/)), configure the GCS remote backend; in app tfvars set `network_remote_state_bucket` and `network_remote_state_prefix` to match the network state.
2. `terraform apply` Artifact Registry (you can defer Cloud SQL on the first pass if not ready).
3. Push images with Cloud Build.
4. Set `container_image` to the correct URL.
5. `enable_cloud_sql = true` → `apply` app (MySQL private IP + Direct VPC on Cloud Run + Cloud Run).
6. `terraform apply` again if you need to update secrets or attachments.

**Note:** In Terraform, `allow_unauthenticated` / `allow_unauthenticated_web` default to **false**. Sample dev `terraform.tfvars.dev` may set **true** for public `.run.app` (requires org policy allowing `allUsers`). If blocked, keep **false** and grant `roles/run.invoker` to users/groups or use IAP/LB.

## Important variables

| Variable | Purpose |
|----------|---------|
| `env_suffix` | `dev` / `prod` — used for bucket name, secret `mitene-database-url-{suffix}`, SQL instance |
| `enable_gcs` | Create bucket + IAM for Cloud Run SA |
| `enable_cloud_sql` | MySQL (private IP) + Secret `DATABASE_URL` + `/cloudsql` volume + **Direct VPC** (`PRIVATE_RANGES_ONLY`) on API Cloud Run |
| `api_secret_env_from_sm` / `web_secret_env_from_sm` | Inject env vars from **existing** Secret Manager secrets; runtime SA gets `secretAccessor` |
| `cloud_run_api_*` / `cloud_run_web_*` | Scaling, CPU, memory, timeout, concurrency for API / web services |
| `project_iam_members` | Optional `google_project_iam_member` for groups/SAs (see org wiki) |
| `resource_tier` | Tier for wiki / optional GCP label `tier` when labels are managed |
| `sql_instance_name` | Override Cloud SQL instance id; default **`mitene-mysql-{env_suffix}`**. Set to the current instance id when migrating from older names |
| `manage_gcp_project_labels` | If **true**, manage wiki label `tier` on the GCP project — **import required once** (see above); requires `label_tier` or `resource_tier` |
| `label_tier` | Project label `tier` (e.g. `tier3`); empty falls back to `resource_tier` |
| `network_remote_state_*` | Required when `enable_cloud_sql` — points to [`network/`](network/) state |
| `api_custom_domain` / `web_custom_domain` | Optional FQDNs (apex or subdomain) for [`google_cloud_run_domain_mapping`](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/cloud_run_domain_mapping). DNS stays at your registrar — after `apply`, use `terraform output api_domain_mapping_status` (and `web_*`) to add TXT/CNAME (apex may need ALIAS/CNAME flattening). When set, Terraform merges `API_URL` as **HTTPS origin only**, `CORS_ORIGINS`, `FRONTEND_URL`, and `NEXT_PUBLIC_*` (including `NEXT_PUBLIC_API_URL` **with** `/api` for Mitene). If only one service uses a custom domain, keep the other URLs on `*.run.app` in tfvars. |
| `sql_deletion_protection` | Prefer `true` in prod |
| `sql_backup_enabled` | Automated daily Cloud SQL backups (**default `false`**) — set `true` for stg/prod when required |
| `sql_backup_start_time` | Backup window start in **UTC** (`HH:MM`) when backups enabled |
| `sql_point_in_time_recovery_enabled` | PITR (transaction logs); requires `sql_backup_enabled`; extra cost — common for prod |
| `enable_sql_night_weekend_schedule` | **Dev only:** Scheduler + Function to stop/start Cloud SQL on JST (`sql_schedule_*`) |
| `sql_schedule_timezone` / `sql_schedule_start_cron` / `sql_schedule_stop_cron` | Customize schedule (default 08:00 / 22:00 Mon–Fri) |

**Note:** When `enable_cloud_sql = true`, do **not** set `DATABASE_URL` in `env_vars` (enforced by a check). The app may still use the AWS SDK for S3 until you switch to GCS — bucket from `terraform output gcs_uploads_bucket`.

### Cloud SQL night/weekend schedule (Japan time, dev)

- Enable: `enable_cloud_sql = true` and `enable_sql_night_weekend_schedule = true` (see [`terraform.tfvars.example`](terraform.tfvars.example)).
- Default: **Mon–Fri** at **08:00** JST start SQL (`ALWAYS`), **22:00** JST stop (`NEVER`). From **Friday** evening through **Monday** morning the instance stays stopped.
- Terraform keeps `activation_policy` in `lifecycle.ignore_changes` so later applies do not overwrite Scheduler-driven state.
- After SQL starts, the instance may need a few minutes; the API Cloud Run may return DB errors until then.
- **Migrations / CI:** run your DB migration tool while SQL is up (JST business hours), or start SQL manually in the console.
- Cloud Run API/Web scale to zero when idle; the GCS bucket does not need a schedule (mostly storage cost).

### `env_vars` (API) and `web_env_vars` (web)

- **`env_vars`:** Map of backend env vars (see `backend/.env.example`). When `enable_gcs = true`, Terraform **merges** `GCS_BUCKET` and `GCP_PROJECT_ID`; keys in `env_vars` **override** on collision.
- **`web_env_vars`:** Map for Next.js Cloud Run when `enable_web = true` (see `frontend/.env.example`, often `NEXT_PUBLIC_*`). Put secrets (JWT, Stripe, …) in **Secret Manager** + `gcloud run services update --set-secrets`, not in committed tfvars.

### Custom domains (registrar DNS, not Cloud DNS required)

1. Set `api_custom_domain` and/or `web_custom_domain` in your tfvars (FQDN only; optional `https://` is stripped). Empty string = no domain mapping for that service.
2. `terraform apply` creates [`domain_mapping.tf`](domain_mapping.tf) resources. Map **web** only when `enable_web = true`.
3. At your DNS provider (where you bought the domain), add the records shown in **`terraform output api_domain_mapping_status`** / **`web_domain_mapping_status`** (typically TXT verification + CNAME to `ghs.googlehosted.com` for subdomains; **apex** often needs ALIAS/ANAME or your provider’s CNAME flattening).
4. Outputs **`api_public_base_url`** and **`web_public_base_url`** show the effective browser-facing bases (custom hostname or default `*.run.app`).

## Outputs

- `cloud_run_url`, `api_public_base_url`, `web_public_base_url`, `api_domain_mapping_status`, `web_domain_mapping_status`, `gcs_uploads_bucket`, `cloud_sql_connection_name`, `secret_database_url_id`, …
- When SQL schedule is enabled: `sql_schedule_function_url`, `sql_scheduler_job_stop`, `sql_scheduler_job_start`

## State

Use a **remote backend** (GCS) for team workflows. The bucket often lives in the **common** project; **one bucket**, multiple **prefixes** (`app/dev`, `network/dev`, …) — do not share one prefix across environments. See [`bootstrap/README.md`](bootstrap/README.md) and [`backend.tf.example`](backend.tf.example).

## Related docs

- [Cloud Build](../../cloudbuild/)
- [scripts/gcp](../../scripts/gcp/README.md)
