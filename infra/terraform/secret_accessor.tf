# Grant Cloud Run runtime SA access to secrets referenced by api_secret_env_from_sm / web_secret_env_from_sm.

locals {
  distinct_sm_secret_ids_for_runtime = distinct(concat(
    [for s in var.api_secret_env_from_sm : s.secret_id],
    [for s in var.web_secret_env_from_sm : s.secret_id],
  ))
}

resource "google_secret_manager_secret_iam_member" "cloudrun_secret_accessor" {
  for_each = toset(local.distinct_sm_secret_ids_for_runtime)

  project   = var.project_id
  secret_id = each.value
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${local.cloud_run_service_account}"
}
