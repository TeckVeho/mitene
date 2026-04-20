variable "project_id" {
  type        = string
  description = "GCP project ID (e.g. mitene-dev)."
}

variable "region" {
  type        = string
  default     = "asia-northeast1"
  description = "Region for Artifact Registry and Cloud Run."
}

variable "artifact_repo_id" {
  type        = string
  default     = "mitene-docker"
  description = "Artifact Registry repository id (Docker format). Used only when create_artifact_registry is true."
}

variable "create_artifact_registry" {
  type        = bool
  default     = true
  description = <<-EOT
    If true, create a Docker Artifact Registry repository in var.project_id (single-project workflow).
    If false, push/pull images from a registry in another project (e.g. common); set container_image
    to that host and grant readers via infra/terraform/common.
  EOT
}

variable "cloud_run_service_name" {
  type        = string
  default     = "mitene-api-dev"
  description = "Cloud Run service name."
}

variable "container_image" {
  type        = string
  description = "Full image URL (must already exist in Artifact Registry), e.g. asia-northeast1-docker.pkg.dev/PROJECT/REPO/mitene-api:dev"
}

variable "container_port" {
  type        = number
  default     = 8080
  description = "Port the app listens on inside the container."
}

variable "allow_unauthenticated" {
  type        = bool
  default     = false
  description = "If true, grant roles/run.invoker to allUsers (public HTTP). Many orgs block allUsers via IAM policy; use false and grant invoker to specific principals or use IAP."
}

variable "env_vars" {
  type        = map(string)
  default     = { PYTHONUNBUFFERED = "1" }
  description = <<-EOT
    Plain environment variables for the API Cloud Run service (Mitene FastAPI backend).
    When enable_gcs is true, GCS_BUCKET and GCP_PROJECT_ID are merged first; keys here override.
    Do not set DATABASE_URL here if enable_cloud_sql is true (injected from Secret Manager).
    OAuth and other secrets should use Secret Manager + api_secret_env_from_sm, not this map.
    See backend/.env.example for variable names.
  EOT
}

variable "enable_web" {
  type        = bool
  default     = false
  description = "If true, create a second Cloud Run service for the Next.js frontend (mitene-web image)."
}

variable "web_cloud_run_service_name" {
  type        = string
  default     = "mitene-web-dev"
  description = "Cloud Run service name for the frontend."
}

variable "web_container_image" {
  type        = string
  default     = ""
  description = "Full image URL for the web container (Artifact Registry). Required when enable_web is true."
}

variable "web_container_port" {
  type        = number
  default     = 3000
  description = "Port the Next.js standalone server listens on inside the container."
}

variable "web_env_vars" {
  type        = map(string)
  default     = { NODE_ENV = "production" }
  description = <<-EOT
    Plain environment variables for the web Cloud Run service (Next.js).
    Typical keys: NEXT_PUBLIC_API_URL, NEXT_PUBLIC_BASE_URL (see frontend/.env.example).
    NEXT_PUBLIC_* are baked in at docker build for client bundles; keep Cloud Build substitutions aligned with these URLs.
  EOT
}

variable "allow_unauthenticated_web" {
  type        = bool
  default     = false
  description = "If true, grant roles/run.invoker to allUsers for the web service. Set false if org policy blocks allUsers."
}

# --- Custom domains (DNS at your registrar; apex or subdomain) ---

variable "api_custom_domain" {
  type        = string
  default     = ""
  description = <<-EOT
    Optional FQDN for the API Cloud Run service (e.g. api.example.com or apex if you use it for API — rare).
    If non-empty, creates google_cloud_run_domain_mapping and merges API_URL (HTTPS origin only, no path suffix) into the API service env.
    If only the web uses a custom domain, leave this empty and set URLs that still point to the default *.run.app host in env_vars.
  EOT
}

variable "web_custom_domain" {
  type        = string
  default     = ""
  description = <<-EOT
    Optional FQDN for the web Cloud Run service when enable_web = true (e.g. app.example.com or www.example.com).
    If non-empty, creates a domain mapping and merges FRONTEND_URL/CORS_ALLOWED_ORIGINS (API) and NEXT_PUBLIC_* (web) when applicable.
    Requires enable_web = true.
  EOT
}

# --- Cloud Run API: scaling & resources (align with org tier / wiki) ---

variable "cloud_run_api_min_instances" {
  type        = number
  default     = 0
  description = "Minimum instances for the API Cloud Run service (0 = scale to zero when idle)."
}

