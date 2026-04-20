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
