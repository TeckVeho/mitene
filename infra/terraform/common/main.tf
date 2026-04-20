resource "google_project_service" "artifactregistry" {
  service = "artifactregistry.googleapis.com"
}

resource "google_artifact_registry_repository" "docker" {
  location      = var.region
  repository_id = var.artifact_repo_id
  description   = "Mitene Docker images (shared; dev/stg/prod pull from here)"
  format        = "DOCKER"

  depends_on = [
    google_project_service.artifactregistry,
  ]
}

data "google_project" "reader" {
  for_each   = toset(var.reader_project_ids)
  project_id = each.value
}

# Default Cloud Run / GCE runtime SA ({project_number}-compute@developer.gserviceaccount.com)
# is created when Compute Engine API is enabled. Without it, IAM binding fails with 400.
resource "google_project_service" "reader_compute" {
  for_each = toset(var.reader_project_ids)

  project            = each.value
  service            = "compute.googleapis.com"
  disable_on_destroy = false
}

locals {
  cloud_run_runtime_sa_emails = {
    for pid in toset(var.reader_project_ids) :
    pid => "${data.google_project.reader[pid].number}-compute@developer.gserviceaccount.com"
  }
}

resource "google_artifact_registry_repository_iam_member" "cloud_run_readers" {
  for_each = local.cloud_run_runtime_sa_emails

  project    = var.project_id
  location   = var.region
  repository = google_artifact_registry_repository.docker.repository_id
  role       = "roles/artifactregistry.reader"
  member     = "serviceAccount:${each.value}"

  depends_on = [google_project_service.reader_compute]
}

resource "google_artifact_registry_repository_iam_member" "additional_readers" {
  for_each = toset(var.additional_artifact_registry_reader_members)

  project    = var.project_id
  location   = var.region
  repository = google_artifact_registry_repository.docker.repository_id
  role       = "roles/artifactregistry.reader"
  member     = each.value
}

resource "google_artifact_registry_repository_iam_member" "additional_writers" {
  for_each = toset(var.additional_artifact_registry_writer_members)

  project    = var.project_id
  location   = var.region
  repository = google_artifact_registry_repository.docker.repository_id
  role       = "roles/artifactregistry.writer"
  member     = each.value
}