variable "cloud_run_api_max_instances" {
  type        = number
  default     = 10
  description = "Maximum instances for the API Cloud Run service."
}

variable "cloud_run_api_cpu" {
  type        = string
  default     = "1"
  description = "CPU limit for the API container (e.g. 1 or 1000m)."
}

variable "cloud_run_api_memory" {
  type        = string
  default     = "256Mi"
  description = "Memory limit for the API container. With cpu_idle=true (main.tf), values below 512Mi are valid; otherwise Cloud Run requires at least 512Mi when CPU is always allocated."
}

variable "cloud_run_api_timeout" {
  type        = string
  default     = "300s"
  description = "Max request duration for the API service (e.g. 300s)."
}

variable "cloud_run_api_concurrency" {
  type        = number
  default     = 80
  description = "Max concurrent requests per API instance."
}

# --- Cloud Run Web: scaling & resources ---

variable "cloud_run_web_min_instances" {
  type        = number
  default     = 0
  description = "Minimum instances for the web Cloud Run service."
}

variable "cloud_run_web_max_instances" {
  type        = number
  default     = 10
  description = "Maximum instances for the web Cloud Run service."
}

variable "cloud_run_web_cpu" {
  type        = string
  default     = "1"
  description = "CPU limit for the web container."
}

variable "cloud_run_web_memory" {
  type        = string
  default     = "256Mi"
  description = "Memory limit for the web container. With cpu_idle=true (main.tf), values below 512Mi are valid; otherwise Cloud Run requires at least 512Mi when CPU is always allocated."
}

variable "cloud_run_web_timeout" {
  type        = string
  default     = "300s"
  description = "Max request duration for the web service."
}

variable "cloud_run_web_concurrency" {
  type        = number
  default     = 80
  description = "Max concurrent requests per web instance."
}

# --- Secrets: reference existing Secret Manager secrets (no values in tfvars) ---

variable "api_secret_env_from_sm" {
  type = list(object({
    env_name  = string
    secret_id = string
    version   = optional(string, "latest")
  }))
  default     = []
  description = <<-EOT
    Inject env vars from Secret Manager (create secrets in GCP first). Runtime SA gets secretAccessor on each secret_id.
    Do not use env names that already exist in env_vars.
  EOT
}

variable "web_secret_env_from_sm" {
  type = list(object({
    env_name  = string
    secret_id = string
    version   = optional(string, "latest")
  }))
  default     = []
  description = "Same as api_secret_env_from_sm for the web Cloud Run service when enable_web = true."
}

# --- Optional: project IAM (e.g. Google Groups per internal wiki) ---

variable "project_iam_members" {
  type = list(object({
    member = string
    role   = string
  }))
  default     = []
  description = "Extra project-level IAM bindings (e.g. group:gcp-dev-developers@example.com → roles/viewer)."
}

variable "resource_tier" {
  type        = string
  default     = ""
  description = "Wiki resource tier (e.g. tier3). Used in terraform output and, when manage_gcp_project_labels is true, as the project label `tier` unless label_tier is set."
}

# --- GCP project label `tier` (wiki) ---

variable "manage_gcp_project_labels" {
  type        = bool
  default     = false
  description = <<-EOT
    If true, manage the `tier` label on the existing GCP project via google_project.
    You must run: terraform import 'google_project.wiki_labels[0]' PROJECT_ID once before the first apply.
    Do not enable on a brand-new project creation flow here; this stack assumes the project already exists.
    When true, set label_tier or resource_tier (non-empty) so Terraform can set the tier label.
  EOT

  validation {
    condition     = !var.manage_gcp_project_labels || var.label_tier != "" || var.resource_tier != ""
    error_message = "When manage_gcp_project_labels is true, set label_tier or resource_tier (non-empty) for the project tier label."
  }
}

variable "project_display_name" {
  type        = string
  default     = ""
  description = "Display name for the project when manage_gcp_project_labels is true; defaults to project_id if empty."
}

variable "label_tier" {
  type        = string
  default     = ""
  description = "GCP project label `tier` (e.g. tier3). Empty uses resource_tier when non-empty; omit label key if both empty."
}

# --- Environment label (use separate tfvars / workspace for dev vs prod) ---

variable "env_suffix" {
  type        = string
  default     = "dev"
  description = "Suffix for GCS bucket / secrets / SQL instance naming (e.g. dev, prod). Use one apply per environment with its own tfvars."

  validation {
    condition     = can(regex("^[a-z0-9-]{1,16}$", var.env_suffix))
    error_message = "env_suffix must be lowercase letters, digits, hyphens, max 16 chars."
  }
}

