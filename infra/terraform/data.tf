data "google_project" "current" {
  project_id = var.project_id
}

locals {
  # Default Cloud Run runtime service account (same project)
  cloud_run_service_account = "${data.google_project.current.number}-compute@developer.gserviceaccount.com"
}
