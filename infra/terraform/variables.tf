variable "project_id" {
  type        = string
  description = "GCP project ID (e.g. my-org-mitene-dev)."
}

variable "region" {
  type        = string
  default     = "asia-northeast1"
  description = "Region for Artifact Registry and Cloud Run."
}

variable "artifact_repo_id" {
  type        = string
  default     = "mitene-docker"
  description = "Artifact Registry repository id (Docker format)."
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

variable "cloud_run_timeout" {
  type        = string
  default     = "900s"
  description = "Maximum duration a single request to the API may take (Cloud Run). Increase for long-lived HTTP such as admin remote login; background jobs are not extended by this alone."
}

variable "cloud_run_max_concurrency" {
  type        = number
  default     = 10
  description = "Max concurrent requests per API instance. Lower if Playwright/NotebookLM workloads are memory-heavy."
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
    OAuth and other secrets should use Secret Manager + Cloud Run --set-secrets, not this map.
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