# --- GCS (optional uploads bucket; app code may still use S3 until switched to GCS) ---

variable "enable_gcs" {
  type        = bool
  default     = true
  description = "Create a regional GCS bucket and grant the Cloud Run runtime SA objectAdmin."
}

variable "gcs_bucket_name" {
  type        = string
  default     = ""
  description = "Override bucket name (must be globally unique). If empty, a name is derived from project_id + env_suffix."
}

variable "gcs_force_destroy" {
  type        = bool
  default     = false
  description = "If true, deleting the bucket Terraform resource empties and removes the bucket (use cautiously)."
}

# --- Cloud SQL MySQL (optional; wires DATABASE_URL via Secret Manager + unix socket on Cloud Run) ---

variable "enable_cloud_sql" {
  type        = bool
  default     = false
  description = "Create MySQL instance, database, user, Secret Manager secret, and attach to the API Cloud Run service."
}

variable "sql_instance_name" {
  type        = string
  default     = ""
  description = <<-EOT
    Cloud SQL instance id (resource name). If empty, uses wiki pattern mitene-mysql-{env_suffix} (e.g. mitene-mysql-dev).
    Set explicitly to your existing instance id when migrating from an older naming pattern to avoid Terraform replacing the instance.
  EOT
}

variable "sql_tier" {
  type        = string
  default     = "db-f1-micro"
  description = "Cloud SQL machine tier (cost/size)."
}

variable "sql_disk_size_gb" {
  type        = number
  default     = 10
  description = "Disk size in GB."
}

variable "sql_database_name" {
  type        = string
  default     = "mitene"
  description = "Logical database name inside the instance."
}

variable "sql_user_name" {
  type        = string
  default     = "mitene"
  description = "Application MySQL user name."
}

variable "sql_deletion_protection" {
  type        = bool
  default     = false
  description = "Set true for production instances to block accidental destroy."
}

variable "sql_backup_enabled" {
  type        = bool
  default     = false
  description = "Enable automated daily backups for Cloud SQL. When true, sets backup window and optional PITR (see sql_backup_* variables)."
}

variable "sql_backup_start_time" {
  type        = string
  default     = "17:00"
  description = "Daily backup window start (UTC, HH:MM). Used only when sql_backup_enabled is true. Example: 17:00 UTC ≈ 02:00 JST next calendar day."
}

variable "sql_point_in_time_recovery_enabled" {
  type        = bool
  default     = false
  description = "Enable point-in-time recovery (transaction logs); requires sql_backup_enabled = true. Increases storage cost; prefer true for production."
}

variable "enable_sql_audit" {
  type        = bool
  default     = false
  description = "Enable cloudsql_mysql_audit flag in Cloud SQL (generates Data Access logs, may incur cost on high traffic)"
}

# --- Network stack (remote state) — required when enable_cloud_sql = true ---

variable "network_remote_state_bucket" {
  type        = string
  default     = ""
  description = "GCS bucket for the network Terraform state (from infra/terraform/network). Required when enable_cloud_sql is true."
}

variable "network_remote_state_prefix" {
  type        = string
  default     = ""
  description = "State prefix for the network stack, e.g. network/dev — must match network/backend.tf."
}

# --- Cloud SQL night/weekend schedule (dev; JST) — requires enable_cloud_sql ---

variable "enable_sql_night_weekend_schedule" {
  type        = bool
  default     = false
  description = <<-EOT
    If true, create Cloud Scheduler (JST) + Cloud Functions Gen2 to set Cloud SQL activation_policy NEVER/ALWAYS.
    Use only for non-prod cost savings. Requires enable_cloud_sql = true.
  EOT
}

variable "sql_schedule_timezone" {
  type        = string
  default     = "Asia/Tokyo"
  description = "IANA timezone for Cloud Scheduler (default: Japan)."
}

variable "sql_schedule_start_cron" {
  type        = string
  default     = "0 8 * * 1-5"
  description = "Cron for starting SQL (Mon–Fri morning). Default 08:00 in sql_schedule_timezone."
}

variable "sql_schedule_stop_cron" {
  type        = string
  default     = "0 22 * * 1-5"
  description = "Cron for stopping SQL (Mon–Fri evening). Default 22:00 in sql_schedule_timezone; Fri 22:00 → Mon 08:00 stays off."
}
