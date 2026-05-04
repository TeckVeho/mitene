variable "project_id" {
  type        = string
  description = "Common / shared GCP project ID (Artifact Registry + optional CI IAM)."
}

variable "region" {
  type        = string
  default     = "asia-northeast1"
  description = "Region for Artifact Registry."
}

variable "artifact_repo_id" {
  type        = string
  default     = "mitene-docker"
  description = "Docker Artifact Registry repository id (must match app stack image URLs)."
}

variable "reader_project_ids" {
  type        = list(string)
  default     = []
  description = <<-EOT
    GCP project IDs whose default Compute Engine / Cloud Run runtime service accounts
    (PROJECT_NUMBER-compute@developer.gserviceaccount.com) may pull images from this registry.
    Terraform enables compute.googleapis.com on each listed project so that default SA exists.
    Add dev, stg, prod app projects here.
  EOT
}

variable "additional_artifact_registry_reader_members" {
  type        = list(string)
  default     = []
  description = <<-EOT
    Extra IAM members with roles/artifactregistry.reader on the repository (e.g.
    "serviceAccount:cicd@my-project-common.iam.gserviceaccount.com").
  EOT
}

variable "additional_artifact_registry_writer_members" {
  type        = list(string)
  default     = []
  description = <<-EOT
    IAM members with roles/artifactregistry.writer on the repository (push images).
    Add Cloud Build service accounts that run builds and push to this registry, e.g.
    "serviceAccount:PROJECT_NUMBER@cloudbuild.gserviceaccount.com" for each project where
    triggers execute (common project and/or dev/stg/prod app projects).
  EOT
}

variable "artifact_cleanup_keep_count" {
  type        = number
  default     = 10
  description = <<-EOT
    Minimum number of newest image versions to keep per Docker package (image name) in this repository.
    Versions not protected by a KEEP policy are eligible for DELETE. See wiki / Artifact Registry cleanup docs.
  EOT
  validation {
    condition     = var.artifact_cleanup_keep_count >= 1
    error_message = "artifact_cleanup_keep_count must be >= 1."
  }
}

variable "artifact_cleanup_policy_dry_run" {
  type        = bool
  default     = true
  description = <<-EOT
    If true, cleanup policies log what would be deleted without deleting. Set false after verifying in
    GCP Console (Artifact Registry → repository → Cleanup) that rules match expectations.
  EOT
}

variable "artifact_cleanup_keep_tag_prefixes" {
  type        = list(string)
  default     = []
  description = <<-EOT
    Optional tag prefixes for an extra KEEP policy (TAGGED only). Any version with a tag matching a
    prefix is retained (in addition to keep_count). Example: ["prod", "stg"] for prod-* / stg-* style tags.
    Empty list omits this policy. Note: this keeps all matching tags, not a cap of N per prefix.
  EOT
}

variable "artifact_cleanup_delete_untagged_after_days" {
  type        = number
  default     = 7
  description = <<-EOT
    Delete UNTAGGED image versions at least this many days old (avoids removing digests that just lost
    their tag). Passed to cleanup policy older_than as seconds (API format). Set 14 for a more conservative window.
  EOT
  validation {
    condition     = var.artifact_cleanup_delete_untagged_after_days >= 1
    error_message = "artifact_cleanup_delete_untagged_after_days must be >= 1."
  }
}
