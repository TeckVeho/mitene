# Vertex AI (Generative AI on GCP) — enabled when enable_vertex_ai = true.
# Cloud Run runtime SA uses Application Default Credentials; GEMINI_API_KEY is not injected.

resource "google_project_service" "aiplatform" {
  count = var.enable_vertex_ai ? 1 : 0

  service = "aiplatform.googleapis.com"
}

resource "google_project_iam_member" "cloudrun_vertex_ai_user" {
  count = var.enable_vertex_ai ? 1 : 0

  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${local.cloud_run_service_account}"

  depends_on = [
    google_project_service.aiplatform,
  ]
}
