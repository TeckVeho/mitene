# Optional: apply wiki project label `tier` to the existing GCP project.
# One-time: terraform import 'google_project.wiki_labels[0]' YOUR_PROJECT_ID
# terraform import -var-file=ENV_FILE 'google_project.wiki_labels[0]' YOUR_PROJECT_ID

locals {
  label_tier_effective = var.label_tier != "" ? var.label_tier : var.resource_tier
}

resource "google_project" "wiki_labels" {
  count = var.manage_gcp_project_labels ? 1 : 0

  project_id = var.project_id
  name       = var.project_display_name != "" ? var.project_display_name : var.project_id

  labels = local.label_tier_effective != "" ? { tier = replace(lower(local.label_tier_effective), "_", "-") } : {}

  lifecycle {
    ignore_changes = [
      billing_account,
      org_id,
      folder_id,
    ]
  }
}
